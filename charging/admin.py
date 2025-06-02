from django.contrib import admin

from . import models

# Register your models here.


@admin.register(models.Seller)
class TransactionAdmin(admin.ModelAdmin):
    fields = ('user', 'credit')
    readonly_fields = ('credit',)
    list_display = [
        'user', 'credit'
    ]
    search_fields = ['user__email__istartswith']


@admin.register(models.Transaction)
class TransactionAdmin(admin.ModelAdmin):
    fields = ('seller', 'phone', 'transaction_type', 'amount', 'timestamp')
    readonly_fields = ('seller', 'phone', 'transaction_type', 'amount', 'timestamp')

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                'seller', 'phone', 'transaction_type', 'amount', 'timestamp',
            )}
         ),
    )

    list_display = [
        'seller', 'phone', 'transaction_type', 'amount', 'timestamp',
    ]

    list_filter = ['seller__user__email', 'phone', 'transaction_type']
    search_fields = ['seller__user__email__istartswith', 'phone', 'transaction_type']
    list_per_page = 20


@admin.register(models.CreditRequest)
class CreditRequestAdmin(admin.ModelAdmin):
    pass