from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from charging.models import Seller

from accounts.models import User


class SellerAPITestCase(APITestCase):

    def setUp(self):
        self.user1 = User.objects.create_user(email='testemail1@yahoo.com', national_id="2700110595",
                                              password='testpassword1')
        self.user2 = User.objects.create_user(email='testemail2@yahoo.com', national_id="0924117583",
                                              password='testpassword2')
        self.seller1 = Seller.objects.create(user=self.user1,  credit=10000000)
        self.seller2 = Seller.objects.create(user=self.user2, credit=5000000)

    def test_deposit_success(self):
        deposit_url = reverse("charging:deposit")
        data1 = {'credit': 10000000}
        data2 = {'credit': 5000000}
        self.client.force_authenticate(user=self.user1)

        response1 = self.client.post(deposit_url, data1, format='json')
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertEqual(response1.data['success'], True)
        self.assertEqual(response1.data['message'], 'Credit has been added successfully')

        self.seller1.refresh_from_db()
        self.assertEqual(self.seller1.credit, 20000000)

        self.client.force_authenticate(user=self.user2)
        response2 = self.client.post(deposit_url, data2, format='json')
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.data['success'], True)
        self.assertEqual(response2.data['message'], 'Credit has been added successfully')

        self.seller2.refresh_from_db()
        self.assertEqual(self.seller2.credit, 10000000)

    def test_sell_charge_success(self):
        sell_charge_url = reverse("charging:sell_charge")
        sum1 = 0
        sum2 = 0
        self.client.force_authenticate(user=self.user1)
        for i in range(1, 1001):
            data1 = {'amount': i * 10, 'phone': '09117200513'}
            sum1 += i * 10
            response1 = self.client.post(sell_charge_url, data1, format='json')
            self.assertEqual(response1.status_code, status.HTTP_200_OK)
            self.assertEqual(response1.data['success'], True)
            self.assertEqual(response1.data['message'], 'Selling charge has been done successfully')

        self.client.force_authenticate(user=self.user2)
        for i in range(1, 1001):
            data2 = {'amount': i * 5, 'phone': '09117200513'}
            sum2 += i * 5
            response2 = self.client.post(sell_charge_url, data2, format='json')
            self.assertEqual(response2.status_code, status.HTTP_200_OK)
            self.assertEqual(response2.data['success'], True)
            self.assertEqual(response2.data['message'], 'Selling charge has been done successfully')

        self.seller1.refresh_from_db()
        self.assertEqual(self.seller1.credit, 10000000 - sum1)
        self.seller2.refresh_from_db()
        self.assertEqual(self.seller2.credit, 5000000 - sum2)

    def test_sell_charge_insufficient_funds(self):
        sell_charge_url = reverse("charging:sell_charge")
        data = {'amount': 50000000, 'phone': '09117200513'}
        self.client.force_authenticate(user=self.user1)

        response = self.client.post(sell_charge_url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data['success'], False)
        self.assertEqual(response.data['message'], 'Insufficient credit')

        self.seller1.refresh_from_db()
        self.assertEqual(self.seller1.credit, 10000000)
