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
## This file contains django view-functions implementing the mobile
## web interface.
##
from __future__ import with_statement
import os, re, base64, datetime, hashlib
from random import random
from functools import wraps
import pytz
from django.conf import settings
from django.shortcuts import render_to_response
from django.core.urlresolvers import reverse
from django.utils.translation import get_language
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseNotAllowed, HttpResponseForbidden, Http404
from django.utils.translation import ugettext_lazy as _
from cmbarter.modules import curiousorm, utils
from cmbarter.users.decorators import report_transaction_cost
import cmbarter.users.forms
import cmbarter.profiles.forms
import cmbarter.orders.forms
import cmbarter.deposits.forms


db = curiousorm.Database(settings.CMBARTER_DSN)

TRX_FIELD = re.compile('^trx-(\d{1,15})$')
HANDOFF_FIELD = re.compile('^handoff-(\d{1,9})$')
DEAL_FIELD = re.compile('^deal-(\d{1,9})-(\d{1,9})-(\d{1,9})$')
A_TURN_IS_RUNNING = re.compile('a turn is running')


def render(request, tmpl, c={}):
    for mimetype in 'application/vnd.wap.xhtml+xml', 'application/xhtml+xml':
        if mimetype in request.META['HTTP_ACCEPT']:
            break
    else:
        mimetype = 'text/html'

    response = render_to_response(tmpl, c, mimetype=mimetype)
    if mimetype == 'text/html':
        # If the response is served as 'text/html' we must explicitly
        # specify the encoding, because the <?xml ...?> declaration
        # will be ignored by the browser.
        response['Content-Type'] = 'text/html;charset=UTF-8'

    return response


def logged_in(view):
    """View decorator that ensures the user is correctly logged in."""

    @wraps(view)
    def fn(request, secret, *args, **kargs):
        try:
            trader_id = db.get_loginkey_trader_id(hashlib.md5(secret).hexdigest())
            if trader_id:
                # Render the response with some HTTP-headers added.
                response = view(request, secret, trader_id, *args, **kargs)
                if 'Cache-Control' not in response:
                    response['Cache-Control'] = 'no-cache, must-revalidate'
                    response['Expires'] = 'Mon, 26 Jul 1997 05:00:00 GMT'
                    response['Last-Modified'] = datetime.datetime.now(pytz.utc).strftime("%d %b %Y %H:%M:%S GMT")
                    response['Pragma'] = 'no-cache'
                return response
            else:
                return login(request, method='GET')

        except curiousorm.PgError, e:
            if getattr(e, 'pgcode', '')==curiousorm.RAISE_EXCEPTION and A_TURN_IS_RUNNING.search(getattr(e, 'pgerror', '')):
                return render(request, settings.CMBARTER_TURN_IS_RUNNING_MOBILE_TEMPLATE)
            else:
                raise
            
    return fn


def has_profile(view):
    """View decorator that ensures the user has entered a profile."""

    @wraps(view)
    @logged_in
    def fn(request, secret, trader_id, *args, **kargs):
        userinfo = db.get_userinfo(trader_id, get_language())
        if not userinfo:
            return login(request, method='GET')
        elif not userinfo['has_profile']:
            db.delete_loginkey(trader_id)
            return report_no_profile(request)
        elif (userinfo['banned_until_ts'] > datetime.datetime.now(pytz.utc)
              or userinfo['accumulated_transaction_cost'] > settings.CMBARTER_TRX_COST_QUOTA):
            return HttpResponseForbidden()
        else:
            if not hasattr(request, '_cmbarter_trx_cost'):
                request._cmbarter_trx_cost = 0.0
            try:
                response = view(request, secret, userinfo, *args, **kargs)  # This may affect request._cmbarter_trx_cost
            except Http404:
                report_transaction_cost(db, trader_id, request._cmbarter_trx_cost)
                request._cmbarter_trx_cost = 0.0
                raise
            else:
                report_transaction_cost(db, trader_id, request._cmbarter_trx_cost)
                request._cmbarter_trx_cost = 0.0
                return response

    return fn
    

def set_language(request, lang):
    r = HttpResponseRedirect("%s?method=GET" % reverse('mobile-login'))
    r.set_cookie(
        key=settings.LANGUAGE_COOKIE_NAME,
        value=lang,
        max_age=60*60*24*365*10)
    return r


def report_no_profile(request, tmpl='xhtml-mp/no_profile.html'):
    # Render everything.
    c = {'settings': settings }
    return render(request, tmpl, c)


