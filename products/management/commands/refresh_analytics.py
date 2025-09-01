from django.core.management.base import BaseCommand
from products.models import Product

class Command(BaseCommand):
    help = 'Refresh analytics for all products'

    def handle(self, *args, **options):
        products = Product.objects.filter(approval_status='approved')
        
        for product in products:
            analytics = product.get_analytics_data()
            self.stdout.write(
                self.style.SUCCESS(
                    f'Updated {product.name}: {analytics["views"]} views, '
                    f'{analytics["orders"]} orders, Rs.{analytics["revenue"]} revenue'
                )
            )
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully updated analytics for {products.count()} products')
        )