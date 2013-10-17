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
from django.conf.urls import url, patterns
from django.views.defaults import page_not_found
from django.views.generic.base import RedirectView
from django.conf import settings
from django.views.static import serve
from cmbarter.users.decorators import max_age

serve_max_age = max_age(12096000)(serve)

urlpatterns = patterns('',
    (r'^$', RedirectView.as_view(url='/login/')),
)

urlpatterns += patterns('',
   (r'^doc/([a-z-]{2,5})/$', 'cmbarter.users.views.show_manual'),
   (r'^doc/(?P<path>.*)$', serve_max_age, {'document_root': settings.CMBARTER_DEV_DOC_ROOT }),
   (r'^static/(?P<path>.*)$', serve_max_age, {
            'document_root': settings.CMBARTER_DEV_STATIC_ROOT }),
)

urlpatterns += patterns('cmbarter.users.views',
    url(r'^login/$', 'login', name='users-login'),
    (r'^login-captcha/$', 'login_captcha'),
    (r'^about/$', 'show_about'),
    (r'^about/([a-z-]{2,5})/$', 'set_language'),
    (r'^signup/$', 'signup'),
    (r'^search/([0-9]{1,9})/$', 'search'),
    (r'^confirm/([0-9]{1,9})/([0-9A-Za-z_-]{20})/$', 'verify_email'),
    (r'^cancel/([0-9]{1,9})/([0-9A-Za-z_-]{20})/$', 'cancel_email'),
    (r'^cancel/success/$', 'report_cancel_email_success'),
    (r'^([0-9]{1,9})/logout/$', 'logout'),
    (r'^([0-9]{1,9})/$', 'show_trader'),
    (r'^([0-9]{1,9})/signup-success/$', 'report_signup_success'),
    url(r'^([0-9]{1,9})/create-profile/$', 'create_profile', name='users-profile'),
)

urlpatterns += patterns('cmbarter.profiles.views',
    url(r'^([0-9]{1,9})/check-email/$', 'check_email_verification', name='profiles-check-email'),
    url(r'^([0-9]{1,9})/traders/([0-9]{1,9})/$', 'show_profile', name='profiles-trader'),
    (r'^([0-9]{1,9})/traders/([0-9]{1,9})/add-to-partners/$', 'add_partner'),
    (r'^([0-9]{1,9})/traders/$', 'find_trader'),
    (r'^([0-9]{1,9})/email-customers/$', 'email_customers'),
    (r'^([0-9]{1,9})/email-customers/success/$', 'report_email_customers_success'),
    (r'^([0-9]{1,9})/find-partner/$', 'find_trader', {'tmpl': 'find_partner.html'}),
    (r'^([0-9]{1,9})/edit-profile/$', 'edit_profile'),                        
    (r'^([0-9]{1,9})/upload-photograph/$', 'upload_photograph'),
    (r'^([0-9]{1,9})/change-password/$', 'change_password'),
    (r'^([0-9]{1,9})/change-password/success/$', 'report_change_password_success'),
    (r'^([0-9]{1,9})/change-username/$', 'change_username'),
    (r'^([0-9]{1,9})/change-username/success/$', 'report_change_username_success'),
    (r'^([0-9]{1,9})/partners/$', 'show_partners'),
    (r'^([0-9]{1,9})/partners/([0-9]{1,9})/remove/$', 'remove_partner'),
    (r'^([0-9]{1,9})/partners/([0-9]{1,9})/suggested-partners/$', 'show_suggested_partners'),
    (r'^([0-9]{1,9})/images/([0-9]{1,9})/([0-9]{1,9})/$', 'show_image'),
    url(r'^static/no_img.gif$', page_not_found, name='profiles-no-image'),
)

