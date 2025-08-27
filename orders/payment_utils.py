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
            
            # eSewa v2 API format - WILL redirect to eSewa login
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
            
            print(f"🔗 eSewa URL: {settings.ESEWA_FORM_URL}")
            print(f"📋 eSewa Data: {esewa_data}")
            
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
            
            print(f"🔍 eSewa Response - amt: {total_amount}, refId: {transaction_uuid}, oid: {product_id}")
            
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
        try:
            amount_in_paisa = int(order.grand_total * 100)
            
            khalti_config = {
                'publicKey': settings.KHALTI_SETTINGS['PUBLIC_KEY'],
                'productIdentity': f"ORDER-{order.id}",
                'productName': f"Order #{order.id}",
                'productUrl': 'http://127.0.0.1:8000/',
                'paymentPreference': [
                    'KHALTI',
                    'EBANKING', 
                    'MOBILE_BANKING',
                    'CONNECT_IPS',
                    'SCT',
                ]
            }
            
            return {
                'config': khalti_config,
                'amount': amount_in_paisa
            }
            
        except Exception as e:
            print(f"❌ Khalti Error: {str(e)}")
            return None
    
    @staticmethod
    def verify_payment(token, amount):
        try:
            url = f"{settings.KHALTI_SETTINGS['API_URL']}payment/verify/"
            
            headers = {
                'Authorization': f"Key {settings.KHALTI_SETTINGS['SECRET_KEY']}",
                'Content-Type': 'application/json'
            }
            
            data = {
                'token': token,
                'amount': amount
            }
            
            response = requests.post(url, json=data, headers=headers, timeout=30)
            
            if response.status_code == 200:
                response_data = response.json()
                return {'success': True, 'data': response_data}
            else:
                return {'success': False, 'error': f"API returned {response.status_code}"}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}