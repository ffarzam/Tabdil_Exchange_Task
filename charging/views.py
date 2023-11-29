from django.db import transaction
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Seller, Transaction
from .serializers import TransactionSerializer, SellerSerializer
from accounts.authentication import AccessTokenAuthentication


# Create your views here.


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
            seller.credit += amount
            seller.save()
            Transaction.objects.create(seller=seller, amount=amount, transaction_type='C')

        return Response({'success': True, 'message': 'Credit has been added successfully'}, status=status.HTTP_200_OK)


class SellChargeView(APIView):
    authentication_classes = (AccessTokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    serializer_class = TransactionSerializer

    def post(self, request):
        user = request.user
        data = request.data
        serializer = self.serializer_class(data=data)
        serializer.is_valid(raise_exception=True)
        amount = serializer.validated_data["amount"]
        with transaction.atomic():
            seller = Seller.objects.select_for_update().get(user=user)
            if seller.credit < amount:
                # raise custom_exception.InsufficientFunds()
                return Response({'success': False, 'message': 'Insufficient credit'})
            seller.credit -= amount
            seller.save()
            # Transaction.object.create(seller=seller, amount=amount, transaction_type='S', phone=phone)
            serializer.save(seller=seller, transaction_type='S', amount=amount)

        return Response({'success': True, 'message': 'Sell transaction has been done successfully'})


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
        seller = Seller.objects.get(user=self.request.user)
        return Transaction.objects.select_related("seller").filter(seller=seller)
