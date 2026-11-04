# 业务异常定义
# 全局异常处理器依赖该类型返回统一错误响应


class ServiceError(Exception):
    """可预期业务错误"""

    def __init__(self, message, code=400):
        super().__init__(message)
        self.message = message
        self.code = code
