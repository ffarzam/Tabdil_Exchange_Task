from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

from accounts.models import User

# Create your models here.


class Seller(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    credit = models.PositiveIntegerField(default=0, editable=False) #Todo: Decimal
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Seller: {self.user.national_id} - Balance: {self.credit}"


class Transaction(models.Model):
    DEPOSIT = 'C'
    SELLING = 'S'

    TRANSACTION_CHOICES = [
        (DEPOSIT, "Deposit"),
        (SELLING, "Selling"),
    ]

    seller = models.ForeignKey(Seller, on_delete=models.CASCADE, editable=False)
    phone = models.CharField(max_length=11, null=True, blank=True, editable=False)
    transaction_type = models.CharField(max_length=1, choices=TRANSACTION_CHOICES, editable=False)
    amount = models.PositiveIntegerField() #Todo: Decimal
    timestamp = models.DateTimeField(auto_now_add=True, editable=False)

    def __str__(self):
        return f"{self.get_transaction_type_display()} by {self.seller}"


class CreditRequest(models.Model):
    PENDING = "P"
    APPROVED = "A"
    REJECT = "R"

    STATUS_CHOICES = [
        (PENDING, 'Pending'),
        (APPROVED, 'Approved'),
        (REJECT, 'Rejected'),
    ]

    seller = models.ForeignKey(Seller, on_delete=models.CASCADE, related_name='credit_requests')
    amount = models.PositiveIntegerField(default=0) #Todo: Decimal
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    admin_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='approved_requests')
    created_at = models.DateTimeField(auto_now_add=True)
    change_status_at = models.DateTimeField(null=True, blank=True)
    is_processed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.seller.user.national_id} - {self.amount}"


class PhoneNumber(models.Model):
    phone_number = models.CharField(max_length=11, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.phone_number



