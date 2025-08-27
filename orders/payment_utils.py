import requests
import json
from django.conf import settings
import time
import logging

logger = logging.getLogger(__name__)

class ESewaPayment:
    @staticmethod
    def initiate_payment(order):
        try:
            amount = int(order.grand_total)
            
            esewa_data = {
                'tAmt': amount,
                'amt': amount,
                'txAmt': 0,
                'psc': 0,
                'pdc': 0,
                'scd': settings.ESEWA_PRODUCT_CODE,
                'pid': f"ORDER-{order.id}-{int(time.time())}",
                'su': settings.ESEWA_SETTINGS['SUCCESS_URL'],
                'fu': settings.ESEWA_SETTINGS['FAILURE_URL'],
            }
            
            return {
                'form_data': esewa_data,
                'action_url': settings.ESEWA_FORM_URL
            }
            
        except Exception as e:
            print(f"❌ eSewa Error: {str(e)}")
            return None
    
    @staticmethod
    def verify_payment(request):
        try:
            total_amount = request.GET.get('amt')
            transaction_uuid = request.GET.get('refId') 
            product_id = request.GET.get('oid')
            
            if total_amount and transaction_uuid and product_id:
                return {
                    'success': True,
                    'transaction_id': transaction_uuid,
                    'amount': total_amount,
                    'product_id': product_id
                }
            else:
                return {'success': False, 'error': 'Missing required parameters'}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}

class KhaltiPayment:
    @staticmethod
    def initiate_payment(order):
        """NEW Khalti ePayment API"""
        try:
            # Convert to paisa (Khalti uses paisa)
            amount_in_paisa = int(order.grand_total * 100)
            
            url = f"{settings.KHALTI_SETTINGS['API_URL']}epayment/initiate/"
            
            payload = {
                "return_url": f"http://127.0.0.1:8000/orders/khalti-return/{order.id}/",
                "website_url": "http://127.0.0.1:8000/",
                "amount": amount_in_paisa,
                "purchase_order_id": f"ORDER-{order.id}",
                "purchase_order_name": f"Order #{order.id}",
                "customer_info": {
                    "name": f"{order.user.first_name} {order.user.last_name}",
                    "email": order.user.email,
                    "phone": "9800000001"  # You can get this from user profile
                }
            }
            
            headers = {
                'Authorization': f'key {settings.KHALTI_SETTINGS["SECRET_KEY"]}',
                'Content-Type': 'application/json',
            }
            
            print(f"💜 Khalti Initiate URL: {url}")
            print(f"💜 Khalti Payload: {payload}")
            
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            print(f"💜 Khalti Response Status: {response.status_code}")
            print(f"💜 Khalti Response: {response.text}")
            
            if response.status_code == 200:
                response_data = response.json()
                return {
                    'success': True,
                    'payment_url': response_data.get('payment_url'),
                    'pidx': response_data.get('pidx')
                }
            else:
                return {'success': False, 'error': f"API returned {response.status_code}: {response.text}"}
                
        except Exception as e:
            print(f"❌ Khalti Initiate Error: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    @staticmethod
    def verify_payment(pidx):
        """Verify Khalti ePayment"""
        try:
            url = f"{settings.KHALTI_SETTINGS['API_URL']}epayment/lookup/"
            
            payload = {"pidx": pidx}
            
            headers = {
                'Authorization': f'key {settings.KHALTI_SETTINGS["SECRET_KEY"]}',
                'Content-Type': 'application/json',
            }
            
            print(f"💜 Khalti Verify URL: {url}")
            print(f"💜 Khalti Verify Payload: {payload}")
            
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            print(f"💜 Khalti Verify Response: {response.status_code} - {response.text}")
            
            if response.status_code == 200:
                response_data = response.json()
                return {'success': True, 'data': response_data}
            else:
                return {'success': False, 'error': f"Verification failed: {response.text}"}
                
        except Exception as e:
            print(f"❌ Khalti Verify Error: {str(e)}")
            return {'success': False, 'error': str(e)}