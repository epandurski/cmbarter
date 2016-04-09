## The author disclaims copyright to this source code.  In place of
## a legal notice, here is a poem:
##
##   "Metaphysics"
##   
##   Matter: is the music 
##   of the space.
##   Music: is the matter
##   of the soul.
##   
##   Soul: is the space
##   of God.
##   Space: is the soul
##   of logic.
##   
##   Logic: is the god
##   of the mind.
##   God: is the logic
##   of bliss.
##   
##   Bliss: is a mind
##   of music.
##   Mind: is the bliss
##   of the matter.
##   
######################################################################
## This file defines the urls for the whole django-project.
##

import django

# This is an ugly hack that allows URL patterns to work on old django
# versions as well as on new.
if django.VERSION[0] > 1 or django.VERSION[1] >= 8:
    def patterns(prefix, *urls):
        return list(urls)
else:
    from django.conf.urls import patterns

from django.conf.urls import url
from django.views.defaults import page_not_found
from django.views.generic.base import RedirectView
from django.conf import settings
from django.views.static import serve
from cmbarter.users.decorators import max_age

from cmbarter.users import views as users
from cmbarter.profiles import views as profiles
from cmbarter.products import views as products
from cmbarter.deposits import views as deposits
from cmbarter.orders import views as orders
from cmbarter.deals import views as deals
from cmbarter.mobile import views as mobile

serve_max_age = max_age(12096000)(serve)

urlpatterns = patterns('',
    url(r'^$', RedirectView.as_view(url='/login/')),
)

urlpatterns += patterns('',
   url(r'^doc/([a-z-]{2,5})/$', users.show_manual),
   url(r'^doc/(?P<path>.*)$', serve_max_age, {'document_root': settings.CMBARTER_DEV_DOC_ROOT }),
   url(r'^static/(?P<path>.*)$', serve_max_age, {
            'document_root': settings.CMBARTER_DEV_STATIC_ROOT }),
)

urlpatterns += patterns('cmbarter.users.views',
    url(r'^login/$', users.login, name='users-login'),
    url(r'^login-captcha/$', users.login_captcha),
    url(r'^about/$', users.show_about),
    url(r'^about/([a-z-]{2,5})/$', users.set_language),
    url(r'^signup/$', users.signup),
    url(r'^search/([0-9]{1,9})/$', users.search),
    url(r'^confirm/([0-9]{1,9})/([0-9A-Za-z_-]{20})/$', users.verify_email),
    url(r'^cancel/([0-9]{1,9})/([0-9A-Za-z_-]{20})/$', users.cancel_email),
    url(r'^cancel/success/$', users.report_cancel_email_success),
    url(r'^([0-9]{1,9})/logout/$', users.logout),
    url(r'^([0-9]{1,9})/$', users.show_trader),
    url(r'^([0-9]{1,9})/signup-success/$', users.report_signup_success),
    url(r'^([0-9]{1,9})/create-profile/$', users.create_profile, name='users-profile'),
)

urlpatterns += patterns('cmbarter.profiles.views',
    url(r'^([0-9]{1,9})/check-email/$', profiles.check_email_verification, name='profiles-check-email'),
    url(r'^([0-9]{1,9})/traders/([0-9]{1,9})/$', profiles.show_profile, name='profiles-trader'),
    url(r'^([0-9]{1,9})/traders/([0-9]{1,9})/add-to-partners/$', profiles.add_partner),
    url(r'^([0-9]{1,9})/traders/$', profiles.find_trader),
    url(r'^([0-9]{1,9})/email-customers/$', profiles.email_customers),
    url(r'^([0-9]{1,9})/email-customers/success/$', profiles.report_email_customers_success),
    url(r'^([0-9]{1,9})/find-partner/$', profiles.find_trader, {'tmpl': 'find_partner.html'}),
    url(r'^([0-9]{1,9})/edit-profile/$', profiles.edit_profile),                        
    url(r'^([0-9]{1,9})/upload-photograph/$', profiles.upload_photograph),
    url(r'^([0-9]{1,9})/change-password/$', profiles.change_password),
    url(r'^([0-9]{1,9})/change-password/success/$', profiles.report_change_password_success),
    url(r'^([0-9]{1,9})/change-username/$', profiles.change_username),
    url(r'^([0-9]{1,9})/change-username/success/$', profiles.report_change_username_success),
    url(r'^([0-9]{1,9})/partners/$', profiles.show_partners),
    url(r'^([0-9]{1,9})/partners/([0-9]{1,9})/remove/$', profiles.remove_partner),
    url(r'^([0-9]{1,9})/partners/([0-9]{1,9})/suggested-partners/$', profiles.show_suggested_partners),
    url(r'^([0-9]{1,9})/images/([0-9]{1,9})/([0-9]{1,9})/$', profiles.show_image),
    url(r'^static/no_img.gif$', page_not_found, name='profiles-no-image'),
)

