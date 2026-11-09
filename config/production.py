"""Settings for the dedicated Ubuntu server, behind its local Nginx proxy."""
from .settings import *

DEBUG = False
SECRET_KEY = os.environ['DJANGO_SECRET_KEY']
ALLOWED_HOSTS = [os.environ['SITE_IP']]
STATIC_URL = '/static/'
STATIC_ROOT = '/var/lib/avtoritm/static'
MEDIA_ROOT = '/var/lib/avtoritm/media'
DATABASES = {'default': {
    'ENGINE': 'django.db.backends.postgresql',
    'NAME': 'avtoritm',
    'USER': 'avtoritm',
    'HOST': '/var/run/postgresql',
}}
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 86400
