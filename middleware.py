import logging
import time
import uuid
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from config import get_settings

settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger("vesper")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id
        
        start_time = time.time()
        
        logger.info(
            f"[{request_id}] {request.method} {request.url.path} - Started",
            extra={"request_id": request_id}
        )
        
        try:
            response = await call_next(request)
            process_time = (time.time() - start_time) * 1000
            
            logger.info(
                f"[{request_id}] {request.method} {request.url.path} - "
                f"{response.status_code} ({process_time:.2f}ms)",
                extra={"request_id": request_id}
            )
            
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time-Ms"] = f"{process_time:.2f}"
            
            return response
            
        except Exception as e:
            process_time = (time.time() - start_time) * 1000
            logger.error(
                f"[{request_id}] {request.method} {request.url.path} - "
                f"ERROR: {str(e)} ({process_time:.2f}ms)",
                exc_info=True,
                extra={"request_id": request_id}
            )
            raise