urlpatterns += patterns('cmbarter.products.views',
    url(r'^([0-9]{1,9})/pricelist/$', products.update_pricelist, name='products-pricelist'),
    url(r'^([0-9]{1,9})/pricelist/([0-9]{1,9})/remove/$', products.remove_pricelist_item),
    url(r'^([0-9]{1,9})/pricelist/success/([0-9]{1,9})/$', products.report_update_pricelist_success),
    url(r'^([0-9]{1,9})/pricelist/new/$', products.create_product),
    url(r'^([0-9]{1,9})/pricelist/new/success/$', products.report_create_product_success),
    url(r'^([0-9]{1,9})/shopping-list/$', products.update_shopping_list, name='products-shopping-list'),
    url(r'^([0-9]{1,9})/shopping-list/success/([0-9]{1,9})/$', products.report_update_shopping_list_success),
    url(r'^([0-9]{1,9})/traders/([0-9]{1,9})/products/([0-9]{1,9})/$', products.show_product),
    url(r'^([0-9]{1,9})/traders/([0-9]{1,9})/products/([0-9]{1,9})/add/$', products.add_shopping_list_item),
    url(r'^([0-9]{1,9})/traders/([0-9]{1,9})/unknown-product/$', products.show_unknown_product, 
        name='products-unknown-product'),
    url(r'^([0-9]{1,9})/partners/([0-9]{1,9})/$', products.show_partner_pricelist, 
        name='products-partner-pricelist'),
)

urlpatterns += patterns('cmbarter.deposits.views',
    url(r'^([0-9]{1,9})/unconfirmed-transactions/$', deposits.show_unconfirmed_transactions, 
        name='deposits-unconfirmed-transactions'),
    url(r'^([0-9]{1,9})/unconfirmed-transactions/confirmation/([0-9]{1,9})/$', 
        deposits.report_transactions_confirmation),
    url(r'^([0-9]{1,9})/find-customer/$', deposits.find_customer),
    url(r'^([0-9]{1,9})/transaction-commit/$', deposits.report_transaction_commit),
    url(r'^([0-9]{1,9})/receipt/$', deposits.show_unconfirmed_receipts),
    url(r'^([0-9]{1,9})/receipt/confirmation/$', deposits.report_receipts_confirmation),
    url(r'^([0-9]{1,9})/traders/([0-9]{1,9})/deposits/$', deposits.show_deposits),
    url(r'^([0-9]{1,9})/traders/([0-9]{1,9})/deposits/new/$', deposits.make_deposit),
    url(r'^([0-9]{1,9})/traders/([0-9]{1,9})/deposits/([0-9]{1,9})/$', deposits.make_withdrawal),
    url(r'^([0-9]{1,9})/traders/([0-9]{1,9})/transactions/$', deposits.show_customer_transactions),
    url(r'^([0-9]{1,9})/partners/([0-9]{1,9})/transactions/$', deposits.show_partner_transactions),
)

urlpatterns += patterns('cmbarter.orders.views',
    url(r'^([0-9]{1,9})/orders/$', orders.show_my_order_list),
    url(r'^([0-9]{1,9})/orders/([0-9]{1,9})/$', orders.show_my_order),
    url(r'^([0-9]{1,9})/orders/([0-9]{1,9})/deleted/$', orders.report_my_order_deleted),
    url(r'^([0-9]{1,9})/orders/([0-9]{1,9})/executed/$', orders.report_my_order_unexpected_execution),
    url(r'^([0-9]{1,9})/traders/([0-9]{1,9})/orders/$', orders.show_customer_order_list),
    url(r'^([0-9]{1,9})/traders/([0-9]{1,9})/orders/([0-9]{1,9})/$', orders.review_customer_order),
    url(r'^([0-9]{1,9})/traders/([0-9]{1,9})/products/([0-9]{1,9})/order/$', orders.create_order),
    url(r'^([0-9]{1,9})/traders/([0-9]{1,9})/products/([0-9]{1,9})/payments/$', orders.show_payments),
)

