# 通用参数校验工具
# 各业务模块共用，避免每个模块重复写一遍解析逻辑
from datetime import date, datetime

from services.errors import ServiceError


def clean_text(value, field_name, required=False, max_length=100):
    """清理并校验文本字段"""
    if value is None:
        value = ''
    if not isinstance(value, str):
        raise ServiceError(f'{field_name}必须是字符串')
    value = value.strip()
    if required and not value:
        raise ServiceError(f'{field_name}不能为空')
    if len(value) > max_length:
        raise ServiceError(f'{field_name}不能超过 {max_length} 个字符')
    return value


def parse_positive_int(value, field_name):
    """校验正整数编号"""
    if isinstance(value, bool):
        raise ServiceError(f'{field_name}必须是正整数')
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ServiceError(f'{field_name}必须是正整数') from exc
    if parsed <= 0:
        raise ServiceError(f'{field_name}必须是正整数')
    return parsed


def parse_date(value, field_name):
    """校验 YYYY-MM-DD 格式的日期"""
    if not isinstance(value, str) or not value.strip():
        raise ServiceError(f'{field_name}格式必须是 YYYY-MM-DD')
    try:
        return datetime.strptime(value.strip(), '%Y-%m-%d').date()
    except ValueError as exc:
        raise ServiceError(f'{field_name}格式必须是 YYYY-MM-DD') from exc


def parse_choice(value, field_name, choices):
    """校验取值必须落在允许范围内"""
    if value not in choices:
        raise ServiceError(f'{field_name}只能是 {"/".join(choices)}')
    return value


def inclusive_days(start_date, end_date):
    """计算包含首尾两天的自然日天数"""
    return (end_date - start_date).days + 1
