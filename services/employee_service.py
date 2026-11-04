# 员工业务服务
# 负责员工参数校验、数据库读写和逻辑离职
import sqlite3

from db import get_db
from models.employee import Employee
from services.errors import ServiceError
from services.validators import clean_text, parse_positive_int


def get_employee(employee_id):
    """查询员工详情"""
    employee_id = parse_positive_int(employee_id, '员工编号')
    conn = get_db()
    try:
        row = conn.execute(
            'SELECT * FROM employees WHERE id = ?',
            (employee_id,),
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        raise ServiceError('员工不存在', code=404)
    return Employee.from_row(row)


def ensure_employee_active(employee, action='提交申请'):
    """确认员工仍在职，离职员工不能继续操作"""
    if employee.status != 'active':
        raise ServiceError(f'员工已离职，不能{action}')


def create_employee(payload):
    """新增员工"""
    if not isinstance(payload, dict):
        raise ServiceError('请求体必须是 JSON 对象')
    name = clean_text(payload.get('name'), '姓名', required=True, max_length=50)
    department = clean_text(payload.get('department'), '部门', required=True, max_length=50)
    employee_no = clean_text(payload.get('employee_no'), '工号', required=True, max_length=30)
    phone = clean_text(payload.get('phone'), '手机号', max_length=20)

    conn = get_db()
    try:
        cursor = conn.execute(
            '''
            INSERT INTO employees (name, department, employee_no, phone)
            VALUES (?, ?, ?, ?)
            ''',
            (name, department, employee_no, phone or None),
        )
        conn.commit()
        row = conn.execute(
            'SELECT * FROM employees WHERE id = ?',
            (cursor.lastrowid,),
        ).fetchone()
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        raise ServiceError('工号已存在') from exc
    finally:
        conn.close()
    return Employee.from_row(row)


def list_employees(keyword=None, department=None, status=None):
    """查询员工列表，可按关键字、部门和在职状态筛选"""
    keyword = clean_text(keyword, '关键字', max_length=50)
    department = clean_text(department, '部门', max_length=50)
    status = clean_text(status, '在职状态', max_length=20)

    conditions = []
    params = []

    if keyword:
        conditions.append('(name LIKE ? OR employee_no LIKE ?)')
        value = f'%{keyword}%'
        params.extend([value, value])
    if department:
        conditions.append('department = ?')
        params.append(department)
    if status:
        conditions.append('status = ?')
        params.append(status)

    where_clause = ''
    if conditions:
        where_clause = 'WHERE ' + ' AND '.join(conditions)
    sql = f'SELECT * FROM employees {where_clause} ORDER BY id DESC'

    conn = get_db()
    try:
        rows = conn.execute(sql, params).fetchall()
    finally:
        conn.close()
    items = [Employee.from_row(row).to_dict() for row in rows]
    return {'total': len(items), 'items': items}


def update_employee(employee_id, payload):
    """修改员工信息，在职状态只能通过离职接口变更"""
    if not isinstance(payload, dict):
        raise ServiceError('请求体必须是 JSON 对象')
    employee = get_employee(employee_id)
    name = employee.name
    department = employee.department
    employee_no = employee.employee_no
    phone = employee.phone or ''

    if 'name' in payload:
        name = clean_text(payload.get('name'), '姓名', required=True, max_length=50)
    if 'department' in payload:
        department = clean_text(payload.get('department'), '部门', required=True, max_length=50)
    if 'employee_no' in payload:
        employee_no = clean_text(payload.get('employee_no'), '工号', required=True, max_length=30)
    if 'phone' in payload:
        phone = clean_text(payload.get('phone'), '手机号', max_length=20)

    conn = get_db()
    try:
        conn.execute(
            '''
            UPDATE employees
            SET name = ?, department = ?, employee_no = ?, phone = ?
            WHERE id = ?
            ''',
            (name, department, employee_no, phone or None, employee.id),
        )
        conn.commit()
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        raise ServiceError('工号已存在') from exc
    finally:
        conn.close()
    return get_employee(employee.id)


def delete_employee(employee_id):
    """员工离职，采用逻辑离职保留历史考勤数据"""
    employee = get_employee(employee_id)
    if employee.status != 'active':
        raise ServiceError('员工已经离职，不能重复操作')

    conn = get_db()
    try:
        conn.execute(
            '''
            UPDATE employees
            SET status = 'quit'
            WHERE id = ?
            ''',
            (employee.id,),
        )
        conn.commit()
    finally:
        conn.close()
    return get_employee(employee.id).to_dict()
