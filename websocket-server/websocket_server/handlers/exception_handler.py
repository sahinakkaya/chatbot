import logging
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


def validation_exception_handler(request, exc):
    logger.error(f"Validation error: {exc}", exc_info=True)
    first_error = exc.errors()[0]
    return JSONResponse(
        status_code=422,
        content={"detail": first_error.get("msg"), "title": "Validation Error"},
    )


def general_exception_handler(request, exc):
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error", "title": "Server Error"},
    )