@curiousorm.retry_transient_errors
def login(request, tmpl='xhtml-mp/login.html', method=None):
    method = method or request.GET.get('method') or request.method    
    if method == 'POST':
        form = cmbarter.users.forms.LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password_salt = db.get_password_salt(username)
            password_hash = utils.calc_crypt_hash(password_salt + form.cleaned_data['password'])

            authentication = db.login_trader(username, password_hash)

            if settings.CMBARTER_SHOW_CAPTCHA_ON_REPETITIVE_LOGIN and authentication['needs_captcha']:
                form.needs_captcha = True

            elif authentication['is_valid']:
                # Log the user in and redirect him to his start-page.
                while 1:
                    secret = base64.urlsafe_b64encode(os.urandom(15))
                    if db.replace_loginkey(authentication['trader_id'], hashlib.md5(secret).hexdigest()):
                        break
                r = HttpResponseRedirect(reverse(show_shopping_list, args=[secret]))
                r.set_cookie(
                    key='loginkey',
                    value=secret,
                    secure=request.is_secure(),
                    max_age=60*60*24*365*10)
                r.set_cookie(
                    key='username',
                    value=username,
                    max_age=60*60*24*365*10)
                return r
            
            else:
                form.incorrect_login = True

    else:
        if 'loginkey' in request.COOKIES:
            secret = request.COOKIES['loginkey']
            if db.get_loginkey_trader_id(hashlib.md5(secret).hexdigest()):
                return HttpResponseRedirect(reverse(show_shopping_list, args=[secret]))

        form = cmbarter.users.forms.LoginForm(
            initial={'username': request.COOKIES.get('username')})

    # Render everything.
    c = {'settings': settings, 'form': form }
    return render(request, tmpl, c)


@has_profile
def show_image(request, secret, user, trader_id_str, photograph_id_str):

    # Get the image.
    request._cmbarter_trx_cost += 1.0
    img = db.get_image(int(trader_id_str), int(photograph_id_str))
    
    if img:
        # Render the image with the right MIME-type.
        img_buffer = img['raw_content']
        response = HttpResponse(content_type='image/jpeg')
        response['Content-Encoding'] = 'identity'
        response['Content-Length'] = len(img_buffer)
        response['Cache-Control'] = "max-age=1209600"
        response.write(str(img_buffer))
        return response

    return HttpResponseRedirect(reverse('profiles-no-image'))


@has_profile
def show_shopping_list(request, secret, user, tmpl='xhtml-mp/shopping_list.html'):

    # Get user's shopping list.
    items = db.get_shopping_item_list(user['trader_id'])

    # Render everything.
    c = {'settings': settings, 'secret': secret, 'user': user, 'items' : items }
    return render(request, tmpl, c)


@has_profile
def show_partners(request, secret, user, tmpl='xhtml-mp/partners.html'):

    # Get user's list of partners.
    partners = db.get_trust_list(user['trader_id'])

    # Render everything.
    c = {'settings': settings, 'secret': secret, 'user': user, 'partners' : partners }
    return render(request, tmpl, c)


@has_profile
def find_trader(request, secret, user, tmpl='xhtml-mp/find_partner.html', method=None):
    method = method or request.GET.get('method') or request.method    
    if method == 'POST':
        form = cmbarter.profiles.forms.FindTraderForm(request.POST)
        if form.is_valid():
            request._cmbarter_trx_cost += 1.0
            if db.get_profile(form.cleaned_data['id']):
                return show_profile(request, secret, form.cleaned_data['id'])
            else:
                form.wrong_trader_id = True
    else:
        form = cmbarter.profiles.forms.FindTraderForm()

    # Render everything.
    c = {'settings': settings, 'secret': secret, 'user': user, 'form': form }
    return render(request, tmpl, c)


@has_profile
def show_profile(request, secret, user, trader_id_str, tmpl='xhtml-mp/contact_information.html'):
    trader_id = int(trader_id_str)

    # Get trader's profile.
    request._cmbarter_trx_cost += 1.0
    trader = db.get_profile(trader_id)

    # Get trader's pending email verification if there is one.
    email_verification = db.get_email_verification(trader_id)
    
    if trader:
        # Render everything.
        c = {'settings': settings, 'secret': secret,
             'user': user, 'trader': trader,
             'email_verification': email_verification or {} }
        return render(request, tmpl, c)
    
    return report_trader_not_found(request, secret)


