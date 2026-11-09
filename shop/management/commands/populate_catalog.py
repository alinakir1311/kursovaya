from collections import Counter
from django.core.management.base import BaseCommand
from django.db import transaction
from shop.catalog_data import BUNDLES, CATALOG, CATEGORIES
from shop.models import Brand, Bundle, BundleItem, Category, Product


class Command(BaseCommand):
    help = 'Наполнить учебный каталог описаниями и характеристиками, сохранив остатки, фотографии и заказы'

    @transaction.atomic
    def handle(self, *args, **options):
        categories = {slug: Category.objects.get_or_create(slug=slug, defaults={'name': name})[0] for slug, name in CATEGORIES.items()}
        counters = Counter()
        for category, brand_name, model, price, description, specs in CATALOG:
            counters[category] += 1
            brand, _ = Brand.objects.get_or_create(name=brand_name)
            slug = f'{category}-{counters[category]}'
            product, created = Product.objects.get_or_create(slug=slug, defaults={
                'category': categories[category], 'brand': brand, 'name': f'{brand_name} {model}',
                'price': price, 'description': description, 'specifications': specs, 'stock': 8 + counters[category] * 3})
            if not created:
                Product.objects.filter(pk=product.pk).update(category=categories[category], brand=brand,
                    name=f'{brand_name} {model}', price=price, description=description, specifications=specs)
        for name, purpose, description, slugs in BUNDLES:
            bundle, _ = Bundle.objects.update_or_create(name=name, defaults={'purpose': purpose, 'description': description})
            for slug in slugs:
                BundleItem.objects.get_or_create(bundle=bundle, product=Product.objects.get(slug=slug), defaults={'quantity': 1})
        self.stdout.write(self.style.SUCCESS('Каталог наполнен: 30 моделей, 6 категорий, 3 комплекта. Остатки и заказы сохранены.'))
