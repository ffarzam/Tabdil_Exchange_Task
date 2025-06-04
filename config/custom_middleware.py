import logging
import re
import time
import traceback
from uuid import uuid4

from rest_framework import status

api_logger = logging.getLogger("api")
exception_logger = logging.getLogger("exception")


class ElasticAPILoggerMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        correlation_id = request.headers.get("correlation-id")

        if not correlation_id:
            correlation_id = uuid4().hex
        setattr(request, "correlation_id", correlation_id)

        path_whitelist = self.get_whitelist(request)
        start_time = time.monotonic()
        response = self.get_response(request)
        process_time = time.monotonic() - start_time
        if path_whitelist and response.status_code != 500:
            user = self.find_user(request)
            log_data = self.api_log_data(request, response, user, process_time)
            api_logger.info("api", extra=log_data)

        return response

    def process_exception(self, request, exception):
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        path_whitelist = self.get_whitelist(request)
        if path_whitelist:
            log_data = self.exception_log_data(request, exception)
            log_data["response_status"] = status_code
            exception_logger.error("exception", extra=log_data)

    @staticmethod
    def find_user(request):
        user = None
        if request.user.is_authenticated:
            user = request.user
        return user

    @staticmethod
    def api_log_data(request, response, user, time):
        return {
            "correlation_id": request.correlation_id,
            "request_method": request.method,
            "request_path": request.path,
            "request_user_agent": request.META.get("HTTP_USER_AGENT", " "),
            "user_id": str(user.id) if user else " ",
            "response_status": response.status_code,
            "response_time": time,
            "api": True,
        }

    @staticmethod
    def exception_log_data(request, exception):
        return {
            "correlation_id": request.correlation_id,
            "request_method": request.method,
            "request_path": request.path,
            "request_user_agent": request.META.get("HTTP_USER_AGENT", " "),
            "exception_type": exception.__class__.__name__,
            "exception_message": str(exception),
            "exception_traceback": traceback.format_exc(),
            "exception": True,
        }

    @staticmethod
    def get_whitelist(request):
        versions = [
            "/v1",
        ]
        pattern = rf"^({'|'.join(map(re.escape, versions))})/.*$"
        if re.match(pattern, request.path):
            return True
        return False
