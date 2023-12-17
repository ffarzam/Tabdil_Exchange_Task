import re

from rest_framework import serializers
from .models import Seller, Transaction


class TransactionSerializer(serializers.ModelSerializer):
    transaction_type = serializers.CharField(read_only=True, required=False)

    class Meta:
        model = Transaction
        fields = ['id', 'phone', 'amount', 'transaction_type', 'timestamp']


class TransactionInputSerializer(serializers.Serializer):
    phone = serializers.CharField()
    amount = serializers.IntegerField()

    def validate_phone(self, value):
        if not re.match(r"^09\d{9}$", value):
            raise serializers.ValidationError('Phone number is invalid')
        return value


class SellerSerializer(serializers.ModelSerializer):
    user = serializers.CharField(read_only=True)

    class Meta:
        model = Seller
        fields = ['user', 'credit']
