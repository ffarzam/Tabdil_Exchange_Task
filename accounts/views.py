from django.contrib.auth import authenticate
from django.core.cache import caches
from django.db import transaction
from django.db.models import Q
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .authentication import RefreshTokenAuthentication, AccessTokenAuthentication
from .models import User
from .serializers import SellerRegisterSerializer, SellerLoginSerializer
from .utils import set_token, cache_key_parser
from charging.models import Seller
from permissions import IsSuperuser


# Create your views here.

class SellerRegister(APIView):
    permission_classes = (AllowAny,)
    serializer_class = SellerRegisterSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            user = serializer.create(serializer.validated_data)
            Seller.objects.create(user=user)

        request.user = user
        return Response({'message': "Registered successfully"}, status=status.HTTP_201_CREATED)


class SellerLogin(APIView):
    permission_classes = (AllowAny,)
    serializer_class = SellerLoginSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        user_identifier = serializer.validated_data.get('user_identifier')
        password = serializer.validated_data.get('password')
        user = authenticate(request, user_identifier=user_identifier, password=password)
        if user is None:
            return Response({'message': 'Invalid credentials'}, status=status.HTTP_400_BAD_REQUEST)
        elif not user.is_active:
            return Response({'message': "User is Banned"}, status=status.HTTP_404_NOT_FOUND)

        access_token, refresh_token = set_token(request, user, caches)
        data = {"access": access_token, "refresh": refresh_token}
        request.user = user
        return Response({"message": "Logged in successfully", "data": data}, status=status.HTTP_201_CREATED)


class RefreshToken(APIView):
    authentication_classes = (RefreshTokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        user = request.user
        payload = request.auth

        jti = payload["jti"]
        caches['auth'].delete(f'user_{user.id} || {jti}')

        access_token, refresh_token = set_token(request, user, caches)
        data = {"access": access_token, "refresh": refresh_token}

        return Response(data, status=status.HTTP_201_CREATED)


class LogoutView(APIView):
    authentication_classes = (RefreshTokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def delete(self, request):
        payload = request.auth
        user = request.user
        jti = payload["jti"]
        caches['auth'].delete(f'user_{user.id} || {jti}')

        return Response({"message": "Logged out successfully"}, status=status.HTTP_200_OK)


class CheckAllActiveLogin(APIView):
    authentication_classes = (AccessTokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        user = request.user

        active_login_data = []
        for key, value in caches['auth'].get_many(caches['auth'].keys(f'user_{user.id} || *')).items():
            jti = cache_key_parser(key)[1]

            active_login_data.append({
                "jti": jti,
                "user_agent": value,
            })

        return Response(active_login_data, status=status.HTTP_200_OK)


class LogoutAll(APIView):
    authentication_classes = (RefreshTokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def delete(self, request):
        user = request.user
        caches['auth'].delete_many(caches['auth'].keys(f'user_{user.id} || *'))

        return Response({"message": "All accounts logged out"}, status=status.HTTP_200_OK)


class SelectedLogout(APIView):
    authentication_classes = (AccessTokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def delete(self, request):
        user = request.user
        jti = request.data.get("jti")
        caches['auth'].delete(f'user_{user.id} || {jti}')

        return Response({"message": "Chosen account was successfully logged out"}, status=status.HTTP_200_OK)


