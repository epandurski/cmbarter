# -*- coding: utf-8 -*-
import os.path

#############################################################
##   Circular Multilateral Barter Application Settings:    ##
#############################################################

# Set this to your web server domain name.
CMBARTER_HOST = 'yourdomainname.foo'

# Set this to the PostgreSQL database connection string. For example:
# 'host=localhost port=5432 dbname=cmbarter user=cmbarter
# password=PASSWORD'. For more information, see the PostgreSQL
# documentation. 'dbname=cmbarter' will probably work if you followed
# the instructions in the Installation Guide's "Installation on a
# dedicated server" section.
CMBARTER_DSN = 'dbname=cmbarter'

# Make this unique, and don't share it with anybody.
CMBARTER_SECRET_KEY = 'vjgz%^^7f6-=#%f&5y8qw2ous-l6zz!h+rkpzmxx(ozp%^xeb)'

# This should point to a writable directory that will contain django's
# session files.
CMBARTER_SESSION_DIR = '/var/tmp/cmbarter'

# This should point to a page telling more about you.
CMBARTER_ABOUT_US_URL = 'https://sourceforge.net/projects/cmb/'

# This should be "False" in production.
CMBARTER_DEBUG_MODE = True  

# Sign-up and log-in settings:
CMBARTER_MIN_PASSWORD_LENGTH = 8
CMBARTER_SHOW_CAPTCHA_ON_SIGNUP = True
CMBARTER_SHOW_CAPTCHA_ON_REPETITIVE_LOGIN_FAILURE = True
CMBARTER_REGISTRATION_KEY_IS_REQUIRED = False
CMBARTER_REGISTRATION_KEY_PREFIX = ''

# If a registration key is required for signing up, the next setting
# should point to an URL where users will be instructed how to obtain
# a registration key.  Run "../generate_regkeys.py --help" to learn
# how to generate valid registration keys.
CMBARTER_REGISTRATION_KEY_HELP_URL = ''

# By default, CMB is configured to show CAPTHCA on sign-up, and after
# five unsuccessful attempts to log-in. If you have not altered the
# default behavior, you should obtain your own public/private key pair
# from www.google.com/recaptcha, and put it here:
RECAPTCHA_PUBLIC_KEY='6Ledx7wSAAAAAICFw8vB-2ghpDjzGogPRi6-3FCr'
RECAPTCHA_PIVATE_KEY='6Ledx7wSAAAAAEskQ7Mbi-oqneHDSFVUkxGitn_y'

# The time zone of your users. For example: 'Europe/Rome'
CMBARTER_DEFAULT_USERS_TIME_ZONE = ''  

# Set this to a page where users can search for trusted partners.
CMBARTER_SEARCH_PARTNERS_URL = ''

# This is the maximum size in bytes for users' uploaded photographs.
# If you decide to increase this value, do not forget to increase the
# "LimitRequestBody" directive in your Apache configuration
# accordingly.
CMBARTER_MAX_IMAGE_SIZE = 716800

# This is the maximum amount of pixels (width * height) in users'
# uploaded photographs.
CMBARTER_MAX_IMAGE_PIXELS = 30000000

# By default, CMB is configured to maintain a whitelist of "good" IP
# addresses. This auto-generated whitelist can be used to configure
# your firewall to protect your web-servers from DoS attacks (see the
# "show_whitelist.py" command-line tool).
# To be able to reliably determine the IP addresses of your clients,
# CMB should know the IP address(es) of the reverse proxy server(s) in
# your network.
# If you use reverse proxy servers, list their IPs here.
CMBARTER_REVERSE_PROXIES = ['127.0.0.1', '::1']

