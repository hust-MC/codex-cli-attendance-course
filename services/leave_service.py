# 请假业务服务
# 负责请假申请、日期冲突校验和审批状态流转
from db import LEAVE_TYPES, get_db
from models.leave import Leave
from services import employee_service
from services.errors import ServiceError
from services.validators import clean_text, inclusive_days, parse_date, parse_positive_int


def _find_approved_overlap(conn, employee_id, start_date, end_date):
    """查询与新区间重叠的已审批请假

    两个闭区间 [a1, a2] 和 [b1, b2] 重叠的条件是 a1 <= b2 且 a2 >= b1。
    注意是「小于等于」而不是「小于」：已审批 11-18 到 11-20，
    新申请 11-20 到 11-22 共享 11-20 这一天，属于首尾相接，不算冲突。
    """
    row = conn.execute(
        '''
        SELECT id FROM leaves
        WHERE employee_id = ?
          AND status = 'approved'
          AND start_date <= ?
          AND end_date >= ?
        LIMIT 1
        ''',
        (employee_id, end_date, start_date),
    ).fetchone()
    return row is not None


def create_leave(payload):
    """提交请假申请"""
    if not isinstance(payload, dict):
        raise ServiceError('请求体必须是 JSON 对象')

    employee = employee_service.get_employee(payload.get('employee_id'))
    employee_service.ensure_employee_active(employee)

    leave_type = payload.get('leave_type')
    if leave_type not in LEAVE_TYPES:
        raise ServiceError('请假类型只能是 事假、病假、年假、调休')

    start_date = parse_date(payload.get('start_date'), '开始日期')
    end_date = parse_date(payload.get('end_date'), '结束日期')
    if start_date > end_date:
        raise ServiceError('开始日期不能晚于结束日期')

    reason = clean_text(payload.get('reason'), '请假原因', max_length=200)
    start_text = start_date.isoformat()
    end_text = end_date.isoformat()
    days = inclusive_days(start_date, end_date)

    conn = get_db()
    try:
        if _find_approved_overlap(conn, employee.id, start_text, end_text):
            raise ServiceError('该时间段与已审批的请假冲突')
        cursor = conn.execute(
            '''
            INSERT INTO leaves (employee_id, leave_type, start_date, end_date, days, reason)
            VALUES (?, ?, ?, ?, ?, ?)
            ''',
            (employee.id, leave_type, start_text, end_text, days, reason or None),
        )
        conn.commit()
        row = conn.execute(
            'SELECT * FROM leaves WHERE id = ?',
            (cursor.lastrowid,),
        ).fetchone()
    finally:
        conn.close()
    return Leave.from_row(row)


def get_leave(leave_id):
    """查询请假详情"""
    leave_id = parse_positive_int(leave_id, '请假编号')
    conn = get_db()
    try:
        row = conn.execute('SELECT * FROM leaves WHERE id = ?', (leave_id,)).fetchone()
    finally:
        conn.close()
    if row is None:
        raise ServiceError('请假申请不存在', code=404)
    return Leave.from_row(row)


def list_leaves(employee_id=None, status=None, start_date=None, end_date=None):
    """查询请假列表，可按员工、状态和日期区间筛选"""
    conditions = []
    params = []

    if employee_id not in (None, ''):
        conditions.append('employee_id = ?')
        params.append(parse_positive_int(employee_id, '员工编号'))
    if status:
        if status not in ('pending', 'approved', 'rejected'):
            raise ServiceError('审批状态只能是 pending、approved 或 rejected')
        conditions.append('status = ?')
        params.append(status)
    if start_date:
        conditions.append('end_date >= ?')
        params.append(parse_date(start_date, '开始日期').isoformat())
    if end_date:
        conditions.append('start_date <= ?')
        params.append(parse_date(end_date, '结束日期').isoformat())

    where_clause = ''
    if conditions:
        where_clause = 'WHERE ' + ' AND '.join(conditions)
    sql = f'SELECT * FROM leaves {where_clause} ORDER BY start_date DESC, id DESC'

    conn = get_db()
    try:
        rows = conn.execute(sql, params).fetchall()
    finally:
        conn.close()
    items = [Leave.from_row(row).to_dict() for row in rows]
    return {'total': len(items), 'items': items}


# 审批状态的中文说明，用于给调用方可读的提示
STATUS_LABELS = {'approved': '通过', 'rejected': '驳回'}


def _review_leave(leave_id, payload, target_status):
    """请假审批的统一实现，保证状态只能从 pending 流转一次"""
    leave = get_leave(leave_id)
    if leave.status != 'pending':
        label = STATUS_LABELS.get(leave.status, leave.status)
        raise ServiceError(f'该请假申请已经{label}，不能重复处理')

    if not isinstance(payload, dict):
        payload = {}
    approver = clean_text(payload.get('approver'), '审批人', required=True, max_length=50)
    comment = clean_text(payload.get('comment'), '审批意见', max_length=200)

    conn = get_db()
    try:
        # 审批通过前必须复查冲突：
        # 提交申请时如果还有另一条 pending 请假，两条都可以提交成功，
        # 但先被审批的那条会变成 approved，此时后一条再审批就会造成区间重叠。
        if target_status == 'approved':
            conflict = conn.execute(
                '''
                SELECT id FROM leaves
                WHERE employee_id = ?
                  AND id != ?
                  AND status = 'approved'
                  AND start_date <= ?
                  AND end_date >= ?
                LIMIT 1
                ''',
                (leave.employee_id, leave.id, leave.end_date, leave.start_date),
            ).fetchone()
            if conflict is not None:
                raise ServiceError('该请假申请与已审批的请假时间冲突，不能通过')

        conn.execute(
            '''
            UPDATE leaves
            SET status = ?, approver = ?, approve_comment = ?,
                updated_at = datetime('now', 'localtime')
            WHERE id = ?
            ''',
            (target_status, approver, comment or None, leave.id),
        )
        conn.commit()
    finally:
        conn.close()
    return get_leave(leave.id)


def approve_leave(leave_id, payload=None):
    """审批通过请假申请"""
    return _review_leave(leave_id, payload, 'approved')


def reject_leave(leave_id, payload=None):
    """驳回请假申请"""
    return _review_leave(leave_id, payload, 'rejected')