@has_profile
@curiousorm.retry_transient_errors
def add_partner(request, secret, user, partner_id_str, tmpl='xhtml-mp/add_partner.html', method=None):
    partner_id = int(partner_id_str)

    method = method or request.GET.get('method') or request.method
    if method == 'POST':
        # Initialize the form
        form = cmbarter.profiles.forms.AddPartnerForm(request.POST)

        # Try to add the partner and skip the rest if everything is OK.
        if form.is_valid():
            request._cmbarter_trx_cost += 4.0
            if db.replace_trust(
                user['trader_id'],
                partner_id,
                form.cleaned_data['name'],
                form.cleaned_data['comment']):

                return show_partner_pricelist(request, secret, partner_id)
            else:
                form.name_collision = True

        # Get partner's profile.
        request._cmbarter_trx_cost += 1.0
        trader = db.get_profile(partner_id)
        if not trader:
            raise Http404
        
    else:
        # Get partner's profile.
        request._cmbarter_trx_cost += 1.0
        trader = db.get_profile(partner_id)
        if not trader:
            raise Http404

        # Initialize the form        
        form = cmbarter.profiles.forms.AddPartnerForm(initial=(
            db.get_trust(user['trader_id'], partner_id)
            or
            {'name': trader['full_name'], 'comment': trader['summary']}))

    # Render everything.
    c =  {'settings': settings, 'secret': secret,
          'user' : user, 'trader': trader, 'form' : form }
    return render(request, tmpl, c)    


@has_profile
def show_partner_pricelist(request, secret, user, partner_id_str, tmpl='xhtml-mp/partner_pricelist.html'):
    partner_id = int(partner_id_str)

    # Make sure this is really a user's partner.
    trust = db.get_trust(user['trader_id'], partner_id)
    
    if trust:
        # Get the set of products that are included in user's shopping-list.
        chosen_products = set()
        for row in db.get_shopping_item_list(user['trader_id'], partner_id):
            chosen_products.add(row['promise_id'])
            
        # Get partners's pricelist.
        products = []
        for o in db.get_product_offer_list(partner_id):
            promise_id = o['promise_id']
            p = { 'offer': o,
                  'is_chosen': promise_id in chosen_products }
            products.append(p)

        # Render everything.
        c = {'settings': settings, 'secret': secret,
             'user': user, 'trust': trust, 'products': products }
        return render(request, tmpl, c)        

    return show_profile(request, secret, partner_id) 


@has_profile
def show_product(request, secret, user, issuer_id_str, promise_id_str, tmpl='xhtml-mp/product.html'):
    issuer_id  = int(issuer_id_str) 
    promise_id = int(promise_id_str)
    
    # Get product's description.
    request._cmbarter_trx_cost += 1.0
    product = db.get_product(issuer_id, promise_id)
    
    if product:
        if user['trader_id'] == issuer_id:
            trust = None
            allow_addition_to_shopping_list = False
        else:
            trust = db.get_trust(user['trader_id'], issuer_id)
            allow_addition_to_shopping_list = (
                bool(trust) and
                not db.get_shopping_item(user['trader_id'], issuer_id, promise_id))

        # Render everything.
        c = {'settings': settings, 'secret': secret,
             'user' : user, 'product': product, 'trust': trust,
             'allow_addition_to_shopping_list': allow_addition_to_shopping_list }
        return render(request, tmpl, c)        

    else:
        return show_unknown_product(request, secret, issuer_id)


@has_profile
@curiousorm.retry_transient_errors
def add_shopping_list_item(request, secret, user, issuer_id_str, promise_id_str, method=None):
    issuer_id  = int(issuer_id_str) 
    promise_id = int(promise_id_str)

    method = method or request.GET.get('method') or request.method    
    if method == 'POST':
        if 'add' in request.POST:
            request._cmbarter_trx_cost += 8.0
            db.insert_shopping_item(user['trader_id'], issuer_id, promise_id)

        return show_partner_pricelist(request, secret, issuer_id)

    return HttpResponseNotAllowed(['POST'])


