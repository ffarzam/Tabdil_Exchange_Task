import re

from rest_framework import serializers, status
from rest_framework.exceptions import ValidationError

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
            raise ValidationError({"message":"Phone number is invalid"}, code=status.HTTP_400_BAD_REQUEST)
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


    def update(self, instance, validated_data):
        request = self.context["request"]
        validated_data['is_processed'] = True
        validated_data['admin_user'] = request.user
        apply_admin_action_on_seller_request_for_credit(instance, validated_data)
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

    def create(self, validated_data):
        validated_data["seller"] = self.context["request"].user.seller
        return super().create(validated_data)