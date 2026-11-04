# 请假管理路由
# 只接收 HTTP 参数并调用 service
from flask import Blueprint, request

from routes.common import get_json_object, success
from services import leave_service


leaves_bp = Blueprint('leaves', __name__, url_prefix='/api/leaves')


@leaves_bp.post('')
def create_leave():
    """提交请假申请"""
    leave = leave_service.create_leave(get_json_object())
    return success(leave.to_dict(), '请假申请已提交')


@leaves_bp.get('')
def list_leaves():
    """查询请假列表"""
    data = leave_service.list_leaves(
        employee_id=request.args.get('employee_id'),
        status=request.args.get('status'),
        start_date=request.args.get('start_date'),
        end_date=request.args.get('end_date'),
    )
    return success(data)


@leaves_bp.get('/<int:leave_id>')
def get_leave(leave_id):
    """查询请假详情"""
    leave = leave_service.get_leave(leave_id)
    return success(leave.to_dict())


@leaves_bp.post('/<int:leave_id>/approve')
def approve_leave(leave_id):
    """审批通过请假申请"""
    leave = leave_service.approve_leave(leave_id, get_json_object())
    return success(leave.to_dict(), '请假申请已通过')


@leaves_bp.post('/<int:leave_id>/reject')
def reject_leave(leave_id):
    """驳回请假申请"""
    leave = leave_service.reject_leave(leave_id, get_json_object())
    return success(leave.to_dict(), '请假申请已驳回')
