from django.urls import path
from rest_framework import routers

from charging.views import AdminCreditRequestApprovalView, SellChargeView, ShowSellerCreditView, \
    ShowSellerTransactionView, CheckTransaction, CreditRequestView

app_name = "charging"

router = routers.DefaultRouter()

router.register('deposit_request', CreditRequestView, basename='deposit_request')
router.register('admin_deposit_request_action', AdminCreditRequestApprovalView, basename='demand_quote')

urlpatterns = router.urls

urlpatterns += [
    path('sell_charge/', SellChargeView.as_view(), name='sell_charge'),
    path('show_credit/', ShowSellerCreditView.as_view(), name='show_credit'),
    path('show_transaction/', ShowSellerTransactionView.as_view(), name='show_transaction'),
    path('check_transaction/', CheckTransaction.as_view(), name='check_transaction'),

]
