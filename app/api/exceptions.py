"""
Custom exception classes and FastAPI exception handlers for the Video Caption Watermark API.

This module provides:
- Custom exception classes for each error category (validation, not found, processing, system)
- FastAPI exception handlers for consistent JSON error responses
- Protection against exposing internal error details in production

Error Response Format:
{
    "error_code": "ERROR_CODE",
    "message": "Human-readable message",
    "details": {...}  # Optional additional context
}

Validates: Requirements 1.3, 1.6, 2.8, 3.4, 4.2, 7.3, 7.4, 7.5
"""

from typing import Optional, Dict, Any
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# Custom Exception Classes
# ============================================================================

class APIException(Exception):
    """
    Base exception class for all API exceptions.
    
    Provides a consistent structure for error responses with
    error_code, message, details, and HTTP status code.
    """
    
    def __init__(
        self,
        error_code: str,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)


# ============================================================================
# Not Found Exceptions (404)
# ============================================================================

class VideoNotFoundError(APIException):
    """
    Raised when a requested video does not exist.
    
    Validates: Requirements 1.6
    """
    
    def __init__(self, video_id: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code="VIDEO_NOT_FOUND",
            message=f"Video with ID '{video_id}' not found",
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
        )
        self.video_id = video_id


class WatermarkNotFoundError(APIException):
    """
    Raised when a requested watermark does not exist.
    
    Validates: Requirements 4.2
    """
    
    def __init__(self, watermark_id: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code="WATERMARK_NOT_FOUND",
            message=f"Watermark with ID '{watermark_id}' not found",
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
        )
        self.watermark_id = watermark_id


class JobNotFoundError(APIException):
    """
    Raised when a requested job does not exist.
    
    Validates: Requirements 6.5
    """
    
    def __init__(self, job_id: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code="JOB_NOT_FOUND",
            message=f"Job with ID '{job_id}' not found",
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
        )
        self.job_id = job_id


class CaptionNotFoundError(APIException):
    """
    Raised when captions have not been generated for a video yet.
    
    Validates: Requirements 3.1
    """
    
    def __init__(self, video_id: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code="CAPTION_NOT_FOUND",
            message=f"Captions not found for video '{video_id}'. Generate captions first.",
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
        )
        self.video_id = video_id


# ============================================================================
# Validation Exceptions (400)
# ============================================================================

