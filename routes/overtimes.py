# 加班管理路由
# 只接收 HTTP 参数并调用 service
from flask import Blueprint, request

from routes.common import get_json_object, success
from services import overtime_service


overtimes_bp = Blueprint('overtimes', __name__, url_prefix='/api/overtimes')


@overtimes_bp.post('')
def create_overtime():
    """提交加班申请"""
    overtime = overtime_service.create_overtime(get_json_object())
    return success(overtime.to_dict(), '加班申请已提交')


@overtimes_bp.get('')
def list_overtimes():
    """查询加班列表"""
    data = overtime_service.list_overtimes(
        employee_id=request.args.get('employee_id'),
        status=request.args.get('status'),
        start_date=request.args.get('start_date'),
        end_date=request.args.get('end_date'),
    )
    return success(data)


@overtimes_bp.get('/<int:overtime_id>')
def get_overtime(overtime_id):
    """查询加班申请详情"""
    overtime = overtime_service.get_overtime(overtime_id)
    return success(overtime.to_dict())


@overtimes_bp.post('/<int:overtime_id>/approve')
def approve_overtime(overtime_id):
    """审批通过加班申请"""
    overtime = overtime_service.approve_overtime(overtime_id, get_json_object())
    return success(overtime.to_dict(), '加班申请已通过')


@overtimes_bp.post('/<int:overtime_id>/reject')
def reject_overtime(overtime_id):
    """驳回加班申请"""
    overtime = overtime_service.reject_overtime(overtime_id, get_json_object())
    return success(overtime.to_dict(), '加班申请已驳回')
