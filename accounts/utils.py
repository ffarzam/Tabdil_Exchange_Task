import datetime
# import json

import jwt
# import six
from django.conf import settings
from uuid import uuid4

# from django.core.mail import EmailMessage, send_mail
# from django_celery_beat.models import CrontabSchedule, PeriodicTask
# from django.contrib.auth.tokens import PasswordResetTokenGenerator
#
# from .publisher import publish


def generate_access_token(user_id, jti):
    access_token_payload = {
        "token_type": "access",
        'user_id': user_id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(seconds=settings.ACCESS_TOKEN_TTL),
        'iat': datetime.datetime.utcnow(),
        'jti': jti,
    }
    access_token = encode_jwt(access_token_payload)
    return access_token


def generate_refresh_token(user_id, jti):
    refresh_token_payload = {
        "token_type": "refresh",
        'user_id': user_id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(seconds=settings.REFRESH_TOKEN_TTL),
        'iat': datetime.datetime.utcnow(),
        'jti': jti,
    }
    refresh_token = encode_jwt(refresh_token_payload)
    return refresh_token


def jti_maker():
    return uuid4().hex


def decode_jwt(token):
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
    return payload


def encode_jwt(payload):
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
    return token


def cache_key_parser(arg):
    return arg.split(" || ")


def cache_key_setter(user_id, jti):
    return f"user_{user_id} || {jti}"


def cache_value_setter(request):
    return request.META.get('HTTP_USER_AGENT', 'UNKNOWN')


# def send_email(data):
#     content = data.get("content_subtype")
#     email = EmailMessage(
#         subject=data['email_subject'],
#         body=data["email_body"],
#         to=data["to_email"]
#     )
#
#     if content == "html":
#         email.content_subtype = content
#     email.send(fail_silently=False)


# def create_periodic_task(instance):
#     schedule, _ = CrontabSchedule.objects.get_or_create(minute=instance.broadcast_on.minute,
#                                                         hour=instance.broadcast_on.hour,
#                                                         day_of_month=instance.broadcast_on.day,
#                                                         month_of_year=instance.broadcast_on.month)
#     task = PeriodicTask.objects.create(crontab=schedule,
#                                        name=f"broadcast notification {instance.id}",
#                                        task="accounts.tasks.broadcast_notification",
#                                        args=json.dumps([instance.id]),
#                                        one_off=True,
#                                        )


def get_client_ip_address(request):
    req_headers = request.META
    x_forwarded_for_value = req_headers.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for_value:
        ip_addr = x_forwarded_for_value.split(',')[-1].strip()
    else:
        ip_addr = req_headers.get('REMOTE_ADDR')
    return ip_addr


# def publisher(request, user, message, routing_key):
#     info = {
#         "unique_id": request.unique_id,
#         "username": user.username,
#         "message": message,
#         "routing_key": routing_key,
#         "user_agent": request.META.get('HTTP_USER_AGENT', 'UNKNOWN'),
#         "ip": get_client_ip_address(request) or " "
#     }
#     publish(info)


def set_token(request, user, caches):
    jti = jti_maker()
    access_token = generate_access_token(user.id, jti)
    refresh_token = generate_refresh_token(user.id, jti)

    key = cache_key_setter(user.id, jti)
    value = cache_value_setter(request)
    caches['auth'].set(key, value)
    return access_token, refresh_token


# class AccountActivationTokenGenerator(PasswordResetTokenGenerator):
#     def _make_hash_value(self, user, timestamp):
#         return six.text_type(user.pk) + six.text_type(timestamp) + six.text_type(user.is_account_enable)