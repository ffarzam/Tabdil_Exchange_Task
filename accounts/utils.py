import datetime
import jwt

from django.conf import settings
from uuid import uuid4


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


def get_client_ip_address(request):
    req_headers = request.META
    x_forwarded_for_value = req_headers.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for_value:
        ip_addr = x_forwarded_for_value.split(',')[-1].strip()
    else:
        ip_addr = req_headers.get('REMOTE_ADDR')
    return ip_addr


def set_token(request, user, caches):
    jti = jti_maker()
    access_token = generate_access_token(user.id, jti)
    refresh_token = generate_refresh_token(user.id, jti)

    key = cache_key_setter(user.id, jti)
    value = cache_value_setter(request)
    caches['auth'].set(key, value)
    return access_token, refresh_token
