from django.db import transaction
from django.db.models import F
from .models import OrderItem, Product


@transaction.atomic
def place_order(user, cart, form):
    if not cart:
        raise ValueError('Корзина пуста.')
    products = list(Product.objects.select_for_update().filter(pk__in=cart).order_by('pk'))
    if len(products) != len(cart):
        raise ValueError('Состав каталога изменился. Проверьте корзину.')
    order = form.save(commit=False)
    order.user = user
    order.save()
    for product in products:
        quantity = cart[str(product.pk)]
        if not isinstance(quantity, int) or not 1 <= quantity <= 99:
            raise ValueError('Некорректное количество товара.')
        updated = Product.objects.filter(pk=product.pk, is_active=True, stock__gte=quantity).update(stock=F('stock') - quantity)
        if not updated:
            raise ValueError(f'Недостаточно товара «{product.name}». Обновите корзину.')
        OrderItem.objects.create(order=order, product=product, name=product.name, price=product.price, quantity=quantity)
    return order
