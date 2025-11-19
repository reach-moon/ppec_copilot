from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.status import HTTP_503_SERVICE_UNAVAILABLE, HTTP_400_BAD_REQUEST, HTTP_500_INTERNAL_SERVER_ERROR

from app.core.exceptions import ServiceUnavailableException, InvalidInputException
from app.core.logging_config import logger

"""
处理服务不可用异常的处理器：当外部服务不可用时调用此处理器，记录错误日志并返回503状态码

Args:
    request (Request): FastAPI请求对象
    exc (ServiceUnavailableException): 服务不可用异常实例

Returns:
    JSONResponse: 包含错误详情的JSON响应，状态码为503
"""
async def service_unavailable_handler(request: Request, exc: ServiceUnavailableException):
    logger.error(f"外部服务不可用: {exc.message}", exc_info=True)
    return JSONResponse(
        status_code=HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": f"Service is currently unavailable: {exc.message}"},
    )

async def invalid_input_handler(request: Request, exc: InvalidInputException):
    logger.warning(f"无效的输入: {exc.message}")
    return JSONResponse(
        status_code=HTTP_400_BAD_REQUEST,
        content={"detail": f"Invalid input: {exc.message}"},
    )

async def generic_exception_handler(request: Request, exc: Exception):
    logger.critical(f"未处理的服务器错误: {exc}", exc_info=True)
    return JSONResponse(
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred."},
    )