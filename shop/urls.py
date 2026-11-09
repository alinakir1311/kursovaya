from django.urls import path
from . import views
urlpatterns = [path('', views.home, name='home'), path('guide/', views.guide, name='guide'), path('catalog/', views.catalog, name='catalog'),
    path('catalog/<slug:slug>/', views.product, name='product'), path('cart/', views.cart_detail, name='cart'),
    path('cart/<int:pk>/', views.cart_change, name='cart_change'), path('checkout/', views.checkout, name='checkout'),
    path('accounts/signup/', views.signup, name='signup'), path('orders/', views.orders, name='orders'),
    path('orders/<int:pk>/', views.order_detail, name='order'), path('bundles/', views.bundles, name='bundles'),
    path('bundles/<int:pk>/add/', views.bundle_add, name='bundle_add')]
