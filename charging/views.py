import json
import logging

from django.db import transaction
from django.db.models import Sum, F, Case, When, IntegerField, Count, Avg, Value, Q
from django.db.models.functions import Cast
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Seller, Transaction
from .serializers import TransactionSerializer, SellerSerializer, TransactionInputSerializer
from accounts.authentication import AccessTokenAuthentication

from .utils import TransactionPagination
from config import custom_exception

# Create your views here.

logger = logging.getLogger('elastic_logger')


class DepositView(APIView):
    authentication_classes = (AccessTokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    serializer_class = SellerSerializer

    def post(self, request):
        user = request.user
        data = request.data
        serializer = self.serializer_class(data=data)
        serializer.is_valid(raise_exception=True)
        amount = serializer.validated_data["credit"]
        with transaction.atomic():
            seller = Seller.objects.select_for_update().get(user=user)
            seller.credit = F("credit") + amount
            seller.save()
            Transaction.objects.create(seller=seller, amount=amount, transaction_type='C')

            log_data = {"by": seller.id,
                        "amount": amount,
                        "type": "charge",
                        "unique_id": request.unique_id,
                        }
            logger.info(json.dumps(log_data))

        return Response({'success': True, 'message': 'Credit has been added successfully'}, status=status.HTTP_200_OK)


class SellChargeView(APIView):
    authentication_classes = (AccessTokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    serializer_class = TransactionInputSerializer

    def post(self, request):
        user = request.user
        data = request.data
        serializer = self.serializer_class(data=data)
        serializer.is_valid(raise_exception=True)
        amount = serializer.validated_data["amount"]
        phone = serializer.validated_data["phone"]
        with transaction.atomic():
            seller = Seller.objects.select_for_update().get(user=user)
            if seller.credit < amount:
                return Response({'success': False, 'message': 'Insufficient credit'},
                                status=status.HTTP_404_NOT_FOUND)
            seller.credit = F("credit") - amount
            seller.save()
            Transaction.objects.create(seller=seller, transaction_type='S', amount=amount, phone=phone)

            log_data = {"from": seller.id,
                        "to": phone,
                        "amount": amount,
                        "type": "sell",
                        "unique_id": request.unique_id,
                        }
            logger.info(json.dumps(log_data))

        return Response({'success': True, 'message': 'Selling charge has been done successfully'},
                        status=status.HTTP_200_OK)


class ShowSellerCreditView(generics.RetrieveAPIView):
    authentication_classes = (AccessTokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    serializer_class = SellerSerializer

    def get_object(self):
        return Seller.objects.get(user=self.request.user)


class ShowSellerTransactionView(generics.ListAPIView):
    authentication_classes = (AccessTokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    serializer_class = TransactionSerializer
    pagination_class = TransactionPagination

    def get_queryset(self):
        return Transaction.objects.select_related("seller__user").filter(seller__user=self.request.user)


class CheckTransaction(APIView):
    authentication_classes = (AccessTokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get(self, request):

        data = Transaction.objects.select_related("seller__user"). \
            filter(seller__user=request.user).values("amount", "transaction_type"). \
            aggregate(charge=Sum(Case(When(transaction_type='C', then=F('amount')), default=Value(0))),
                      sell=Sum(Case(When(transaction_type='S', then=F('amount')), default=Value(0))),
                      transaction_balance=F("charge") - F("sell"),
                      seller_credit=Cast(Avg(F("seller__credit")), output_field=IntegerField()),
                      )

        data = {"charge": data.get("charge") or 0,
                "sell": data.get("sell") or 0,
                "transaction_balance": data.get("transaction_balance") or 0,
                "seller_credit": data.get("seller_credit") or 0,
                }

        state = data["seller_credit"] == data["transaction_balance"]

        return Response({"equal": state, 'data': data})
