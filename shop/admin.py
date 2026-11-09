from django.contrib import admin
from .models import Brand, Bundle, BundleItem, Category, Order, OrderItem, Product

admin.site.site_header = 'АвтоРитм · Управление магазином'
admin.site.site_title = 'АвтоРитм'
admin.site.register([Brand, Category])

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'brand', 'price', 'stock', 'is_active']
    list_filter = ['category', 'brand', 'is_active']
    search_fields = ['name']
    prepopulated_fields = {'slug': ('name',)}

class BundleInline(admin.TabularInline):
    model = BundleItem
    extra = 1

@admin.register(Bundle)
class BundleAdmin(admin.ModelAdmin):
    inlines = [BundleInline]

class OrderInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    can_delete = False
    readonly_fields = ['product', 'name', 'price', 'quantity']
    def has_add_permission(self, request, obj=None):
        return False

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'full_name', 'status', 'delivery', 'created_at']
    list_filter = ['status', 'delivery']
    search_fields = ['full_name', 'phone']
    readonly_fields = ['user', 'full_name', 'phone', 'delivery', 'address', 'comment', 'created_at']
    inlines = [OrderInline]
    def has_add_permission(self, request):
        return False
    def has_delete_permission(self, request, obj=None):
        return False
