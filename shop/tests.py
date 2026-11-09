from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse
from .models import Bundle, Order, Product


class ShopTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_demo', verbosity=0)
        cls.user = get_user_model().objects.create_user('buyer', password='Example-pass-837')
        cls.other = get_user_model().objects.create_user('other', password='Example-pass-837')

    def setUp(self):
        self.product = Product.objects.first()
        self.checkout_data = {'full_name': 'Иван Петров', 'phone': '+7 (999) 123-45-67', 'delivery': 'pickup'}

    def add(self, product=None, quantity=1):
        return self.client.post(reverse('cart_change', args=[(product or self.product).pk]), {'quantity': quantity})

    def test_pages_render(self):
        for name in ['home', 'catalog', 'cart', 'bundles', 'login', 'signup']:
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)
        self.assertEqual(self.client.get(reverse('product', args=[self.product.slug])).status_code, 200)

    def test_search_price_and_bad_filters(self):
        response = self.client.get(reverse('catalog'), {'q': self.product.name, 'max': self.product.price})
        self.assertEqual(response.context['page'].paginator.count, 1)
        for value in ['bad', 'NaN', 'Infinity', '-1', '1e999999']:
            self.assertEqual(self.client.get(reverse('catalog'), {'max': value}).status_code, 200)

    def test_cart_rejects_invalid_quantities(self):
        for value in [0, -1, 99999, 'bad']:
            self.add(quantity=value)
            self.assertEqual(self.client.session.get('cart', {}), {})
        self.add(quantity=2)
        self.assertEqual(self.client.session['cart'][str(self.product.pk)], 2)
        self.client.post(reverse('cart_change', args=[self.product.pk]), {'action': 'remove'})
        self.assertEqual(self.client.session['cart'], {})

    def test_checkout_snapshots_price_and_prevents_repeat(self):
        self.client.force_login(self.user)
        self.add(quantity=2)
        before = self.product.stock
        response = self.client.post(reverse('checkout'), self.checkout_data)
        order = Order.objects.get()
        self.assertRedirects(response, reverse('order', args=[order.pk]))
        self.assertEqual(order.total, self.product.price * 2)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, before - 2)
        Product.objects.filter(pk=self.product.pk).update(price=Decimal('99999'))
        self.assertEqual(order.items.get().price, self.product.price)
        self.client.post(reverse('checkout'), self.checkout_data)
        self.assertEqual(Order.objects.count(), 1)

    def test_stock_failure_rolls_back_entire_order(self):
        self.client.force_login(self.user)
        second = Product.objects.order_by('pk')[1]
        self.add()
        self.add(second)
        original = self.product.stock
        Product.objects.filter(pk=second.pk).update(stock=0)
        response = self.client.post(reverse('checkout'), self.checkout_data)
        self.assertContains(response, 'Недостаточно товара')
        self.assertFalse(Order.objects.exists())
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, original)
        self.assertEqual(len(self.client.session['cart']), 2)

    def test_private_orders(self):
        self.client.force_login(self.user)
        self.add()
        self.client.post(reverse('checkout'), self.checkout_data)
        order = Order.objects.get()
        self.client = Client()
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(reverse('order', args=[order.pk])).status_code, 404)
        self.assertNotContains(self.client.get(reverse('orders')), f'Заказ №{order.pk}')

    def test_delivery_needs_address(self):
        self.client.force_login(self.user)
        self.add()
        response = self.client.post(reverse('checkout'), {**self.checkout_data, 'delivery': 'courier'})
        self.assertContains(response, 'Укажите адрес доставки')
        self.assertFalse(Order.objects.exists())

    def test_bundle_budget_and_atomic_add(self):
        bundle = Bundle.objects.first()
        response = self.client.get(reverse('bundles'), {'budget': '1'})
        self.assertEqual(response.context['bundles'], [])
        self.client.post(reverse('bundle_add', args=[bundle.pk]))
        self.assertEqual(len(self.client.session['cart']), bundle.items.count())
        saved = self.client.session['cart'].copy()
        last = bundle.items.last().product
        Product.objects.filter(pk=last.pk).update(stock=0)
        self.client.post(reverse('bundle_add', args=[bundle.pk]))
        self.assertEqual(self.client.session['cart'], saved)

    def test_mutations_require_post_and_csrf(self):
        self.assertEqual(self.client.get(reverse('cart_change', args=[self.product.pk])).status_code, 405)
        strict = Client(enforce_csrf_checks=True)
        self.assertEqual(strict.post(reverse('cart_change', args=[self.product.pk]), {'quantity': 1}).status_code, 403)

    def test_seed_is_repeatable(self):
        count = Product.objects.count()
        Product.objects.filter(pk=self.product.pk).update(stock=1)
        call_command('seed_demo', verbosity=0)
        self.assertEqual(Product.objects.count(), count)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 1)

    def test_signup_and_checkout_login_required(self):
        self.add()
        self.assertEqual(self.client.get(reverse('checkout')).status_code, 302)
        self.assertNotContains(self.client.get(reverse('signup')), 'name="password2"')
        response = self.client.post(reverse('signup'), {'username': 'newbuyer', 'password1': '1'})
        self.assertRedirects(response, reverse('cart'))
        self.assertEqual(self.client.get(reverse('checkout')).status_code, 200)
        self.client.logout()
        self.assertTrue(self.client.login(username='newbuyer', password='1'))

    def test_catalog_content_preserves_stock_and_orders(self):
        self.client.force_login(self.user)
        self.add()
        self.client.post(reverse('checkout'), self.checkout_data)
        order = Order.objects.get()
        saved_price = order.total
        self.product.refresh_from_db()
        stock = self.product.stock
        call_command('populate_catalog', verbosity=0)
        call_command('populate_catalog', verbosity=0)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, stock)
        self.assertEqual(order.total, saved_price)
        self.assertEqual(Product.objects.count(), 30)
        self.assertEqual(self.product.name, 'Ritm Audio Stage 165')
        self.assertContains(self.client.get(reverse('guide')), 'Выбрать акустику')
        self.assertContains(self.client.get(reverse('product', args=[self.product.slug])), 'speakers.svg')
