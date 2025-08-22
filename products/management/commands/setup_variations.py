from django.core.management.base import BaseCommand
from products.models import VariationType, VariationOption, CategoryVariation, Category

class Command(BaseCommand):
    help = 'Setup initial product variations'

    def handle(self, *args, **options):
        # Create Variation Types
        color_type, _ = VariationType.objects.get_or_create(
            name='Color',
            defaults={'display_name': 'Choose Color'}
        )
        
        size_type, _ = VariationType.objects.get_or_create(
            name='Size',
            defaults={'display_name': 'Select Size'}
        )
        
        storage_type, _ = VariationType.objects.get_or_create(
            name='Storage',
            defaults={'display_name': 'Storage Capacity'}
        )

        # Create Color Options
        colors = [
            ('Red', 'Bright Red', '#FF0000'),
            ('Blue', 'Ocean Blue', '#0066CC'),
            ('Black', 'Jet Black', '#000000'),
            ('White', 'Pure White', '#FFFFFF'),
            ('Green', 'Forest Green', '#228B22'),
            ('Yellow', 'Sunshine Yellow', '#FFD700'),
        ]
        
        for value, display, code in colors:
            VariationOption.objects.get_or_create(
                variation_type=color_type,
                value=value,
                defaults={'display_value': display, 'color_code': code}
            )

        # Create Size Options
        sizes = ['XS', 'S', 'M', 'L', 'XL', 'XXL']
        for i, size in enumerate(sizes):
            VariationOption.objects.get_or_create(
                variation_type=size_type,
                value=size,
                defaults={'sort_order': i}
            )

        # Create Storage Options
        storages = ['64GB', '128GB', '256GB', '512GB', '1TB']
        for i, storage in enumerate(storages):
            VariationOption.objects.get_or_create(
                variation_type=storage_type,
                value=storage,
                defaults={'sort_order': i}
            )

        # Link variations to categories
        try:
            clothing_cat = Category.objects.get(category_name__icontains='cloth')
            CategoryVariation.objects.get_or_create(
                category=clothing_cat,
                variation_type=color_type,
                defaults={'sort_order': 1}
            )
            CategoryVariation.objects.get_or_create(
                category=clothing_cat,
                variation_type=size_type,
                defaults={'sort_order': 2, 'is_required': True}
            )
        except Category.DoesNotExist:
            pass

        self.stdout.write(
            self.style.SUCCESS('Successfully setup product variations')
        )