urlpatterns += patterns('cmbarter.products.views',
    url(r'^([0-9]{1,9})/pricelist/$', 'update_pricelist', name='products-pricelist'),
    (r'^([0-9]{1,9})/pricelist/([0-9]{1,9})/remove/$', 'remove_pricelist_item'),
    (r'^([0-9]{1,9})/pricelist/success/([0-9]{1,9})/$', 'report_update_pricelist_success'),
    (r'^([0-9]{1,9})/pricelist/new/$', 'create_product'),
    (r'^([0-9]{1,9})/pricelist/new/success/$', 'report_create_product_success'),
    url(r'^([0-9]{1,9})/shopping-list/$', 'update_shopping_list', name='products-shopping-list'),
    (r'^([0-9]{1,9})/shopping-list/success/([0-9]{1,9})/$', 'report_update_shopping_list_success'),
    (r'^([0-9]{1,9})/traders/([0-9]{1,9})/products/([0-9]{1,9})/$', 'show_product'),
    (r'^([0-9]{1,9})/traders/([0-9]{1,9})/products/([0-9]{1,9})/add/$', 'add_shopping_list_item'),
    url(r'^([0-9]{1,9})/traders/([0-9]{1,9})/unknown-product/$', 'show_unknown_product', 
        name='products-unknown-product'),
    url(r'^([0-9]{1,9})/partners/([0-9]{1,9})/$', 'show_partner_pricelist', 
        name='products-partner-pricelist'),
)

urlpatterns += patterns('cmbarter.deposits.views',
    url(r'^([0-9]{1,9})/unconfirmed-transactions/$', 'show_unconfirmed_transactions', 
        name='deposits-unconfirmed-transactions'),
    (r'^([0-9]{1,9})/unconfirmed-transactions/confirmation/([0-9]{1,9})/$', 
        'report_transactions_confirmation'),
    (r'^([0-9]{1,9})/find-customer/$', 'find_customer'),
    (r'^([0-9]{1,9})/transaction-commit/$', 'report_transaction_commit'),
    (r'^([0-9]{1,9})/receipt/$', 'show_unconfirmed_receipts'),
    (r'^([0-9]{1,9})/receipt/confirmation/$', 'report_receipts_confirmation'),
    (r'^([0-9]{1,9})/traders/([0-9]{1,9})/deposits/$', 'show_deposits'),
    (r'^([0-9]{1,9})/traders/([0-9]{1,9})/deposits/new/$', 'make_deposit'),
    (r'^([0-9]{1,9})/traders/([0-9]{1,9})/deposits/([0-9]{1,9})/$', 'make_withdrawal'),
    (r'^([0-9]{1,9})/traders/([0-9]{1,9})/transactions/$', 'show_customer_transactions'),
    (r'^([0-9]{1,9})/partners/([0-9]{1,9})/transactions/$', 'show_partner_transactions'),
)

urlpatterns += patterns('cmbarter.orders.views',
    (r'^([0-9]{1,9})/orders/$', 'show_my_order_list'),
    (r'^([0-9]{1,9})/orders/([0-9]{1,9})/$', 'show_my_order'),
    (r'^([0-9]{1,9})/orders/([0-9]{1,9})/deleted/$', 'report_my_order_deleted'),
    (r'^([0-9]{1,9})/orders/([0-9]{1,9})/executed/$', 'report_my_order_unexpected_execution'),
    (r'^([0-9]{1,9})/traders/([0-9]{1,9})/orders/$', 'show_customer_order_list'),
    (r'^([0-9]{1,9})/traders/([0-9]{1,9})/orders/([0-9]{1,9})/$', 'review_customer_order'),
    (r'^([0-9]{1,9})/traders/([0-9]{1,9})/products/([0-9]{1,9})/order/$', 'create_order'),
    (r'^([0-9]{1,9})/traders/([0-9]{1,9})/products/([0-9]{1,9})/payments/$', 'show_payments'),
)

urlpatterns += patterns('cmbarter.deals.views',
    (r'^([0-9]{1,9})/customer-deals/([0-9]{1,4})-([0-9]{1,2})-([0-9]{1,2})/$', 'show_customer_deals'),
    (r'^([0-9]{1,9})/customer-deals/$', 'show_todays_customer_deals'),
    (r'^([0-9]{1,9})/my-deals/([0-9]{1,4})-([0-9]{1,2})-([0-9]{1,2})/$', 'show_my_deals'),
    (r'^([0-9]{1,9})/my-deals/$', 'show_my_todays_deals'),
    (r'^([0-9]{1,9})/completed-deals/$', 'show_unconfirmed_deals'),
    (r'^([0-9]{1,9})/completed-deals/confirmation/([0-9]{1,9})/$', 'report_deals_confirmation'),
)

