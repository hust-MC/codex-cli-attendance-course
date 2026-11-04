# 加班业务服务
# 负责加班申请、时长校验和审批状态流转
import sqlite3

from db import get_db
from models.overtime import Overtime
from services import employee_service
from services.errors import ServiceError
from services.validators import clean_text, parse_date, parse_positive_int


# 加班时长上限，普通工作日不可能超过 24 小时
MAX_OVERTIME_HOURS = 24

# 审批状态的中文说明，用于给调用方可读的提示
STATUS_LABELS = {'approved': '通过', 'rejected': '驳回'}


def _parse_hours(value):
    """校验加班时长"""
    if isinstance(value, bool):
        raise ServiceError('加班时长必须是数字')
    try:
        hours = float(value)
    except (TypeError, ValueError) as exc:
        raise ServiceError('加班时长必须是数字') from exc
    if hours <= 0:
        raise ServiceError('加班时长必须大于 0 小时')
    if hours > MAX_OVERTIME_HOURS:
        raise ServiceError(f'加班时长不能超过 {MAX_OVERTIME_HOURS} 小时')
    return hours


def create_overtime(payload):
    """提交加班申请"""
    if not isinstance(payload, dict):
        raise ServiceError('请求体必须是 JSON 对象')

    employee = employee_service.get_employee(payload.get('employee_id'))
    employee_service.ensure_employee_active(employee)

    work_date = parse_date(payload.get('work_date'), '加班日期')
    hours = _parse_hours(payload.get('hours'))
    reason = clean_text(payload.get('reason'), '加班原因', max_length=200)

    conn = get_db()
    try:
        cursor = conn.execute(
            '''
            INSERT INTO overtimes (employee_id, work_date, hours, reason)
            VALUES (?, ?, ?, ?)
            ''',
            (employee.id, work_date.isoformat(), hours, reason or None),
        )
        conn.commit()
        row = conn.execute(
            'SELECT * FROM overtimes WHERE id = ?',
            (cursor.lastrowid,),
        ).fetchone()
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        raise ServiceError('该员工当天已经提交过加班申请') from exc
    finally:
        conn.close()
    return Overtime.from_row(row)


def get_overtime(overtime_id):
    """查询加班申请详情"""
    overtime_id = parse_positive_int(overtime_id, '加班编号')
    conn = get_db()
    try:
        row = conn.execute('SELECT * FROM overtimes WHERE id = ?', (overtime_id,)).fetchone()
    finally:
        conn.close()
    if row is None:
        raise ServiceError('加班申请不存在', code=404)
    return Overtime.from_row(row)


def list_overtimes(employee_id=None, status=None, start_date=None, end_date=None):
    """查询加班列表，可按员工、状态和日期区间筛选"""
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
        conditions.append('work_date >= ?')
        params.append(parse_date(start_date, '开始日期').isoformat())
    if end_date:
        conditions.append('work_date <= ?')
        params.append(parse_date(end_date, '结束日期').isoformat())

    where_clause = ''
    if conditions:
        where_clause = 'WHERE ' + ' AND '.join(conditions)
    sql = f'SELECT * FROM overtimes {where_clause} ORDER BY work_date DESC, id DESC'

    conn = get_db()
    try:
        rows = conn.execute(sql, params).fetchall()
    finally:
        conn.close()
    items = [Overtime.from_row(row).to_dict() for row in rows]
    return {'total': len(items), 'items': items}


def _review_overtime(overtime_id, payload, target_status):
    """加班审批的统一实现，保证状态只能从 pending 流转一次"""
    overtime = get_overtime(overtime_id)
    if overtime.status != 'pending':
        label = STATUS_LABELS.get(overtime.status, overtime.status)
        raise ServiceError(f'该加班申请已经{label}，不能重复审批')

    if not isinstance(payload, dict):
        payload = {}
    approver = clean_text(payload.get('approver'), '审批人', required=True, max_length=50)
    comment = clean_text(payload.get('comment'), '审批意见', max_length=200)

    conn = get_db()
    try:
        conn.execute(
            '''
            UPDATE overtimes
            SET status = ?, approver = ?, approve_comment = ?,
                updated_at = datetime('now', 'localtime')
            WHERE id = ?
            ''',
            (target_status, approver, comment or None, overtime.id),
        )
        conn.commit()
    finally:
        conn.close()
    return get_overtime(overtime.id)


def approve_overtime(overtime_id, payload=None):
    """审批通过加班申请"""
    return _review_overtime(overtime_id, payload, 'approved')


def reject_overtime(overtime_id, payload=None):
    """驳回加班申请"""
    return _review_overtime(overtime_id, payload, 'rejected')
