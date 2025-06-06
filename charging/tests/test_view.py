from rest_framework.test import APITestCase, APITransactionTestCase
from django.contrib.auth import get_user_model
from django.test import TestCase, TransactionTestCase

from charging.models import CreditRequest, Seller, Transaction, PhoneNumber
from concurrent.futures import ProcessPoolExecutor, as_completed

from django.urls import reverse

from rest_framework import status
from django.db import connection
from rest_framework.test import APIClient

User = get_user_model()


class CreditRequestAPITest(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(email='testemail1@yahoo.com', national_id="2700110595",
                                             password='testpassword1')

        self.seller = Seller.objects.create(user=self.user)

        login_url = reverse("tabdil:accounts:login")

        response = self.client.post(login_url, {
            "user_identifier": "2700110595",
            "password": "testpassword1"
        })
        access_token = response.data["data"]["access"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {access_token}")

        self.url = reverse("tabdil:charging:deposit_request-list")

    def test_create_credit_request(self):
        data = {"amount": 5000}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(CreditRequest.objects.count(), 1)
        self.assertEqual(CreditRequest.objects.first().amount, 5000)
        self.assertEqual(CreditRequest.objects.first().seller, self.seller)


class AdminCreditApprovalViewTest(APITestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(email='testemail1@yahoo.com', national_id="2700110595",
                                                   password='testpassword1')

        self.seller_user = User.objects.create_user(email='testemail2@yahoo.com', national_id="2700110596",
                                                    password='testpassword2')
        self.seller = Seller.objects.create(user=self.seller_user)
        self.credit_request = CreditRequest.objects.create(
            seller=self.seller,
            amount=5000,
        )

        login_url = reverse("tabdil:accounts:login")

        response = self.client.post(login_url, {
            "user_identifier": "2700110595",
            "password": "testpassword1"
        })
        access_token = response.data["data"]["access"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {access_token}")

        self.list_url = reverse("tabdil:charging:admin_deposit_request_action-list")
        self.detail_url = reverse("tabdil:charging:admin_deposit_request_action-detail", args=[self.credit_request.id])

    def test_approve_credit_request(self):
        response = self.client.patch(self.detail_url, {"status": "A"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.credit_request.refresh_from_db()
        self.seller.refresh_from_db()

        self.assertTrue(self.credit_request.is_processed)
        self.assertEqual(self.credit_request.status, "A")
        self.assertEqual(self.seller.credit, 5000)

        self.assertTrue(Transaction.objects.filter(seller=self.seller, amount=5000).exists())

    def test_reject_credit_request(self):
        response = self.client.patch(self.detail_url, {"status": "R"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.credit_request.refresh_from_db()
        self.assertTrue(self.credit_request.is_processed)
        self.assertEqual(self.credit_request.status, "R")

        self.seller.refresh_from_db()
        self.assertEqual(self.seller.credit, 0)

        self.assertFalse(Transaction.objects.exists())

    def test_invalid_status_rejected(self):
        response = self.client.patch(self.detail_url, {"status": "invalid_status"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("status", response.data)


class SellChargeViewTest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='testemail1@yahoo.com', national_id="2700110595",
                                             password='testpassword1')
        self.seller = Seller.objects.create(user=self.user, credit=10000)

        login_url = reverse("tabdil:accounts:login")

        response = self.client.post(login_url, {
            "user_identifier": "2700110595",
            "password": "testpassword1"
        })
        access_token = response.data["data"]["access"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {access_token}")

        self.url = reverse("tabdil:charging:sell_charge")

    def test_successful_sell_charge(self):
        data = {"phone": "09123456789", "amount": 5000}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["success"], True)

        self.seller.refresh_from_db()
        self.assertEqual(self.seller.credit, 5000)

        transaction = Transaction.objects.get(seller=self.seller)
        self.assertEqual(transaction.amount, 5000)
        self.assertEqual(transaction.transaction_type, Transaction.SELLING)

        phone_exists = PhoneNumber.objects.filter(phone_number="09123456789").exists()
        self.assertTrue(phone_exists)

    def test_insufficient_credit(self):
        data = {"phone": "09123456789", "amount": 20000}  # More than credit
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["message"], "Insufficient credit")

        self.seller.refresh_from_db()
        self.assertEqual(self.seller.credit, 10000)  # No deduction

        self.assertFalse(Transaction.objects.exists())

    def test_invalid_phone_number(self):
        data = {"phone": "123456", "amount": 1000}
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("phone", response.data)

        self.assertFalse(Transaction.objects.exists())


def credit_increase_worker(args):
    """Worker function for credit increase operations"""
    process_id, seller_id, admin_user_id, amount = args

    connection.close()

    admin_user = User.objects.get(id=admin_user_id)
    seller = Seller.objects.get(id=seller_id)

    # Create credit request
    credit_request = CreditRequest.objects.create(
        seller=seller,
        amount=amount,
    )

    # Admin approves the request
    client = APIClient()
    client.force_authenticate(user=admin_user)

    detail_url = reverse("tabdil:charging:admin_deposit_request_action-detail",
                         args=[credit_request.id])

    response = client.patch(detail_url, {"status": "A"}, format="json")

    return {
        'process_id': process_id,
        'seller_id': seller_id,
        'status_code': response.status_code,
        'success': response.status_code == status.HTTP_200_OK,
        'amount': amount,
        'credit_request_id': credit_request.id
    }
#
#
def charge_sale_worker(args):
    """Worker function for charge selling operations"""
    process_id, seller_id, amount, phone_base = args

    connection.close()

    seller = Seller.objects.get(id=seller_id)

    seller_user = seller.user

    client = APIClient()
    client.force_authenticate(user=seller_user)

    url = reverse('tabdil:charging:sell_charge')

    # Generate unique phone number for this transaction
    phone_number = f"{phone_base}{process_id:04d}"

    payload = {
        'phone': phone_number,
        'amount': amount
    }

    response = client.post(url, payload, format='json')

    return {
        'process_id': process_id,
        'seller_id': seller_id,
        'status_code': response.status_code,
        'success': response.data.get('success', False) if hasattr(response, 'data') else False,
        'amount': amount,
        'phone': phone_number,
        'message': response.data.get('message', '') if hasattr(response, 'data') else ''
    }


class ParallelAccountingSystemTestCase(TransactionTestCase):
    """
    Comprehensive parallel test for accounting system with multiple sellers,
    credit increases, and high-volume charge sales
    """

    def setUp(self):
        """Set up test data with multiple sellers and admin"""
        # Create admin user
        self.admin_user = User.objects.create_user(
            national_id="2700110590",
            email='admin@example.com',
            password='admin123'
        )

        # Create sellers
        self.sellers = []
        self.seller_users = []

        for i in range(2):  # At least 2 sellers as required
            user = User.objects.create_user(
                national_id=f"270011059{i + 1}",
                email=f'seller{i + 1}@example.com',
                password=f'seller{i + 1}123'
            )

            seller = Seller.objects.create(
                user=user,
                credit=0  # Start with zero credit
            )

            self.seller_users.append(user)
            self.sellers.append(seller)

    def test_comprehensive_parallel_accounting_system(self):
        """
        Test accounting system under high parallel load:
        - At least 2 sellers
        - 10 credit increases (5 per seller)
        - 1000 charge sales (500 per seller)
        - Final credit verification
        """
        print("Starting comprehensive parallel accounting system test...")

        # Phase 1: Parallel Credit Increases (10 total)
        print("Phase 1: Processing credit increases...")

        credit_increase_args = []
        credit_amount_per_increase = 100000  # 100,000 per increase

        # 5 credit increases per seller
        for seller_idx, seller in enumerate(self.sellers):
            for i in range(5):
                process_id = seller_idx * 5 + i
                credit_increase_args.append((
                    process_id,
                    seller.id,
                    self.admin_user.id,
                    credit_amount_per_increase
                ))

        # Execute credit increases in parallel
        with ProcessPoolExecutor(max_workers=10) as executor:
            credit_futures = [
                executor.submit(credit_increase_worker, args)
                for args in credit_increase_args
            ]
            credit_results = [future.result() for future in as_completed(credit_futures)]

        # Verify credit increases
        successful_credit_increases = [r for r in credit_results if r['success']]

        print(f"Credit increase results:")
        print(f"  Total credit requests: {len(credit_results)}")
        print(f"  Successful: {len(successful_credit_increases)}")

        self.assertEqual(len(successful_credit_increases), 10,
                         "Should have 10 successful credit increases")

        # Verify sellers have correct initial credit
        connection.close()
        for seller in self.sellers:
            seller.refresh_from_db()
            expected_credit = 5 * credit_amount_per_increase  # 5 increases per seller
            self.assertEqual(float(seller.credit), float(expected_credit),
                             f"Seller {seller.id} should have {expected_credit} credit")

        # Phase 2: Parallel Charge Sales (1000 total)
        print("Phase 2: Processing charge sales...")

        charge_sale_args = []
        sale_amount = 1000  # 1,000 per sale
        sales_per_seller = 500  # 500 sales per seller = 1000 total

        # Generate charge sale arguments
        for seller_idx, seller in enumerate(self.sellers):
            phone_base = f"091234{seller_idx}"  # Different phone base per seller

            for i in range(sales_per_seller):
                process_id = seller_idx * sales_per_seller + i
                charge_sale_args.append((
                    process_id,
                    seller.id,
                    sale_amount,
                    phone_base
                ))

        # Execute charge sales in parallel with high concurrency
        max_workers = 50  # High concurrency to test system under load

        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            sale_futures = [
                executor.submit(charge_sale_worker, args)
                for args in charge_sale_args
            ]

            # Collect results as they complete
            sale_results = []
            for future in as_completed(sale_futures):
                try:
                    result = future.result()
                    sale_results.append(result)
                except Exception as e:
                    print(f"Sale worker failed: {e}")

        # Analyze results
        successful_sales = [r for r in sale_results if r['success']]
        failed_sales = [r for r in sale_results if not r['success']]

        print(f"Charge sale results:")
        print(f"  Total sale attempts: {len(sale_results)}")
        print(f"  Successful sales: {len(successful_sales)}")
        print(f"  Failed sales: {len(failed_sales)}")

        # Group results by seller
        sales_by_seller = {}
        for result in successful_sales:
            seller_id = result['seller_id']
            if seller_id not in sales_by_seller:
                sales_by_seller[seller_id] = []
            sales_by_seller[seller_id].append(result)

        for seller_id, sales in sales_by_seller.items():
            print(f"  Seller {seller_id}: {len(sales)} successful sales")

        # Phase 3: Final Credit Verification
        print("Phase 3: Final credit verification...")

        connection.close()

        total_expected_sales = 0
        for seller in self.sellers:
            seller.refresh_from_db()

            # Calculate expected credit
            initial_credit = 5 * credit_amount_per_increase  # From credit increases
            seller_successful_sales = len(sales_by_seller.get(seller.id, []))
            total_sales_amount = seller_successful_sales * sale_amount
            expected_final_credit = initial_credit - total_sales_amount

            total_expected_sales += seller_successful_sales

            print(f"Seller {seller.id} verification:")
            print(f"  Initial credit: {initial_credit}")
            print(f"  Successful sales: {seller_successful_sales}")
            print(f"  Total sales amount: {total_sales_amount}")
            print(f"  Expected final credit: {expected_final_credit}")
            print(f"  Actual final credit: {seller.credit}")

            self.assertEqual(float(seller.credit), float(expected_final_credit),
                             f"Seller {seller.id} final credit mismatch")

        # Verify transaction records
        total_transactions = Transaction.objects.count()
        expected_transactions = len(successful_credit_increases) + len(successful_sales)

        print(f"Transaction verification:")
        print(f"  Total transactions in DB: {total_transactions}")
        print(f"  Expected transactions: {expected_transactions}")
        print(f"  (Credit increases + Sales: {len(successful_credit_increases)} + {len(successful_sales)})")

        self.assertEqual(total_transactions, expected_transactions,
                         "Transaction count should match successful operations")


        self.assertEqual(total_expected_sales, len(successful_sales),
                         "Total successful sales should match sum of individual seller sales")

        print("✓ Comprehensive parallel accounting system test completed successfully!")


# Keep original parallel tests for backward compatibility
def make_depletion_request_worker(args):
    """Worker function for credit depletion testing"""
    process_id, user_id, request_amount, url = args

    connection.close()

    user = User.objects.get(id=user_id)

    client = APIClient()
    client.force_authenticate(user=user)

    payload = {
        'phone': f'0912345678{process_id}',
        'amount': request_amount
    }

    response = client.post(url, payload, format='json')
    return {
        'process_id': process_id,
        'status_code': response.status_code,
        'success': response.data.get('success', False) if hasattr(response, 'data') else False,
        'message': response.data.get('message', '') if hasattr(response, 'data') else ''
    }


def make_concurrent_request_worker(args):
    """Worker function for concurrent API requests"""
    process_id, user_id, requests_per_process, request_amount, url = args

    connection.close()
    user = User.objects.get(id=user_id)

    results = []
    client = APIClient()
    client.force_authenticate(user=user)

    for i in range(requests_per_process):
        payload = {
            'phone': f'0912345678{process_id}',
            'amount': request_amount
        }

        response = client.post(url, payload, format='json')
        results.append({
            'process_id': process_id,
            'request_id': i,
            'status_code': response.status_code,
            'success': response.data.get('success', False) if hasattr(response, 'data') else False
        })

    return results


class ParallelSellChargeTestCase(TransactionTestCase):
    """
    TransactionTestCase is used instead of TestCase to properly test
    database transactions and locks in parallel scenarios
    """

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            national_id="2700110595",
            email='test@example.com',
            password='testpass123'
        )

        self.seller = Seller.objects.create(
            user=self.user,
            credit=1000
        )

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.url = reverse('tabdil:charging:sell_charge')

        self.valid_payload = {
            'phone': '09123456789',
            'amount': 100
        }

    def test_concurrent_requests_same_seller(self):
        """Test concurrent requests from the same seller - race condition test"""
        num_processes = 4
        requests_per_process = 4
        request_amount = 50

        process_args = [
            (i, self.user.id, requests_per_process, request_amount, self.url)
            for i in range(num_processes)
        ]

        with ProcessPoolExecutor(max_workers=num_processes) as executor:
            futures = [executor.submit(make_concurrent_request_worker, args) for args in process_args]
            all_results = []

            for future in as_completed(futures):
                process_results = future.result()
                all_results.extend(process_results)

        successful_requests = [r for r in all_results if r['success']]
        failed_requests = [r for r in all_results if not r['success']]

        print(f"Concurrent test results:")
        print(f"  Total requests: {len(all_results)}")
        print(f"  Successful: {len(successful_requests)}")
        print(f"  Failed: {len(failed_requests)}")

        connection.close()

        self.seller.refresh_from_db()
        actual_credit = int(self.seller.credit)
        expected_credit = 1000 - (len(successful_requests) * request_amount)

        self.assertEqual(actual_credit, expected_credit,
                         f"Expected credit: {expected_credit}, Actual: {actual_credit}")

        transaction_count = Transaction.objects.filter(seller=self.seller).count()
        self.assertEqual(transaction_count, len(successful_requests))

    def test_credit_depletion_race_condition(self):
        """Test race condition when multiple requests try to deplete remaining credit"""
        self.seller.credit = 150
        self.seller.save()

        num_processes = 6
        request_amount = 50

        process_args = [
            (i, self.user.id, request_amount, self.url)
            for i in range(num_processes)
        ]

        with ProcessPoolExecutor(max_workers=num_processes) as executor:
            futures = [executor.submit(make_depletion_request_worker, args) for args in process_args]
            results = [future.result() for future in as_completed(futures)]

        all_requests = [r for r in results]
        successful_requests = [r for r in results if r['success']]
        insufficient_credit_requests = [r for r in results
                                        if not r['success'] and r['status_code'] == status.HTTP_400_BAD_REQUEST]

        print(f"Credit depletion test results:")
        print(f"  All requests: {len(all_requests)}")
        print(f"  Successful requests: {len(successful_requests)}")
        print(f"  Insufficient credit responses: {len(insufficient_credit_requests)}")

        connection.close()

        self.assertEqual(len(successful_requests), 3,
                         "Should have exactly 3 successful requests")

        self.assertEqual(len(insufficient_credit_requests), num_processes - 3,
                         "Remaining requests should get insufficient credit error")

        self.seller.refresh_from_db()
        self.assertEqual(float(self.seller.credit), 0.0, "Final credit should be 0")