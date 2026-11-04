# 路由公共工具
# 统一成功响应和 JSON 请求体读取
from flask import jsonify, request

from services.errors import ServiceError


def success(data=None, message='操作成功'):
    """构造统一成功响应"""
    return jsonify({'code': 200, 'message': message, 'data': data})


def get_json_object():
    """读取并校验 JSON 请求体"""
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise ServiceError('请求体必须是 JSON 对象')
    return payload
