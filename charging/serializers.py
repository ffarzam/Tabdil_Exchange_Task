import re

from rest_framework import serializers
from .models import Seller, Transaction, CreditRequest
from .services import apply_admin_action_on_seller_request_for_credit


class TransactionSerializer(serializers.ModelSerializer):
    transaction_type = serializers.CharField(read_only=True, required=False)

    class Meta:
        model = Transaction
        fields = ("id", "phone", "amount", "transaction_type", "timestamp")


class SellerSellingChargeCreateSerializer(serializers.Serializer):
    phone = serializers.CharField()
    amount = serializers.IntegerField()

    def validate_phone(self, value):
        if not re.match(r"^09\d{9}$", value):
            raise serializers.ValidationError("Phone number is invalid")
        return value


class SellerSerializer(serializers.ModelSerializer):
    user = serializers.CharField(read_only=True)

    class Meta:
        model = Seller
        fields = ("user", "credit")


class AdminDepositRequestApprovalListSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreditRequest
        fields = "__all__"


class AdminDepositRequestApprovalPatchSerializer(serializers.ModelSerializer):

    class Meta:
        model = CreditRequest
        fields = ("status",)

    def validate_status(self, value):
        if value not in [CreditRequest.APPROVED, CreditRequest.REJECT]:
            raise serializers.ValidationError("Only 'Approved' or 'Rejected' status is allowed.")
        return value

    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        data['is_processed'] = True
        data['admin_user'] = self.context["request"].user
        return data

    def update(self, instance, validated_data):
        request = self.context["request"]
        apply_admin_action_on_seller_request_for_credit(instance, validated_data, request)
        instance.refresh_from_db()
        return instance

class CreditRequestListSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreditRequest
        fields = "__all__"



class CreditRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreditRequest
        fields = ("id", "amount")
        read_only_fields = ('id',)

    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        data['seller'] = self.context["request"].user.seller
        return data