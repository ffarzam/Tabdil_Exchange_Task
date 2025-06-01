import json
import logging

from django.db import transaction
from django.db.models import Sum, F, Case, When, IntegerField, Avg, Value
from django.db.models.functions import Cast
from rest_framework import generics, status
from rest_framework.mixins import ListModelMixin, UpdateModelMixin, CreateModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from .models import Seller, Transaction, CreditRequest
from .serializers import TransactionSerializer, SellerSerializer, SellerSellingChargeCreateSerializer, \
    AdminDepositRequestApprovalPatchSerializer, AdminDepositRequestApprovalListSerializer, \
    CreditRequestListSerializer, CreditRequestCreateSerializer
from accounts.authentication import AccessTokenAuthentication
from .services import perform_charge

# Create your views here.

logger = logging.getLogger('elastic_logger')


class CreditRequestView(ListModelMixin, CreateModelMixin, GenericViewSet):
    queryset = CreditRequest.objects.all()
    authentication_classes = (AccessTokenAuthentication,)
    permission_classes = (IsAuthenticated,) #TODO here need a permission to only accept sellers
    serializer_class = {
        "list": CreditRequestListSerializer,
        "create": CreditRequestCreateSerializer,
    }
    http_method_names = ('get', 'post')

    def get_serializer_class(self):
        return self.serializer_class.get(self.action)

    def get_queryset(self):
        user = self.request.user
        seller = user.seller
        queryset = self.queryset.filter(seller=seller)
        return queryset


class AdminCreditRequestApprovalView(ListModelMixin, UpdateModelMixin, GenericViewSet):
    queryset = CreditRequest.objects.filter(is_processed=False)
    authentication_classes = (AccessTokenAuthentication,)
    permission_classes = (IsAuthenticated,) #TODO here need a permission to only accept admins
    serializer_class = {
        "list": AdminDepositRequestApprovalListSerializer,
        "patch": AdminDepositRequestApprovalPatchSerializer,
    }
    http_method_names = ('get', 'patch')

    def get_serializer_class(self):
        return self.serializer_class.get(self.action)


class SellChargeView(APIView):
    authentication_classes = (AccessTokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    serializer_class = SellerSellingChargeCreateSerializer


    def post(self, request):
        user = request.user
        data = request.data
        serializer = self.serializer_class(data=data)
        serializer.is_valid(raise_exception=True)
        amount = serializer.validated_data["amount"]
        phone = serializer.validated_data["phone"]
        seller = user.seller
        if seller.credit < amount:
            return Response({'success': False, 'message': 'Insufficient credit'},
                                    status=status.HTTP_404_NOT_FOUND)
        perform_charge(request, user.seller.id, phone, amount)
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
