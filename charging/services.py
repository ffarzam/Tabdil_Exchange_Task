import json
import logging

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from charging.models import CreditRequest, Seller, Transaction, PhoneNumber

logger = logging.getLogger('elastic_logger')


class CreditApproveStrategy:
    def apply(self, instance, validated_data):
        with transaction.atomic():
            instance = instance.__class__.objects.select_for_update().get(id=instance.id)
            seller = Seller.objects.select_for_update().get(id=instance.seller.id)
            validated_data["change_status_at"] = timezone.now()
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save(update_fields=validated_data.keys())
            seller.credit = F("credit") + instance.amount
            seller.save(update_fields=("credit",))
            Transaction.objects.create(
                seller=seller,
                amount=instance.amount,
                transaction_type=Transaction.DEPOSIT,
            )


class CreditRejectStrategy:
    def apply(self, instance, validated_data):
        with transaction.atomic():
            instance = instance.__class__.objects.select_for_update().get(id=instance.id)
            for attr, value in validated_data.items():
                setattr(instance, attr, value)
            instance.save()


ACTION_STRATEGY = {
    CreditRequest.APPROVED: CreditApproveStrategy(),
    CreditRequest.REJECT: CreditRejectStrategy(),
}

def apply_admin_action_on_seller_request_for_credit(instance, validated_data):

    action_strategy = ACTION_STRATEGY.get(validated_data['status'])
    if action_strategy:
        action_strategy.apply(instance, validated_data)



def perform_charge(seller_id, phone_number, amount):
    with transaction.atomic():
        seller = Seller.objects.select_for_update().get(id=seller_id)

        if seller.credit < amount:
            raise ValueError("Insufficient credit")

        seller.credit = F("credit") - amount
        seller.save(update_fields=("credit",))

        Transaction.objects.create(
            seller=seller,
            amount=amount,
            phone=phone_number,
            transaction_type=Transaction.SELLING,
        )

        PhoneNumber.objects.get_or_create(phone_number=phone_number)