@has_profile
@curiousorm.retry_transient_errors
def create_order(request, secret, user, partner_id_str, promise_id_str, tmpl='xhtml-mp/create_order.html', method=None):
    partner_id = int(partner_id_str)
    promise_id = int(promise_id_str)
    
    method = method or request.GET.get('method') or request.method    
    if method == 'POST':
        form = cmbarter.orders.forms.CreateOrderForm(request.POST)
        if form.is_valid():
            request._cmbarter_trx_cost += 8.0
            order_id = db.insert_delivery_order(
                user['trader_id'],
                partner_id,
                promise_id,
                form.cleaned_data['amount'],
                form.cleaned_data['carrier'],
                form.cleaned_data['instruction'])

            if order_id:
                return show_my_order(request, secret, order_id, method='GET')
            else:
                form.avl_amount = db.get_deposit_avl_amount(user['trader_id'], partner_id, promise_id)
                form.show_avl_amount = form.avl_amount < form.cleaned_data['amount']
                form.insufficient_amount = True
    else:
        form = cmbarter.orders.forms.CreateOrderForm()

    # Get partner's name.
    trust = db.get_trust(user['trader_id'], partner_id)
    if not trust:
        raise Http404

    # Get product's information.
    product = db.get_product(partner_id, promise_id)
    if not product:
        raise Http404

    # Truncate form.avl_amount
    if hasattr(form, 'avl_amount'):
        form.avl_amount = utils.truncate(form.avl_amount, product['epsilon'])

    # Render everything.
    c = {'settings': settings, 'secret': secret, 'user': user, 'trust': trust,
         'product': product, 'form': form }
    return render(request, tmpl, c)                


@has_profile
@curiousorm.retry_transient_errors
def show_payments(request, secret, user, partner_id_str, promise_id_str, tmpl='xhtml-mp/pending_payments.html', method=None):
    partner_id = int(partner_id_str)
    promise_id = int(promise_id_str)

    method = method or request.GET.get('method') or request.method
    if method == 'POST':
        try:
            payer_id = int(request.POST.get('payer_id', '')[:30])
            order_id = int(request.POST.get('order_id', '')[:30])
            if not (1 <= payer_id <= 999999999 and 1 <= payer_id <= 999999999):
                raise ValueError()
        except ValueError:
            error_code = 100
        else:
            request._cmbarter_trx_cost += 30.0
            error_code = db.accept_payment(user['trader_id'], payer_id, order_id)
            if error_code==0:
                return show_unconfirmed_transactions(
                    request, secret, method='GET',
                    payments=reverse(show_payments, args=[secret, partner_id, promise_id]))
    else:
        error_code = 0

    # Get partner's name.
    trust = db.get_trust(user['trader_id'], partner_id)
    if not trust:
        raise Http404

    # Get product's information.
    product = db.get_product(partner_id, promise_id)
    if not product:
        raise Http404

    # Get pending payments list.
    payments = db.get_pending_payment_list(user['trader_id'], partner_id, promise_id)

    # Render everything.
    c = {'settings': settings, 'secret': secret, 'user': user, 'trust': trust,
         'product': product, 'payments': payments, 'error_code': error_code }
    return render(request, tmpl, c)


@has_profile
@curiousorm.retry_transient_errors
def show_unconfirmed_transactions(request, secret, user, tmpl='xhtml-mp/unconfirmed_transactions.html', method=None, payments=None):
    method = method or request.GET.get('method') or request.method    
    if method == 'POST':
        
        confirmed = 0
        with db.Transaction() as trx:
            for field_name in request.POST:
                tf = TRX_FIELD.match(field_name)
                if tf:
                    trx.confirm_transaction(user['trader_id'], int(tf.group(1)))
                    confirmed += 1
        request._cmbarter_trx_cost += (1.0 + 10.0 * confirmed)
        
        return HttpResponseRedirect(reverse(
            show_shopping_list,
            args=[secret]))

    # Get user's list of unconfirmed transactions.    
    transactions = db.get_unconfirmed_transaction_list(user['trader_id'])
    
    # Render everything.
    c = {'settings': settings, 'user': user, 'secret': secret, 'transactions' : transactions,
         'pending_payments_link': payments }
    return render(request, tmpl, c)


