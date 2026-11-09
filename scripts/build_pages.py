"""Render the public catalog with an isolated in-memory database."""
import argparse
import os
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
from django.conf import settings

parser = argparse.ArgumentParser()
parser.add_argument('--base-path', default='')
args = parser.parse_args()
base_path = '/' + args.base_path.strip('/') if args.base_path.strip('/') else ''
settings.DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}
settings.STATIC_URL = base_path + '/static/'
django.setup()

from django.core.management import call_command
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.urls import set_script_prefix
from shop.models import Brand, Bundle, Category, Product

set_script_prefix(base_path + '/')
call_command('migrate', verbosity=0)
call_command('populate_catalog', verbosity=0)
output = ROOT / '_site'
output.mkdir(exist_ok=True)
shutil.copytree(ROOT / 'static', output / 'static', dirs_exist_ok=True)
(output / '.nojekyll').touch()


def write_page(route, template, context=None):
    destination = output / route / 'index.html'
    destination.parent.mkdir(parents=True, exist_ok=True)
    html = render_to_string(template, {'pages_demo': True, **(context or {})})
    destination.write_text(html, encoding='utf-8')


products = Product.objects.filter(is_active=True).select_related('category', 'brand')
categories = Category.objects.all()
write_page('', 'shop/home.html', {
    'categories': categories,
    'products': products.filter(slug__in=[
        'speakers-1', 'subwoofers-2', 'amplifiers-3', 'head-units-3',
    ]),
})
write_page('catalog', 'shop/catalog.html', {
    'page': Paginator(products, max(products.count(), 1)).page(1),
    'categories': categories,
    'brands': Brand.objects.all(),
})
for product in products:
    write_page(f'catalog/{product.slug}', 'shop/product.html', {'product': product})
write_page('bundles', 'shop/bundles.html', {
    'bundles': Bundle.objects.prefetch_related('items__product'),
    'purposes': Bundle._meta.get_field('purpose').choices,
})
write_page('guide', 'shop/guide.html')
print(f'Built {len(list(output.rglob("index.html")))} pages in {output}')
