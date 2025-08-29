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

# QR Payment class for future enhancements
class QRPayment:
    @staticmethod
    def initiate_payment(order, seller_qr_data):
        """Prepare QR payment data"""
        return {
            'success': True,
            'order_id': order.id,
            'seller_qr_data': seller_qr_data,
            'total_amount': order.grand_total
        }
    
    @staticmethod
    def confirm_payment(order):
        """Confirm QR payment (manual confirmation)"""
        return {
            'success': True,
            'payment_method': 'QR Payment',
            'reference': f"QR-{order.id}",
            'status': 'completed'
        }