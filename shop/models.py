from decimal import Decimal
from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Category(models.Model):
    name = models.CharField('Название', max_length=100)
    slug = models.SlugField(unique=True)
    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
    def __str__(self):
        return self.name


class Brand(models.Model):
    name = models.CharField('Название', max_length=100, unique=True)
    class Meta:
        verbose_name = 'Бренд'
        verbose_name_plural = 'Бренды'
    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.PROTECT, verbose_name='Категория')
    brand = models.ForeignKey(Brand, on_delete=models.PROTECT, verbose_name='Бренд')
    name = models.CharField('Название', max_length=180)
    slug = models.SlugField(unique=True)
    description = models.TextField('Описание')
    price = models.DecimalField('Цена', max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    stock = models.PositiveIntegerField('Остаток', default=0)
    image = models.ImageField('Фото', upload_to='products/', blank=True)
    specifications = models.JSONField('Характеристики', default=dict, blank=True)
    is_active = models.BooleanField('В продаже', default=True)
    class Meta:
        ordering = ['id']
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'
        constraints = [models.CheckConstraint(condition=models.Q(price__gt=0), name='product_positive_price')]
    def __str__(self):
        return self.name


class Bundle(models.Model):
    name = models.CharField('Название', max_length=180)
    description = models.TextField('Описание')
    purpose = models.CharField('Назначение', max_length=30, choices=[('upgrade', 'Обновление штатной системы'), ('bass', 'Больше баса'), ('balance', 'Сбалансированный звук')])
    class Meta:
        verbose_name = 'Комплект'
        verbose_name_plural = 'Комплекты'
    def __str__(self):
        return self.name
    @property
    def total(self):
        return sum((i.product.price * i.quantity for i in self.items.all()), Decimal('0'))
    @property
    def available(self):
        items = list(self.items.all())
        return bool(items) and all(i.product.is_active and i.product.stock >= i.quantity for i in items)


class BundleItem(models.Model):
    bundle = models.ForeignKey(Bundle, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT, verbose_name='Товар')
    quantity = models.PositiveIntegerField('Количество', default=1, validators=[MinValueValidator(1)])
    class Meta:
        constraints = [models.UniqueConstraint(fields=['bundle', 'product'], name='unique_bundle_product'),
                       models.CheckConstraint(condition=models.Q(quantity__gte=1), name='bundle_quantity_positive')]


class Order(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, verbose_name='Покупатель')
    full_name = models.CharField('Имя и фамилия', max_length=150)
    phone = models.CharField('Телефон', max_length=30)
    delivery = models.CharField('Получение', max_length=20, choices=[('pickup', 'Самовывоз'), ('courier', 'Доставка курьером')])
    address = models.CharField('Адрес доставки', max_length=250, blank=True)
    comment = models.TextField('Комментарий', blank=True)
    status = models.CharField('Статус', max_length=20, default='new', choices=[('new', 'Новый'), ('processing', 'В обработке'), ('ready', 'Готов к выдаче'), ('completed', 'Завершён')])
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
    @property
    def total(self):
        return sum((i.subtotal for i in self.items.all()), Decimal('0'))
    def __str__(self):
        return f'Заказ №{self.pk}'


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    name = models.CharField(max_length=180)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    @property
    def subtotal(self):
        return self.price * self.quantity
