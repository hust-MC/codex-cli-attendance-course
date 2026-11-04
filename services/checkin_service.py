# 打卡业务服务
# 负责签到、签出、重复校验和记录查询
import sqlite3
from datetime import datetime

from db import get_db
from models.checkin import Checkin
from services import employee_service
from services.errors import ServiceError
from services.validators import clean_text


TIME_FORMATS = (
    '%Y-%m-%d %H:%M:%S',
    '%Y-%m-%dT%H:%M:%S',
    '%Y-%m-%d %H:%M',
    '%Y-%m-%dT%H:%M',
)

# 打卡地点和备注仅用于补充业务信息，长度上限与同类文本字段保持一致
MAX_LOCATION_LENGTH = 100
MAX_REMARK_LENGTH = 200


def _parse_employee_id(value):
    """校验打卡请求中的员工编号"""
    if isinstance(value, bool):
        raise ServiceError('employee_id 必须是正整数')
    try:
        employee_id = int(value)
    except (TypeError, ValueError) as exc:
        raise ServiceError('employee_id 必须是正整数') from exc
    if employee_id <= 0:
        raise ServiceError('employee_id 必须是正整数')
    return employee_id


def _parse_check_time(value):
    """解析打卡时间，未传时使用当前时间"""
    if value is None or value == '':
        return datetime.now().replace(microsecond=0)
    if not isinstance(value, str):
        raise ServiceError('check_time 格式必须是 YYYY-MM-DD HH:MM:SS')
    normalized = value.strip()
    for time_format in TIME_FORMATS:
        try:
            return datetime.strptime(normalized, time_format)
        except ValueError:
            continue
    raise ServiceError('check_time 格式必须是 YYYY-MM-DD HH:MM:SS')


def _parse_work_date(value):
    """解析查询日期"""
    if value is None or value == '':
        return datetime.now().date().isoformat()
    if not isinstance(value, str):
        raise ServiceError('date 格式必须是 YYYY-MM-DD')
    try:
        return datetime.strptime(value.strip(), '%Y-%m-%d').date().isoformat()
    except ValueError as exc:
        raise ServiceError('date 格式必须是 YYYY-MM-DD') from exc


def _exists_check(conn, employee_id, check_type, work_date):
    """查询某天是否已有指定类型的打卡"""
    row = conn.execute(
        '''
        SELECT 1 FROM checkins
        WHERE employee_id = ? AND check_type = ? AND date(check_time) = ?
        LIMIT 1
        ''',
        (employee_id, check_type, work_date),
    ).fetchone()
    return row is not None


def create_checkin(payload, check_type):
    """创建签到或签出记录"""
    if not isinstance(payload, dict):
        raise ServiceError('请求体必须是 JSON 对象')
    if check_type not in ('in', 'out'):
        raise ServiceError('打卡类型不合法')

    employee_id = _parse_employee_id(payload.get('employee_id'))
    employee = employee_service.get_employee(employee_id)
    employee_service.ensure_employee_active(employee, '打卡')
    check_time = _parse_check_time(payload.get('check_time'))
    location = clean_text(
        payload.get('location'),
        '打卡地点',
        max_length=MAX_LOCATION_LENGTH,
    )
    remark = clean_text(
        payload.get('remark'),
        '打卡备注',
        max_length=MAX_REMARK_LENGTH,
    )
    work_date = check_time.date().isoformat()

    conn = get_db()
    try:
        if _exists_check(conn, employee_id, check_type, work_date):
            action = '签到' if check_type == 'in' else '签出'
            raise ServiceError(f'当天已经{action}，不能重复操作')
        if check_type == 'out' and not _exists_check(conn, employee_id, 'in', work_date):
            raise ServiceError('当天还没有签到，不能直接签出')

        cursor = conn.execute(
            '''
            INSERT INTO checkins (employee_id, check_type, check_time, location, remark)
            VALUES (?, ?, ?, ?, ?)
            ''',
            (
                employee_id,
                check_type,
                check_time.isoformat(sep=' '),
                location or None,
                remark or None,
            ),
        )
        conn.commit()
        row = conn.execute(
            'SELECT * FROM checkins WHERE id = ?',
            (cursor.lastrowid,),
        ).fetchone()
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        raise ServiceError('当天已经完成过该类型的打卡') from exc
    finally:
        conn.close()
    return Checkin.from_row(row)


def list_checkins(employee_id, date=None):
    """查询员工指定日期的打卡记录"""
    employee_id = _parse_employee_id(employee_id)
    employee_service.get_employee(employee_id)
    work_date = _parse_work_date(date)

    conn = get_db()
    try:
        rows = conn.execute(
            '''
            SELECT * FROM checkins
            WHERE employee_id = ? AND date(check_time) = ?
            ORDER BY check_time ASC, id ASC
            ''',
            (employee_id, work_date),
        ).fetchall()
    finally:
        conn.close()

    records = [Checkin.from_row(row).to_dict() for row in rows]
    first_in = next((item['check_time'] for item in records if item['check_type'] == 'in'), None)
    last_out = next(
        (item['check_time'] for item in reversed(records) if item['check_type'] == 'out'),
        None,
    )
    return {
        'employee_id': employee_id,
        'date': work_date,
        'first_in': first_in,
        'last_out': last_out,
        'records': records,
    }