# Usually, you do not need to change anything bellow this line.
CMBARTER_MAINTAIN_IP_WHITELIST = True
CMBARTER_HTTP_X_FORWARDED_FOR_IS_TRUSTWORTHY = False
CMBARTER_INSERT_BIDI_MARKS = False 
CMBARTER_HOST_IS_SPAM_LISTED = False
CMBARTER_HISTORY_HORISON_DAYS = 26
CMBARTER_SESSION_TOUCH_MINUTES = 10
CMBARTER_PRICE_PREFIXES = set([u'', u'$', u'\u00A3', u'\u20AC'])
CMBARTER_PRICE_SUFFIXES = set([u'', u'\u20AC', u'ЛВ', u'ЛВ.'])
CMBARTER_TRX_COST_QUOTA = 50000.0
CMBARTER_SEARCH_MAX_PER_SECOND = 10
CMBARTER_SEARCH_MAX_BURST = 100
CMBARTER_TURN_IS_RUNNING_TEMPLATE = 'turn_is_running.html'
CMBARTER_TURN_IS_RUNNING_MOBILE_TEMPLATE = 'xhtml-mp/turn_is_running.html'
CMBARTER_DOC_ROOT_URL = '/doc'
CMBARTER_PROJECT_DIR = os.path.dirname(__file__)
CMBARTER_DEV_DOC_ROOT = os.path.join(CMBARTER_PROJECT_DIR, '../doc')
CMBARTER_DEV_STATIC_ROOT = os.path.join(CMBARTER_PROJECT_DIR, '../static')



###########################################
## Django settings:                      ##
###########################################

assert CMBARTER_SHOW_CAPTCHA_ON_SIGNUP or CMBARTER_REGISTRATION_KEY_IS_REQUIRED

DEBUG = CMBARTER_DEBUG_MODE
TEMPLATE_DEBUG = DEBUG
SILENCED_SYSTEM_CHECKS = []

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

TIME_ZONE = 'America/Chicago'

LANGUAGE_CODE = 'en'
LANGUAGES = (
    ('en', u'english'),
    ('bg', u'български'),
)

LANGUAGE_COOKIE_NAME = 'cmbarter_language'

USE_I18N = True

LOCALE_PATHS = (
    os.path.join(CMBARTER_PROJECT_DIR, 'locale'),
)

MEDIA_ROOT = ''
MEDIA_URL = ''

SECRET_KEY = CMBARTER_SECRET_KEY

ALLOWED_HOSTS = [CMBARTER_HOST, 'localhost', '127.0.0.1', '[::1]']

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
) if DEBUG else (
    ('django.template.loaders.cached.Loader', (
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader',
    )),
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
)

# Newer versions of django (1.10+) insist that middleware settings are
# defined in the TEMPLATES variable. It even issues a warning if
# old-style and new-style template settings coexist. We therefore
# silence this warning.
MIDDLEWARE = [
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
]
SILENCED_SYSTEM_CHECKS += ["1_10.W001"]

ROOT_URLCONF = 'cmbarter.urls'

WSGI_APPLICATION = 'cmbarter.wsgi.application'

TEMPLATE_DIRS = (
    os.path.join(CMBARTER_PROJECT_DIR, 'templates'),
)

# Newer versions of django (1.8+) insist that template settings are
# defined in one place (the TEMPLATES variable). It even issues a
# warning if old-style and new-style template settings coexist. We
# therefore silence this warning.
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': TEMPLATE_DIRS,
        'OPTIONS': {
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
            ],
            'loaders': TEMPLATE_LOADERS
        },
    },
]
SILENCED_SYSTEM_CHECKS += ["1_8.W001"]

# We have no test, therefore we silence the warning saying that test
# execution changed in Django 1.6.
SILENCED_SYSTEM_CHECKS += ["1_6.W001"]

INSTALLED_APPS = (
    'django.contrib.sessions',
    'cmbarter.users',
    'cmbarter.profiles',
    'cmbarter.products',
    'cmbarter.deposits',
    'cmbarter.deals',
    'cmbarter.orders',
    'cmbarter.mobile',
)

FILE_UPLOAD_HANDLERS = ("cmbarter.profiles.forms.PhotographUploadHandler",)

SESSION_SERIALIZER = 'django.contrib.sessions.serializers.PickleSerializer'
SESSION_ENGINE='django.contrib.sessions.backends.file'
SESSION_FILE_PATH=CMBARTER_SESSION_DIR
SESSION_COOKIE_SECURE=False if DEBUG else True
SESSION_EXPIRE_AT_BROWSER_CLOSE=True
SESSION_COOKIE_DOMAIN=None if DEBUG else CMBARTER_HOST

CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE
CSRF_COOKIE_DOMAIN = SESSION_COOKIE_DOMAIN
CSRF_COOKIE_HTTPONLY = True
CSRF_FAILURE_VIEW = 'cmbarter.users.views.csrf_abort'

DATA_UPLOAD_MAX_NUMBER_FIELDS = 1200
DATA_UPLOAD_MAX_MEMORY_SIZE = 50000
