# 打卡路由
# 提供签到、签出和记录查询接口
from flask import Blueprint, request

from routes.common import get_json_object, success
from services import checkin_service


checkins_bp = Blueprint('checkins', __name__, url_prefix='/api/checkins')


@checkins_bp.post('/in')
def check_in():
    """上班签到"""
    checkin = checkin_service.create_checkin(get_json_object(), 'in')
    return success(checkin.to_dict(), '签到成功')


@checkins_bp.post('/out')
def check_out():
    """下班签出"""
    checkin = checkin_service.create_checkin(get_json_object(), 'out')
    return success(checkin.to_dict(), '签出成功')


@checkins_bp.get('')
def list_checkins():
    """查询指定员工和日期的打卡记录"""
    data = checkin_service.list_checkins(
        request.args.get('employee_id'),
        request.args.get('date'),
    )
    return success(data)
