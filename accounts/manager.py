from django.contrib.auth.models import BaseUserManager


class CustomManager(BaseUserManager):
    def create_user(self, email, national_id, password):
        if not email:
            raise ValueError("Users must have an email")
        if not national_id:
            raise ValueError("Users must have an national id")

        user = self.model(national_id=national_id, email=email)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, national_id, password):
        user = self.create_user(email, national_id, password)
        user.is_account_enable = True
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user