urlpatterns += patterns('cmbarter.deals.views',
    url(r'^([0-9]{1,9})/customer-deals/([0-9]{1,4})-([0-9]{1,2})-([0-9]{1,2})/$', deals.show_customer_deals),
    url(r'^([0-9]{1,9})/customer-deals/$', deals.show_todays_customer_deals),
    url(r'^([0-9]{1,9})/my-deals/([0-9]{1,4})-([0-9]{1,2})-([0-9]{1,2})/$', deals.show_my_deals),
    url(r'^([0-9]{1,9})/my-deals/$', deals.show_my_todays_deals),
    url(r'^([0-9]{1,9})/completed-deals/$', deals.show_unconfirmed_deals),
    url(r'^([0-9]{1,9})/completed-deals/confirmation/([0-9]{1,9})/$', deals.report_deals_confirmation),
)

urlpatterns += patterns('cmbarter.mobile.views',
    url(r'^mobile/$', mobile.login, name='mobile-login'),
    url(r'^mobile/insecure/$', mobile.login, {'tmpl': 'xhtml-mp/login_insecure.html'}),
    url(r'^mobile/no-profile/$', mobile.report_no_profile),                        
    url(r'^mobile/lang/([a-z-]{2,5})/$', mobile.set_language),
    url(r'^mobile/([0-9A-Za-z_-]{20})/images/([0-9]{1,9})/([0-9]{1,9})/$', mobile.show_image),
    url(r'^mobile/([0-9A-Za-z_-]{20})/shopping-list/$', mobile.show_shopping_list),
    url(r'^mobile/([0-9A-Za-z_-]{20})/partners/$', mobile.show_partners),
    url(r'^mobile/([0-9A-Za-z_-]{20})/find-partner/$', mobile.find_trader),
    url(r'^mobile/([0-9A-Za-z_-]{20})/traders/([0-9]{1,9})/$', mobile.show_profile),
    url(r'^mobile/([0-9A-Za-z_-]{20})/traders/([0-9]{1,9})/add-to-partners/$', mobile.add_partner),
    url(r'^mobile/([0-9A-Za-z_-]{20})/partners/([0-9]{1,9})/$', mobile.show_partner_pricelist),
    url(r'^mobile/([0-9A-Za-z_-]{20})/traders/([0-9]{1,9})/products/([0-9]{1,9})/$', mobile.show_product),
    url(r'^mobile/([0-9A-Za-z_-]{20})/traders/([0-9]{1,9})/products/([0-9]{1,9})/add/$',
        mobile.add_shopping_list_item),
    url(r'^mobile/([0-9A-Za-z_-]{20})/traders/([0-9]{1,9})/products/([0-9]{1,9})/order/$', mobile.create_order),
    url(r'^mobile/([0-9A-Za-z_-]{20})/traders/([0-9]{1,9})/products/([0-9]{1,9})/payments/$', 
        mobile.show_payments),
    url(r'^mobile/([0-9A-Za-z_-]{20})/unconfirmed-transactions/$', mobile.show_unconfirmed_transactions),
    url(r'^mobile/([0-9A-Za-z_-]{20})/orders/([0-9]{1,9})/$', mobile.show_my_order),
    url(r'^mobile/([0-9A-Za-z_-]{20})/orders/$', mobile.show_my_order_list),
    url(r'^mobile/([0-9A-Za-z_-]{20})/orders/([0-9]{1,9})/deleted/$', mobile.report_my_order_deleted),
    url(r'^mobile/([0-9A-Za-z_-]{20})/orders/([0-9]{1,9})/executed/$', 
        mobile.report_my_order_unexpected_execution),
    url(r'^mobile/([0-9A-Za-z_-]{20})/find-customer/$', mobile.find_customer),
    url(r'^mobile/([0-9A-Za-z_-]{20})/traders/([0-9]{1,9})/deposits/$', mobile.show_deposits),
    url(r'^mobile/([0-9A-Za-z_-]{20})/traders/([0-9]{1,9})/deposits/new/$', mobile.make_deposit),
    url(r'^mobile/([0-9A-Za-z_-]{20})/traders/([0-9]{1,9})/deposits/([0-9]{1,9})/$', mobile.make_withdrawal),
    url(r'^mobile/([0-9A-Za-z_-]{20})/traders/([0-9]{1,9})/unknown-product/$', mobile.show_unknown_product),
    url(r'^mobile/([0-9A-Za-z_-]{20})/completed-deals/$', mobile.show_unconfirmed_deals),
    url(r'^mobile/([0-9A-Za-z_-]{20})/receipt/$', mobile.report_transaction_commit),
    url(r'^mobile/([0-9A-Za-z_-]{20})/edit-profile/$', mobile.edit_profile),
    url(r'^mobile/([0-9A-Za-z_-]{20})/trader-not-found/$', mobile.report_trader_not_found),
    url(r'^mobile/([0-9A-Za-z_-]{20})/logout/$', mobile.logout),
)
