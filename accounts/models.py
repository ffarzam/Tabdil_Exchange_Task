from django.contrib.auth.models import AbstractUser
from django.db import models

from .manager import CustomManager


# Create your models here.


class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    national_id = models.CharField(max_length=10, unique=True)

    USERNAME_FIELD = 'email'

    REQUIRED_FIELDS = ["national_id"]

    objects = CustomManager()

    def __str__(self):
        return self.email
