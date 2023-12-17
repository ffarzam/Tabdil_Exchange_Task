import json
import logging
import re
import time
import traceback
from uuid import uuid4

from rest_framework import status

from accounts.utils import get_client_ip_address

logger = logging.getLogger('elastic_logger')


class ElasticAPILoggerMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        unique_id = request.headers.get("unique_id")

        if not unique_id:
            unique_id = uuid4().hex
        setattr(request, "unique_id", unique_id)

        path_blacklist = self.get_blacklist(request)
        start_time = time.perf_counter_ns()

        response = self.get_response(request)
        end_time = time.perf_counter_ns()
        process_time = end_time - start_time

        if len(path_blacklist) == 0 and not request.META.get("exception", False):
            user = self.find_user(request)
            log_data = self.api_log_data(request, response, user)
            log_data['process_time'] = process_time / (10 ** 9)

            logger.info(json.dumps(log_data))

        response.headers["unique_id"] = unique_id
        return response

    def process_exception(self, request, exception):
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        path_blacklist = self.get_blacklist(request)
        if len(path_blacklist) == 0:
            log_data = self.exception_log_data(request, exception)
            log_data['response_status'] = status_code
            logger.error(json.dumps(log_data))
            request.META["exception"] = True

    @staticmethod
    def find_user(request):
        user = None
        if request.user.is_authenticated:
            user = request.user
        return user

    @staticmethod
    def api_log_data(request, response, user):
        return {
            "unique_id": request.unique_id,
            'request_method': request.method,
            'request_path': request.path,
            'request_ip': get_client_ip_address(request) or ' ',
            'request_user_agent': request.META.get('HTTP_USER_AGENT', ' '),
            'user_id': str(user.id) if user else " ",
            'response_status': response.status_code,
            'event': f"api.{request.resolver_match.app_names[0]}.{request.resolver_match.url_name}"
            if request.resolver_match and len(request.resolver_match.app_names) != 0
            else " "
        }

    @staticmethod
    def exception_log_data(request, exception):
        return {
            "unique_id": request.unique_id,
            'request_method': request.method,
            'request_path': request.path,
            'request_ip': get_client_ip_address(request) or ' ',
            'request_user_agent': request.META.get('HTTP_USER_AGENT', ' '),
            'exception_type': exception.__class__.__name__,
            'exception_message': str(exception),
            'exception_traceback': traceback.format_exc(),
            'event': f"api.{request.resolver_match.app_names[0]}.{request.resolver_match.url_name}"
            if request.resolver_match and len(request.resolver_match.app_names) != 0
            else " ",
            'exception': True,
        }

    @staticmethod
    def get_blacklist(request):
        lst = ['admin', "favicon.ico", ]
        path_blacklist = list(filter(lambda x: re.match(rf"(/..|)/({x})(/.*|)$", request.path), lst))
        return path_blacklist
