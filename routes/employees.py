# 员工管理路由
# 只接收 HTTP 参数并调用 service
from flask import Blueprint, request

from routes.common import get_json_object, success
from services import employee_service


employees_bp = Blueprint('employees', __name__, url_prefix='/api/employees')


@employees_bp.post('')
def create_employee():
    """新增员工"""
    employee = employee_service.create_employee(get_json_object())
    return success(employee.to_dict(), '员工创建成功')


@employees_bp.get('')
def list_employees():
    """查询员工列表"""
    data = employee_service.list_employees(
        keyword=request.args.get('keyword'),
        department=request.args.get('department'),
        status=request.args.get('status'),
    )
    return success(data)


@employees_bp.get('/<int:employee_id>')
def get_employee(employee_id):
    """查询员工详情"""
    employee = employee_service.get_employee(employee_id)
    return success(employee.to_dict())


@employees_bp.put('/<int:employee_id>')
def update_employee(employee_id):
    """修改员工信息"""
    employee = employee_service.update_employee(employee_id, get_json_object())
    return success(employee.to_dict(), '员工信息已更新')


@employees_bp.delete('/<int:employee_id>')
def delete_employee(employee_id):
    """删除员工"""
    data = employee_service.delete_employee(employee_id)
    return success(data, '员工已离职')