@has_profile
@curiousorm.retry_transient_errors
def show_my_order(request, secret, user, order_id_str, tmpl='xhtml-mp/my_order.html', method=None):
    order_id = int(order_id_str)

    method = method or request.GET.get('method') or request.method    
    if method == 'POST':
        form = cmbarter.orders.forms.RemoveOrderForm(request.POST)
        if form.is_valid():
            if form.cleaned_data['remove']:
                request._cmbarter_trx_cost += 6.0
                execution_ts = db.deactivate_delivery_order(user['trader_id'], order_id)

                if ('pending_payment' in request.POST) and (execution_ts is not None):
                    # The payment order has been executed beneath user's
                    # feet, so we have to report this to him.
                    return report_my_order_unexpected_execution(request, secret, order_id)

            return show_my_order_list(request, secret)
    else:
        form = cmbarter.orders.forms.RemoveOrderForm()

    # Get order info.
    order = db.get_active_delivery_order(user['trader_id'], order_id)

    if order:

        # Render everything.
        c = {'settings': settings, 'secret': secret,
             'user': user, 'order': order, 'form': form }
        return render(request, tmpl, c)        

    # Say that the order has been deleted if it can not be found.
    return report_my_order_deleted(request, secret, order_id)


@has_profile
def show_my_order_list(request, secret, user, tmpl='xhtml-mp/my_orders.html'):
    # Get user's list of active orders.
    orders = db.get_active_delivery_order_list(user['trader_id'])
    
    # Render everything.
    c = {'settings': settings, 'secret': secret, 'user': user, 'orders' : orders }
    return render(request, tmpl, c)    


@has_profile
def report_my_order_deleted(request, secret, user, order_id_str, tmpl='xhtml-mp/my_order_deleted.html'):
    order_id = int(order_id_str)
    
    # Render everything.    
    c = {'settings': settings, 'secret': secret, 'user': user, 'order_id' : order_id }
    return render(request, tmpl, c)    


@has_profile
def report_my_order_unexpected_execution(request, secret, user, order_id_str, tmpl='xhtml-mp/my_order_executed.html'):
    order_id = int(order_id_str)
    
    # Render everything.
    c = {'settings': settings, 'secret': secret, 'user': user, 'order_id' : order_id }
    return render(request, tmpl, c)    


@has_profile
def find_customer(request, secret, user, tmpl='xhtml-mp/find_customer.html', method=None):
    method = method or request.GET.get('method') or request.method    
    if method == 'POST':
        form = cmbarter.deposits.forms.FindCustomerForm(request.POST)
        if form.is_valid():
            request._cmbarter_trx_cost += 1.0
            if db.get_profile(form.cleaned_data['id']):
                return HttpResponseRedirect(reverse(
                    show_deposits,
                    args=[secret, form.cleaned_data['id']]))
            else:
                form.wrong_trader_id = True
    else:
        form = cmbarter.deposits.forms.FindCustomerForm()

    # Render everything.
    c = {'settings': settings, 'secret': secret, 'user': user, 'form': form }
    return render(request, tmpl, c)        


@has_profile
def show_deposits(request, secret, user, customer_id_str, tmpl='xhtml-mp/deposits.html'):
    customer_id = int(customer_id_str)

    # Get customer's profile.
    request._cmbarter_trx_cost += 1.0
    trader = db.get_profile(customer_id)
    
    if trader:
        # Get customer's list of deposits.
        deposits = db.get_deposit_list(customer_id, user['trader_id'])

        # Render everything.
        c = {'settings': settings, 'secret': secret,
             'user': user, 'trader': trader, 'deposits': deposits }
        return render(request, tmpl, c)        
    
    raise Http404


