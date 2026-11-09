from decimal import Decimal
from .models import Product


def rows(request):
    cart = request.session.get('cart', {})
    products = Product.objects.filter(pk__in=cart.keys()).select_related('category', 'brand')
    return [{'product': p, 'quantity': cart[str(p.pk)], 'subtotal': p.price * cart[str(p.pk)]} for p in products]


def total(items):
    return sum((r['subtotal'] for r in items), Decimal('0'))


def context(request):
    return {'cart_count': sum(request.session.get('cart', {}).values())}
