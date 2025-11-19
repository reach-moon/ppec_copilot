# app/core/exceptions.py
class PpecCopilotException(Exception):
    """项目自定义异常基类"""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

class ServiceUnavailableException(PpecCopilotException):
    """外部服务不可用异常"""
    pass

class InvalidInputException(PpecCopilotException):
    """用户输入无效异常"""
    pass