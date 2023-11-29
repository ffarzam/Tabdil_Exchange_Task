import re

from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode

from rest_framework import serializers

from .models import User


class SellerRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('national_id', 'email', 'password', 'password2')

    def create(self, validated_data):
        print("7" * 100)
        del validated_data['password2']
        return User.objects.create_user(**validated_data)

    def validate_national_id(self, value):
        print("5" * 100)
        if not re.search(r'^\d{10}$', value):
            raise serializers.ValidationError('National ID is invalid')
        control_number = int(value[9])
        s = sum(int(value[x]) * (10 - x) for x in range(9)) % 11
        if (2 > s == control_number) or (2 <= s == 11 - control_number):
            return value
        else:
            raise serializers.ValidationError('National ID is invalid')

    def validate(self, data):
        print("6" * 100)
        if data['password'] != data['password2']:
            raise serializers.ValidationError("Passwords don't match")

        if data['password'] == data['email']:
            raise serializers.ValidationError("Password and email can't be same")
        return data


class SellerLoginSerializer(serializers.Serializer):
    user_identifier = serializers.CharField()
    password = serializers.CharField()

