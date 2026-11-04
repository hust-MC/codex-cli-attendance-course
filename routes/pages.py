# 页面路由
# 负责渲染考勤工作台，业务数据仍通过 /api 接口获取
from flask import Blueprint, render_template


pages_bp = Blueprint('pages', __name__)


@pages_bp.get('/')
def index():
    """渲染员工考勤工作台"""
    return render_template('index.html')
