from django.db import models

from accounts.models import User

# Create your models here.


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

    seller = models.ForeignKey(Seller, on_delete=models.CASCADE, editable=False)
    phone = models.CharField(max_length=11, null=True, blank=True, editable=False)
    transaction_type = models.CharField(max_length=1, choices=TRANSACTION_CHOICES, editable=False)
    amount = models.PositiveIntegerField(editable=False) #Todo: Decimal
    timestamp = models.DateTimeField(auto_now_add=True, editable=False)
    is_spent = models.BooleanField(default=True, editable=False)

    def save(self, *args, **kwargs):
        if self.id is None:
            super().save(*args, **kwargs)
        else:
            pass

    def __str__(self):
        return f"{self.get_transaction_type_display()} by {self.seller}"