@has_profile
@curiousorm.retry_transient_errors
def make_deposit(request, secret, user, customer_id_str, tmpl='xhtml-mp/make_deposit.html', method=None):
    customer_id = int(customer_id_str)

    method = method or request.GET.get('method') or request.method    
    if method == 'POST':
        form = cmbarter.deposits.forms.MakeDepositForm(request.POST)
        if form.is_valid():
            request._cmbarter_trx_cost += 1.0
            with db.Transaction() as trx:
                if form.cleaned_data['subtract']:
                    # Try to subtract the amount from the issuer's
                    # account first.
                    request._cmbarter_trx_cost += 11.0
                    amount_is_available =  trx.insert_transaction(
                        user['trader_id'],
                        user['trader_id'],
                        form.cleaned_data['promise_id'],
                        (- form.cleaned_data['amount']),
                        form.cleaned_data['reason'],
                        False, None, None, None, None, None)
                else:
                    # This is a pure deposit transaction, so we should
                    # do nothing.
                    amount_is_available = True

                # We do the deposit to the customer's account if the
                # amount is available.
                if amount_is_available:
                    request._cmbarter_trx_cost += 11.0
                    trx.insert_transaction(
                        user['trader_id'],
                        customer_id,
                        form.cleaned_data['promise_id'],
                        form.cleaned_data['amount'],
                        form.cleaned_data['reason'],
                        False, None, None, None, None, None)

            # Here the transaction is committed. We redirect the user
            # to the "committed transaction" page if everything went
            # OK.  Otherwise we report an error.
            if amount_is_available:
                return report_transaction_commit(
                    request, secret, method='GET',
                    backref=request.GET.get('backref', '/mobile/'))
            else:
                form.insufficient_amount = True
    else:
        form = cmbarter.deposits.forms.MakeDepositForm(initial={'subtract': user['trader_id'] != customer_id })

    # Get user's product-offers and fetch them in the form's
    # product-select-box.  If two or more products happen to have the
    # same names, only the most recently created product is shown.
    products = db.get_product_offer_list(user['trader_id'])
    choices = []
    choices_name_index = {}
    for p in products:
        name = '%s [%s]'% (p['title'], p['unit'])
        if name in choices_name_index:
            choices[choices_name_index[name]] = (p['promise_id'], name)
        else:
            choices_name_index[name] = len(choices)
            choices.append( (p['promise_id'], name) )
    
    if len(choices) == 1:
        form.fields['promise_id'].widget.choices = choices
    elif len(choices) > 1:
        form.fields['promise_id'].widget.choices = [('', _('Choose a product...'))] + choices
    else:
        # There are no active product-offers, so we redirect the user to his items for sale.
        return HttpResponseRedirect(reverse(
            show_deposits,
            args=[secret, customer_id]))

    # Get customer's profile.
    request._cmbarter_trx_cost += 1.0
    trader = db.get_profile(customer_id)

    if trader:
        # Render everything.
        c = {'settings': settings, 'secret': secret,
             'user' : user, 'trader': trader, 'form' : form }
        return render(request, tmpl, c)                
    
    raise Http404


@has_profile
@curiousorm.retry_transient_errors
def make_withdrawal(request, secret, user, customer_id_str, promise_id_str, tmpl='xhtml-mp/make_withdrawal.html', method=None):
    customer_id = int(customer_id_str)
    promise_id = int(promise_id_str)

    method = method or request.GET.get('method') or request.method    
    if method == 'POST':
        form = cmbarter.deposits.forms.MakeWithdrawalForm(request.POST)
        if form.is_valid():
            request._cmbarter_trx_cost += 12.0
            if db.insert_transaction(
                  user['trader_id'],
                  customer_id,
                  promise_id,
                  (- form.cleaned_data['amount']),
                  form.cleaned_data['reason'],
                  False, None, None, None, None, None):

                return report_transaction_commit(
                    request, secret, method='GET',
                    backref=request.GET.get('backref', '/mobile/'))
            else:
                form.insufficient_amount = True
    else:
        form = cmbarter.deposits.forms.MakeWithdrawalForm(initial={
            'amount': request.GET.get('amount'),
            'reason': request.GET.get('reason')})

    # Get customer's profile
    request._cmbarter_trx_cost += 1.0
    trader = db.get_profile(customer_id)

    # Get product's information.
    product = db.get_product(user['trader_id'], promise_id)

    if trader and product:
        # Get the maximum withdrawable amount and put it in the form's help-text.
        l = db.get_deposit(customer_id, user['trader_id'], promise_id)
        max_amount = utils.truncate(l['amount'] if l else 0.0, product['epsilon'])
        form.fields['amount'].help_text = _("may not exceed %(amount)s") % {'amount': max_amount }

        # Render everything.
        c = {'settings': settings, 'user' : user, 'secret': secret,
             'trader': trader, 'product': product, 'form' : form, 'max_amount': max_amount }
        return render(request, tmpl, c)        

    return show_unknown_product(request, secret, user['trader_id'])


@has_profile
def show_unknown_product(request, secret, user, issuer_id_str, tmpl='xhtml-mp/unknown_product.html'):
    issuer_id  = int(issuer_id_str) 

    # Render everything.
    c = {'settings': settings, 'secret': secret,
         'user' : user, 'issuer_id': issuer_id }
    return render(request, tmpl, c)    


