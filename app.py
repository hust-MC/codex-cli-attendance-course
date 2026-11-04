# Flask 应用入口
# 负责创建应用、注册路由和统一异常响应
import os

from flask import Flask, jsonify

from db import init_db
from routes import register_blueprints
from services.errors import ServiceError


def create_app():
    """创建并配置 Flask 应用"""
    app = Flask(__name__)
    app.json.ensure_ascii = False
    register_blueprints(app)

    @app.get('/api/health')
    def health_check():
        """健康检查接口"""
        return jsonify({'code': 200, 'message': '服务正常', 'data': None})

    @app.errorhandler(ServiceError)
    def handle_service_error(error):
        """将业务异常转换为统一响应"""
        return jsonify({
            'code': error.code,
            'message': error.message,
            'data': None,
        }), error.code

    @app.errorhandler(404)
    def handle_not_found(error):
        """处理不存在的接口"""
        return jsonify({'code': 404, 'message': '接口不存在', 'data': None}), 404

    @app.errorhandler(405)
    def handle_method_not_allowed(error):
        """处理不支持的请求方法"""
        return jsonify({'code': 405, 'message': '请求方法不支持', 'data': None}), 405

    @app.errorhandler(500)
    def handle_internal_error(error):
        """处理未预期异常"""
        return jsonify({'code': 500, 'message': '服务器内部错误', 'data': None}), 500

    with app.app_context():
        init_db()
    return app


app = create_app()


if __name__ == '__main__':
    debug_enabled = os.environ.get('FLASK_DEBUG', '1') == '1'
    # 端口可以用 PORT 环境变量覆盖，方便测试脚本使用独立端口
    port = int(os.environ.get('PORT', '3000'))
    app.run(host='0.0.0.0', port=port, debug=debug_enabled)
