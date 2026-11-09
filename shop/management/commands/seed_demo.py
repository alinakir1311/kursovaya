from django.core.management.base import BaseCommand
from django.db import transaction
from shop.models import Brand, Bundle, BundleItem, Category, Product


class Command(BaseCommand):
    help = 'Добавить демонстрационные товары и комплекты без перезаписи существующих'

    @transaction.atomic
    def handle(self, *args, **options):
        groups = [
            ('speakers', 'Акустика', 4200, {'Тип': 'Компонентная', 'Диаметр': '16,5 см', 'Мощность RMS': '60 Вт', 'Сопротивление': '4 Ом'}),
            ('subwoofers', 'Сабвуферы', 7500, {'Диаметр': '30 см', 'Мощность RMS': '300 Вт', 'Сопротивление': '4 Ом'}),
            ('amplifiers', 'Усилители', 8900, {'Каналы': '4', 'Мощность RMS при 4 Ом': '4 × 60 Вт', 'Класс': 'AB'}),
            ('head-units', 'Магнитолы', 6500, {'Размер': '1 DIN', 'Bluetooth': 'Есть', 'USB': 'Есть'}),
            ('cables', 'Кабели и подключение', 1900, {'Тип': 'Установочный набор', 'Длина силового кабеля': '5 м'}),
            ('accessories', 'Аксессуары', 900, {'Тип': 'Монтажные аксессуары', 'Комплектность': '1 набор'}),
        ]
        brands = [Brand.objects.get_or_create(name=n)[0] for n in ['Ritm Audio', 'Drive Sound', 'Pulse Lab', 'Road Beat', 'Bass Line']]
        products = {}
        for slug, name, price, specs in groups:
            category, _ = Category.objects.get_or_create(slug=slug, defaults={'name': name})
            for i, brand in enumerate(brands):
                product, _ = Product.objects.get_or_create(slug=f'{slug}-{i + 1}', defaults={
                    'category': category, 'brand': brand, 'name': f'{brand.name} {name} {100 + i * 20}',
                    'description': f'{name} для автомобильной аудиосистемы. Демонстрационная модель учебного каталога; бренд и характеристики вымышлены.',
                    'price': price + i * 1300, 'stock': 8 + i * 3, 'specifications': specs})
                products[(slug, i)] = product
        for name, purpose, description, parts in [
            ('Первое обновление', 'upgrade', 'Магнитола, акустика и набор подключения для знакомства с новым звучанием.', [('speakers', 0), ('head-units', 0), ('cables', 0)]),
            ('Бас в движении', 'bass', 'Сабвуфер, усилитель и подключение — основа басового дополнения системы.', [('subwoofers', 1), ('amplifiers', 1), ('cables', 1)]),
            ('Баланс на каждый день', 'balance', 'Акустика, усилитель, магнитола и кабели в одном наборе.', [('speakers', 2), ('amplifiers', 2), ('head-units', 2), ('cables', 2)]),
        ]:
            bundle, created = Bundle.objects.get_or_create(name=name, defaults={'purpose': purpose, 'description': description})
            if created:
                for part in parts:
                    BundleItem.objects.create(bundle=bundle, product=products[part])
        self.stdout.write(self.style.SUCCESS('Готово: 30 демонстрационных товаров и 3 комплекта (повторный запуск безопасен).'))
