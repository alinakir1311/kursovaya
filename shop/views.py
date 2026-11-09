from decimal import Decimal, InvalidOperation
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Prefetch
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from . import cart
from .forms import CheckoutForm, SignupForm
from .models import Brand, Bundle, BundleItem, Category, Order, Product
from .services import place_order


def money(value):
    try:
        number = Decimal(value)
        return number if number.is_finite() and 0 <= number <= 99999999 else None
    except (InvalidOperation, TypeError):
        return None


def home(request):
    return render(request, 'shop/home.html', {'products': Product.objects.filter(is_active=True, slug__in=['speakers-1', 'subwoofers-2', 'amplifiers-3', 'head-units-3']).select_related('category', 'brand'), 'categories': Category.objects.all()})


def guide(request):
    return render(request, 'shop/guide.html')


def catalog(request):
    products = Product.objects.filter(is_active=True).select_related('category', 'brand')
    if query := request.GET.get('q', '').strip():
        products = products.filter(Q(name__icontains=query) | Q(brand__name__icontains=query))
    if category := request.GET.get('category'):
        products = products.filter(category__slug=category)
    if brand := request.GET.get('brand'):
        products = products.filter(brand__name=brand)
    for key, lookup in [('min', 'price__gte'), ('max', 'price__lte')]:
        value = money(request.GET.get(key))
        if value is not None:
            products = products.filter(**{lookup: value})
    if request.GET.get('available'):
        products = products.filter(stock__gt=0)
    products = products.order_by({'price': 'price', '-price': '-price', 'name': 'name'}.get(request.GET.get('sort'), 'id'))
    page = Paginator(products, 12).get_page(request.GET.get('page'))
    params = request.GET.copy()
    params.pop('page', None)
    return render(request, 'shop/catalog.html', {'page': page, 'params': params.urlencode(), 'categories': Category.objects.all(), 'brands': Brand.objects.all()})


def product(request, slug):
    item = get_object_or_404(Product.objects.select_related('category', 'brand'), slug=slug, is_active=True)
    return render(request, 'shop/product.html', {'product': item})


@require_POST
def cart_change(request, pk):
    item = get_object_or_404(Product, pk=pk)
    data = request.session.get('cart', {}).copy()
    try:
        quantity = int(request.POST.get('quantity', '1'))
        if request.POST.get('action') == 'remove':
            data.pop(str(pk), None)
        else:
            if request.POST.get('action') != 'set':
                quantity += data.get(str(pk), 0)
            if not item.is_active or not 1 <= quantity <= min(item.stock, 99):
                raise ValueError
            data[str(pk)] = quantity
        request.session['cart'] = data
        messages.success(request, 'Корзина обновлена.')
    except ValueError:
        messages.error(request, 'Проверьте количество и наличие товара (не более 99 шт.).')
    return redirect('cart')


def cart_detail(request):
    items = cart.rows(request)
    return render(request, 'shop/cart.html', {'items': items, 'total': cart.total(items)})


@login_required
def checkout(request):
    items = cart.rows(request)
    if not items:
        return redirect('cart')
    form = CheckoutForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        try:
            order = place_order(request.user, request.session.get('cart', {}), form)
        except ValueError as exc:
            form.add_error(None, str(exc))
        else:
            request.session['cart'] = {}
            messages.success(request, f'Заказ №{order.pk} оформлен. Оплата при получении.')
            return redirect('order', pk=order.pk)
    return render(request, 'shop/form.html', {'form': form, 'title': 'Оформление заказа', 'total': cart.total(items), 'checkout': True})


def signup(request):
    form = SignupForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        login(request, form.save())
        return redirect('cart' if request.session.get('cart') else 'orders')
    return render(request, 'shop/form.html', {'form': form, 'title': 'Создать аккаунт'})


@login_required
def orders(request):
    return render(request, 'shop/orders.html', {'orders': Order.objects.filter(user=request.user).prefetch_related('items')})


@login_required
def order_detail(request, pk):
    order = get_object_or_404(Order.objects.prefetch_related('items'), pk=pk, user=request.user)
    return render(request, 'shop/order.html', {'order': order})


def bundles(request):
    sets = Bundle.objects.prefetch_related(Prefetch('items', queryset=BundleItem.objects.select_related('product')))
    if purpose := request.GET.get('purpose'):
        sets = sets.filter(purpose=purpose)
    budget = money(request.GET.get('budget'))
    sets = [b for b in sets if budget is None or b.total <= budget]
    return render(request, 'shop/bundles.html', {'bundles': sets, 'purposes': Bundle._meta.get_field('purpose').choices})


@require_POST
def bundle_add(request, pk):
    bundle = get_object_or_404(Bundle.objects.prefetch_related('items__product'), pk=pk)
    data = request.session.get('cart', {}).copy()
    if not bundle.available:
        messages.error(request, 'Комплект временно недоступен.')
        return redirect('bundles')
    for item in bundle.items.all():
        key = str(item.product_id)
        quantity = data.get(key, 0) + item.quantity
        if quantity > min(item.product.stock, 99):
            messages.error(request, 'Не хватает товаров с учётом вашей корзины.')
            return redirect('cart')
        data[key] = quantity
    request.session['cart'] = data
    messages.success(request, 'Комплект добавлен в корзину.')
    return redirect('cart')
