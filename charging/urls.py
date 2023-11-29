from django.urls import path
from . import views

urlpatterns = [
    path('deposit/', views.DepositView.as_view(), name='deposit'),
    path('sell_charge/', views.SellChargeView.as_view(), name='sell_charge'),
    path('show_credit/', views.ShowSellerCreditView.as_view(), name='show_credit'),
    path('show_transaction/', views.ShowSellerTransactionView.as_view(), name='show_transaction'),

]
