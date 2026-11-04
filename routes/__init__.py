# 路由包
# 集中注册员工、打卡、请假和加班蓝图


def register_blueprints(app):
    """注册业务路由"""
    from routes.checkins import checkins_bp
    from routes.employees import employees_bp
    from routes.leaves import leaves_bp
    from routes.overtimes import overtimes_bp
    from routes.pages import pages_bp

    app.register_blueprint(pages_bp)
    app.register_blueprint(employees_bp)
    app.register_blueprint(checkins_bp)
    app.register_blueprint(leaves_bp)
    app.register_blueprint(overtimes_bp)
    return app
