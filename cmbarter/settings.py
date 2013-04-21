# -*- coding: utf-8 -*-
import os.path

#############################################################
##   Circular Multilateral Barter Application Settings:    ##
#############################################################

# Set this to your web server domain name.
CMBARTER_HOST = "yourdomainname.foo"

# Set this to the PostgreSQL database connection string. For example:
# "host=localhost port=5432 dbname=cmbarter user=cmbarter
# password=PASSWORD". For more information, see the PostgreSQL
# documentation. "dbname=cmbarter" should work for you if you followed
# the instructions in the Installation Guide's "Installation on a
# dedicated server" section.
CMBARTER_DSN = "dbname=cmbarter"

# This should point to a writable directory that will contain django's
# session files.
CMBARTER_SESSION_DIR = "/var/tmp/cmbarter"

# This should point to a page telling more about you.
CMBARTER_ABOUT_US_URL = 'https://sourceforge.net/projects/cmb/'

# This should be "False" in production.
CMBARTER_DEBUG_MODE = True  



# Sign-up and log-in settings:
CMBARTER_MIN_PASSWORD_LENGTH = 8
CMBARTER_SHOW_CAPTCHA_ON_SIGNUP = True
CMBARTER_SHOW_CAPTCHA_ON_REPETITIVE_LOGIN = True
CMBARTER_REGISTRATION_KEY_IS_REQUIRED = False
CMBARTER_REGISTRATION_KEY_PREFIX = u''

# If a registration key is required for signing up, the next setting
# should point to an URL where users will be instructed how to obtain
# a registration key.  Run "../generate_regkeys.py --help" to learn
# how to generate valid registration keys.
CMBARTER_REGISTRATION_KEY_HELP_URL = ''

# By default CMB is configured to show CAPTHCA on sign-up, and after
# five unsuccessful attempts to log-in. If you have not altered the
# default behavior, you should obtain your own public/private key pair
# from www.google.com/recaptcha, and put it here:
RECAPTCHA_PUBLIC_KEY='6Ledx7wSAAAAAICFw8vB-2ghpDjzGogPRi6-3FCr'
RECAPTCHA_PIVATE_KEY='6Ledx7wSAAAAAEskQ7Mbi-oqneHDSFVUkxGitn_y'

assert CMBARTER_SHOW_CAPTCHA_ON_SIGNUP or CMBARTER_REGISTRATION_KEY_IS_REQUIRED
assert CMBARTER_SHOW_CAPTCHA_ON_REPETITIVE_LOGIN or CMBARTER_MIN_PASSWORD_LENGTH > 10



# Miscellaneous settings:
CMBARTER_SEARCH_PARTNERS_URL = ''  # Set this to a page where users
                                   # can search for trusted partners.
CMBARTER_MAX_IMAGE_SIZE = 1e6  # This is the maximum size in bytes for
                               # users' uploaded photographs.
CMBARTER_MAX_IMAGE_PIXELS = 30e6  # This is the maximum amount of
                                  # pixels (width * height) in users'
                                  # uploaded photographs.
CMBARTER_INSERT_BIDI_MARKS = False  # You may set this to "True" if
                                    # you do not need to support IE6.
CMBARTER_HOST_IS_SPAM_LISTED = False
CMBARTER_HISTORY_HORISON_DAYS = 26
CMBARTER_SESSION_TOUCH_MINUTES = 30
CMBARTER_PRICE_PREFIXES = [u'$', u'\u00A3', u'\u00A4', u'\u20AC']
CMBARTER_PRICE_SUFFIXES = [u'\u00A4', u'\u20AC', u'ЛВ', u'ЛВ.']
CMBARTER_TRX_COST_QUOTA = 50000.0
CMBARTER_SEARCH_MAX_PER_SECOND = 10
CMBARTER_SEARCH_MAX_BURST = 100
CMBARTER_TURN_IS_RUNNING_TEMPLATE = 'turn_is_running.html'
CMBARTER_TURN_IS_RUNNING_MOBILE_TEMPLATE = 'xhtml-mp/turn_is_running.html'
CMBARTER_DOC_ROOT_URL = '/doc'
CMBARTER_PROJECT_DIR = os.path.dirname(__file__)
CMBARTER_DEV_DOC_ROOT = os.path.join(CMBARTER_PROJECT_DIR, "../doc")
CMBARTER_DEV_STATIC_ROOT = os.path.join(CMBARTER_PROJECT_DIR, "../static")



###########################################
## Django settings:                      ##
###########################################


DEBUG = CMBARTER_DEBUG_MODE
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'

LANGUAGE_CODE = 'en'
LANGUAGES = (
    ('en', u'english'),
    ('bg', u'български'),
)

LANGUAGE_COOKIE_NAME = 'cmbarter_language'

USE_I18N = True

LOCALE_PATHS = (
    os.path.join(CMBARTER_PROJECT_DIR, "locale"),
)

MEDIA_ROOT = ''
MEDIA_URL = ''

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'vjgz%^^7f6-=#%f&5y8qw2ous-l6zz!h+rkpzmxx(ozp%^xeb)'

ALLOWED_HOSTS = [CMBARTER_HOST]

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
    'django.middleware.gzip.GZipMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
)

ROOT_URLCONF = 'cmbarter.urls'

WSGI_APPLICATION = "cmbarter.wsgi.application"

TEMPLATE_DIRS = (
    os.path.join(CMBARTER_PROJECT_DIR, "templates"),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'cmbarter.users',
    'cmbarter.profiles',
    'cmbarter.products',
    'cmbarter.deposits',
    'cmbarter.deals',
    'cmbarter.orders',
    'cmbarter.mobile',
)

SESSION_ENGINE="django.contrib.sessions.backends.file"
SESSION_FILE_PATH=CMBARTER_SESSION_DIR
SESSION_COOKIE_SECURE=False if DEBUG else True
SESSION_EXPIRE_AT_BROWSER_CLOSE=True
SESSION_COOKIE_DOMAIN=None if DEBUG else CMBARTER_HOST

CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE
CSRF_COOKIE_DOMAIN = SESSION_COOKIE_DOMAIN
CSRF_FAILURE_VIEW = 'cmbarter.users.views.csrf_abort'
