from django.db import models

# Create your models here.

from django.db import models

from accounts.models import User

from .utils import phoneNumberRegex


class Seller(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    credit = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.user.email


class Transaction(models.Model):
    CHARGE = "C"
    SELL = "S"

    TRANSACTION_CHOICES = [
        (CHARGE, "Charging"),
        (SELL, "Selling"),
    ]

    seller = models.ForeignKey(Seller, on_delete=models.CASCADE)
    phone = models.CharField(max_length=11, null=True, blank=True)
    transaction_type = models.CharField(max_length=1, choices=TRANSACTION_CHOICES)
    amount = models.PositiveIntegerField()
    timestamp = models.DateTimeField(auto_now_add=True, editable=False)

    def __str__(self):
        return f"{self.get_transaction_type_display()} by {self.seller}"