@has_profile
@curiousorm.retry_transient_errors
def show_unconfirmed_deals(request, secret, user, tmpl='xhtml-mp/unconfirmed_deals.html', method=None):
    method = method or request.GET.get('method') or request.method    
    if method == 'POST':

        confirmed = 0
        with db.Transaction() as trx:        
            for field_name in request.POST:
                df = DEAL_FIELD.match(field_name)
                if df:
                    turn_id, issuer_id, promise_id = [int(x) for x in df.group(1, 2, 3)]
                    trx.confirm_deal(turn_id, user['trader_id'], issuer_id, promise_id)
                    confirmed += 1
        request._cmbarter_trx_cost += (1.0 + 5.0 * confirmed)

        return HttpResponseRedirect(reverse(
            show_shopping_list,            
            args=[secret]))

    # Get user's list of unconfirmed deals.
    deals = db.get_unconfirmed_deal_list(user['trader_id'])

    # Render everything.
    c = {'settings': settings, 'secret': secret, 'user': user, 'deals' : deals }
    return render(request, tmpl, c)      


@has_profile
@curiousorm.retry_transient_errors
def report_transaction_commit(request, secret, user, tmpl='xhtml-mp/unconfirmed_receipt.html', method=None, backref=None):
    method = method or request.GET.get('method') or request.method    
    if method == 'POST':

        # Process all form fields.
        request._cmbarter_trx_cost += 1.0
        with db.Transaction() as trx:
            for field_name in request.POST:
                hof = HANDOFF_FIELD.match(field_name)
                if not hof:
                    continue  # This is not a transaction-field.

                request._cmbarter_trx_cost += 2.0
                trx.confirm_receipt(user['trader_id'], int(hof.group(1)))

        redirect_to = backref or request.GET.get('backref') or reverse(
            show_shopping_list,
            args=[secret])
            
        return HttpResponseRedirect(redirect_to)

    # Get user's profile.
    profile = db.get_profile(user['trader_id'])
    
    # Get user's list of unconfirmed receipts.
    receipts = db.get_unconfirmed_receipt_list(user['trader_id'])

    # Group receipts by customer and product.
    items, index = [], {}
    for row in receipts:
        key = (row['recipient_id'], row['promise_id'])
        if key in index:
            items[index[key]]['amount'] += row['amount']
        else:
            index[key] = len(items)
            items.append({'product': row, 'amount': row['amount'] })
    
    # Render everything.
    c = {'settings': settings, 'secret': secret,
         'user': user, 'profile': profile,
         'receipts': receipts, 'items': items, 'backref': backref }
    return render(request, tmpl, c)        


@has_profile
@curiousorm.retry_transient_errors
def edit_profile(request, secret, user, tmpl='xhtml-mp/edit_contact_information.html', method=None):
    method = method or request.GET.get('method') or request.method    
    if method == 'POST':
        form = cmbarter.profiles.forms.EditProfileForm(request.POST)
        if form.is_valid():
            request._cmbarter_trx_cost += 5.0
            db.update_profile(user['trader_id'],
                form.cleaned_data['full_name'],
                form.cleaned_data['summary'],
                form.cleaned_data['country'],
                form.cleaned_data['postal_code'],
                form.cleaned_data['address'],
                form.cleaned_data['email'],
                form.cleaned_data['phone'],
                form.cleaned_data['fax'],
                form.cleaned_data['www'],
                form.cleaned_data['time_zone'],
                form.cleaned_data['advertise_trusted_partners'])

            return HttpResponseRedirect(reverse(
                show_profile,
                args=[secret, user['trader_id']]))
    else:
        form = cmbarter.profiles.forms.EditProfileForm(
            initial=db.get_profile(user['trader_id']))

    # Fetches all known time zones in the form's time-zone-select-box.
    form.fields['time_zone'].widget.choices = [
        (user['time_zone'], user['time_zone'])]

    # Render everything.
    c = {'settings': settings, 'secret': secret, 'user': user, 'form': form }
    return render(request, tmpl, c)    


@has_profile
def report_trader_not_found(request, secret, user, tmpl='xhtml-mp/trader_not_found.html'):
    # Render everything.
    c = {'settings': settings, 'secret': secret, 'user' : user }
    return render(request, tmpl, c)    


@has_profile
@curiousorm.retry_transient_errors
def logout(request, secret, user, tmpl='xhtml-mp/logout.html', method=None):

    method = method or request.GET.get('method') or request.method    
    if method == 'POST':
        db.delete_loginkey(user['trader_id'])
        return HttpResponseRedirect("%s?method=GET" % reverse('mobile-login'))

    # Render everything.
    c = {'settings': settings, 'secret': secret, 'user': user }
    return render(request, tmpl, c)