urlpatterns += patterns('cmbarter.mobile.views',
    url(r'^mobile/$', 'login', name='mobile-login'),
    (r'^mobile/insecure/$', 'login', {'tmpl': 'xhtml-mp/login_insecure.html'}),
    (r'^mobile/no-profile/$', 'report_no_profile'),                        
    (r'^mobile/lang/([a-z-]{2,5})/$', 'set_language'),
    (r'^mobile/([0-9A-Za-z_-]{20})/images/([0-9]{1,9})/([0-9]{1,9})/$', 'show_image'),
    (r'^mobile/([0-9A-Za-z_-]{20})/shopping-list/$', 'show_shopping_list'),
    (r'^mobile/([0-9A-Za-z_-]{20})/partners/$', 'show_partners'),
    (r'^mobile/([0-9A-Za-z_-]{20})/find-partner/$', 'find_trader'),
    (r'^mobile/([0-9A-Za-z_-]{20})/traders/([0-9]{1,9})/$', 'show_profile'),
    (r'^mobile/([0-9A-Za-z_-]{20})/traders/([0-9]{1,9})/add-to-partners/$', 'add_partner'),
    (r'^mobile/([0-9A-Za-z_-]{20})/partners/([0-9]{1,9})/$', 'show_partner_pricelist'),
    (r'^mobile/([0-9A-Za-z_-]{20})/traders/([0-9]{1,9})/products/([0-9]{1,9})/$', 'show_product'),
    (r'^mobile/([0-9A-Za-z_-]{20})/traders/([0-9]{1,9})/products/([0-9]{1,9})/add/$',
        'add_shopping_list_item'),
    (r'^mobile/([0-9A-Za-z_-]{20})/traders/([0-9]{1,9})/products/([0-9]{1,9})/order/$', 'create_order'),
    (r'^mobile/([0-9A-Za-z_-]{20})/traders/([0-9]{1,9})/products/([0-9]{1,9})/payments/$', 
        'show_payments'),
    (r'^mobile/([0-9A-Za-z_-]{20})/unconfirmed-transactions/$', 'show_unconfirmed_transactions'),
    (r'^mobile/([0-9A-Za-z_-]{20})/orders/([0-9]{1,9})/$', 'show_my_order'),
    (r'^mobile/([0-9A-Za-z_-]{20})/orders/$', 'show_my_order_list'),
    (r'^mobile/([0-9A-Za-z_-]{20})/orders/([0-9]{1,9})/deleted/$', 'report_my_order_deleted'),
    (r'^mobile/([0-9A-Za-z_-]{20})/orders/([0-9]{1,9})/executed/$', 
        'report_my_order_unexpected_execution'),
    (r'^mobile/([0-9A-Za-z_-]{20})/find-customer/$', 'find_customer'),
    (r'^mobile/([0-9A-Za-z_-]{20})/traders/([0-9]{1,9})/deposits/$', 'show_deposits'),
    (r'^mobile/([0-9A-Za-z_-]{20})/traders/([0-9]{1,9})/deposits/new/$', 'make_deposit'),
    (r'^mobile/([0-9A-Za-z_-]{20})/traders/([0-9]{1,9})/deposits/([0-9]{1,9})/$', 'make_withdrawal'),
    (r'^mobile/([0-9A-Za-z_-]{20})/traders/([0-9]{1,9})/unknown-product/$', 'show_unknown_product'),
    (r'^mobile/([0-9A-Za-z_-]{20})/completed-deals/$', 'show_unconfirmed_deals'),
    (r'^mobile/([0-9A-Za-z_-]{20})/receipt/$', 'report_transaction_commit'),
    (r'^mobile/([0-9A-Za-z_-]{20})/edit-profile/$', 'edit_profile'),
    (r'^mobile/([0-9A-Za-z_-]{20})/trader-not-found/$', 'report_trader_not_found'),
    (r'^mobile/([0-9A-Za-z_-]{20})/logout/$', 'logout'),
)
