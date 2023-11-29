from django.core.validators import RegexValidator

phoneNumberRegex = RegexValidator(regex=r"^09\d{9}$")