class InvalidFormatError(APIException):
    """
    Raised when an uploaded file has an unsupported format.
    
    Validates: Requirements 1.3, 4.2
    """
    
    def __init__(
        self,
        message: str,
        provided_format: Optional[str] = None,
        supported_formats: Optional[list] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_details = details or {}
        if provided_format is not None:
            error_details["provided_format"] = provided_format
        if supported_formats is not None:
            error_details["supported_formats"] = supported_formats
        
        super().__init__(
            error_code="INVALID_FORMAT",
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=error_details if error_details else None,
        )


class InvalidParameterError(APIException):
    """
    Raised when a request parameter has an invalid value.
    
    Validates: Requirements 3.4
    """
    
    def __init__(
        self,
        message: str,
        parameter_name: Optional[str] = None,
        provided_value: Optional[Any] = None,
        allowed_values: Optional[list] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_details = details or {}
        if parameter_name is not None:
            error_details["parameter"] = parameter_name
        if provided_value is not None:
            error_details["provided_value"] = str(provided_value)
        if allowed_values is not None:
            error_details["allowed_values"] = allowed_values
        
        super().__init__(
            error_code="INVALID_PARAMETER",
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=error_details if error_details else None,
        )


# ============================================================================
# Processing Exceptions (500)
# ============================================================================

class ProcessingError(APIException):
    """
    Base class for processing-related errors.
    
    Used for errors that occur during video/audio processing operations.
    """
    
    def __init__(
        self,
        error_code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            error_code=error_code,
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
        )


class AudioExtractionError(ProcessingError):
    """
    Raised when audio extraction from video fails.
    
    Validates: Requirements 2.8
    """
    
    def __init__(self, message: str = "Failed to extract audio from video", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code="AUDIO_EXTRACTION_FAILED",
            message=message,
            details=details,
        )


class TranscriptionError(ProcessingError):
    """
    Raised when speech-to-text transcription fails.
    
    Validates: Requirements 2.8
    """
    
    def __init__(self, message: str = "Speech-to-text processing failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code="TRANSCRIPTION_FAILED",
            message=message,
            details=details,
        )


class FFmpegError(ProcessingError):
    """
    Raised when FFmpeg processing fails.
    
    Validates: Requirements 5.1, 5.2
    """
    
    def __init__(self, message: str = "FFmpeg processing failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            error_code="FFMPEG_ERROR",
            message=message,
            details=details,
        )


# ============================================================================
# System Exceptions (500, 503)
# ============================================================================

class InternalError(APIException):
    """
    Raised for unexpected internal errors.
    
    This exception should be used as a catch-all for unexpected errors.
    The actual error details should be logged but not exposed to clients.
    
    Validates: Requirements 7.5
    """
    
    def __init__(
        self,
        message: str = "An unexpected internal error occurred",
        details: Optional[Dict[str, Any]] = None,
        log_message: Optional[str] = None,
    ):
        super().__init__(
            error_code="INTERNAL_ERROR",
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
        )
        # Store the detailed message for logging (not exposed to client)
        self.log_message = log_message


class ServiceUnavailableError(APIException):
    """
    Raised when a required service is unavailable.
    
    Used when Redis, FFmpeg, or other required services are not accessible.
    
    Validates: Requirements 9.3, 9.4
    """
    
    def __init__(
        self,
        service_name: str,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        error_message = message or f"Required service '{service_name}' is unavailable"
        error_details = details or {}
        error_details["service"] = service_name
        
        super().__init__(
            error_code="SERVICE_UNAVAILABLE",
            message=error_message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=error_details,
        )
        self.service_name = service_name


# ============================================================================
# Exception Handlers
# ============================================================================

async def api_exception_handler(request: Request, exc: APIException) -> JSONResponse:
    """
    Handle custom API exceptions and return consistent JSON error responses.
    
    Validates: Requirements 7.3
    """
    # Log the error with request context
    logger.warning(
        f"API Exception: {exc.error_code} - {exc.message}",
        extra={
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method,
        }
    )
    
    # If it's an InternalError with a log_message, log the detailed message
    if isinstance(exc, InternalError) and exc.log_message:
        logger.error(f"Internal error details: {exc.log_message}")
    
    response_body = {
        "error_code": exc.error_code,
        "message": exc.message,
        "details": exc.details,
    }
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response_body,
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handle FastAPI request validation errors and return field-level error details.
    
    Converts Pydantic validation errors into a consistent format with
    field names and error messages.
    
    Validates: Requirements 7.4
    """
    # Extract field-level errors from the validation exception
    field_errors = []
    for error in exc.errors():
        # Build the field path (e.g., "body.watermark_opacity" or "query.limit")
        location = error.get("loc", [])
        field_path = ".".join(str(loc) for loc in location)
        
        field_errors.append({
            "field": field_path,
            "message": error.get("msg", "Validation error"),
            "type": error.get("type", "value_error"),
        })
    
    logger.warning(
        f"Validation error on {request.method} {request.url.path}",
        extra={
            "errors": field_errors,
            "path": request.url.path,
            "method": request.method,
        }
    )
    
    response_body = {
        "error_code": "VALIDATION_ERROR",
        "message": "Request validation failed",
        "details": field_errors,
    }
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=response_body,
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle unexpected exceptions and return a generic error response.
    
    This handler catches all unhandled exceptions and returns a safe
    error response that doesn't expose internal details to clients.
    The actual exception is logged for debugging purposes.
    
    Validates: Requirements 7.5
    """
    # Log the full exception for debugging
    logger.exception(
        f"Unhandled exception on {request.method} {request.url.path}: {str(exc)}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "exception_type": type(exc).__name__,
        }
    )
    
    # Return a generic error response without exposing internal details
    response_body = {
        "error_code": "INTERNAL_ERROR",
        "message": "An unexpected internal error occurred",
        "details": None,
    }
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=response_body,
    )


# ============================================================================
# Exception Handler Registration
# ============================================================================

def register_exception_handlers(app: FastAPI) -> None:
    """
    Register all exception handlers with the FastAPI application.
    
    This function should be called during application startup to ensure
    all custom exceptions are properly handled.
    
    Args:
        app: The FastAPI application instance
        
    Validates: Requirements 7.3, 7.4, 7.5
    """
    # Register handler for custom API exceptions
    app.add_exception_handler(APIException, api_exception_handler)
    
    # Register handler for request validation errors (422)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    
    # Register handler for Pydantic validation errors
    app.add_exception_handler(ValidationError, validation_exception_handler)
    
    # Register catch-all handler for unexpected exceptions
    # This must be registered last to catch any unhandled exceptions
    app.add_exception_handler(Exception, generic_exception_handler)
    
    logger.info("Exception handlers registered successfully")
