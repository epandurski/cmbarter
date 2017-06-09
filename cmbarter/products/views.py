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
## This file contains django view-functions implementing functionality
## related to user's pricelist and user's shopping list.
##
from __future__ import with_statement
import re, decimal, urllib
from django.conf import settings
from django.shortcuts import render_to_response
try:
    from django.urls import reverse
except:
    from django.core.urlresolvers import reverse
try:
    from django.template.context_processors import csrf
except:
    from django.core.context_processors import csrf
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseNotAllowed, Http404
from cmbarter.users.decorators import has_profile
from cmbarter.products import forms
from cmbarter.modules import curiousorm, utils


db = curiousorm.Database(settings.CMBARTER_DSN, dictrows=True)

PRICE_FIELD_NAME = re.compile(r'^price-([0-9]{1,9})$')
MIN_PRICE = decimal.Decimal('0.01')
MAX_PRICE = decimal.Decimal('9999999999999.99')
HAVE_FIELD_NAME = re.compile(r'^have-([0-9]{1,9}-[0-9]{1,9})$')


_parse_monetary_value = re.compile(r"""
    \A\s*
    (?P<prefix>[^\s\d.+-]+)?                            # optional monetary prefix
    \s*
    (?P<value>[-+]?(?=\d|\.\d)\d*(\.\d*)?(E[-+]?\d+)?)  # a floating point number
    \s*
    (?P<suffix>\S+)?                                    # optional monetary suffix
    \s*\Z
""", re.VERBOSE | re.IGNORECASE | re.UNICODE).match


def _parse_float(float_str, default=None, error_log=None):
    if error_log is None:
        error_log = []
    try:
        result = float(float_str)
        if result!=result or abs(result) > 1e32:
            error_log.append(float_str)
            result = default
    except ValueError:
        error_log.append(float_str)
        result = default
    return result


def _parse_price(decimal_str, default=None, error_log=None):
    if error_log is None:
        error_log = []
    if len(decimal_str) > 25:
        error_log.append(decimal_str)  # too long
    elif len(decimal_str) > 0 and not decimal_str.isspace():
        m = _parse_monetary_value(decimal_str)
        if m is None:
            error_log.append(decimal_str)  # wrong format
        else:
            prefix = m.group('prefix') or ''
            suffix = m.group('suffix') or ''
            if prefix and suffix:
                error_log.append(decimal_str)  # has both prefix and suffix
            elif prefix.upper() not in settings.CMBARTER_PRICE_PREFIXES:
                error_log.append(decimal_str)  # invalid prefix
            elif suffix.upper() not in settings.CMBARTER_PRICE_SUFFIXES:
                error_log.append(decimal_str)  # invalid suffix
            else:
                try:
                    result = decimal.Decimal(m.group('value'))
                except decimal.InvalidOperation:
                    result = decimal.Decimal(0)  # the value must have been out of range
                if MIN_PRICE <= result <= MAX_PRICE:
                    return result
                else:            
                    error_log.append(decimal_str)  # out of range
    return default


@has_profile(db)
@curiousorm.retry_on_deadlock
def create_product(request, user, tmpl='create_product.html'):
    if request.method == 'POST':
        form = forms.CreateProductForm(request.POST)
        if form.is_valid():
            request._cmbarter_trx_cost += 4.0
            db.insert_product_offer(
                user['trader_id'],
                form.cleaned_data['title'],
                form.cleaned_data['summary'],
                form.cleaned_data['description'],
                form.cleaned_data['unit'],
                form.cleaned_data['epsilon'])
            
            return HttpResponseRedirect(reverse(
                report_create_product_success,
                args=[user['trader_id']]))
    else:
        form = forms.CreateProductForm()

    # Render everything adding CSRF protection.        
    c = {'settings': settings, 'user': user, 'form': form }
    c.update(csrf(request))
    return render_to_response(tmpl, c)        


@has_profile(db)
def report_create_product_success(request, user, tmpl='create_product_success.html'):

    # Render everything adding CSRF protection.            
    c = {'settings': settings, 'user': user }
    c.update(csrf(request))
    return render_to_response(tmpl, c)


@has_profile(db)
@curiousorm.retry_on_deadlock
def update_pricelist(request, user, tmpl='pricelist.html'):
    if request.method == 'POST':

        # Process all form fields.
        errors = []
        request._cmbarter_trx_cost += 1.0
        with db.Transaction() as trx:
            for field_name in request.POST:
                pfn = PRICE_FIELD_NAME.match(field_name)
                if not pfn:
                    continue  # This is not a price-field.
                if request.POST[field_name] == request.POST.get("old-%s" % field_name):
                    continue  # The price has not been changed.

                promise_id = int(pfn.group(1))
                price = _parse_price(request.POST[field_name], error_log=errors)
                if request._cmbarter_trx_cost > 500.0:
                    # This seems to be a DoS attempt, so we stop here.
                    break
                else:
                    request._cmbarter_trx_cost += 1.0
                    trx.update_product_offer(user['trader_id'], promise_id, price)
        
        return HttpResponseRedirect(reverse(
            report_update_pricelist_success,
            args=[user['trader_id'], len(errors)]))

    # Get user's list of offered products.
    offers = db.get_product_offer_list(user['trader_id'])
    offers.sort(key=lambda row: (row['title'].lower(), row['unit'].lower(), row['promise_id']))

    # Render everything adding CSRF protection.            
    c = {'settings': settings, 'user': user, 'offers' : offers }
    c.update(csrf(request))
    return render_to_response(tmpl, c)        


@has_profile(db)
def report_update_pricelist_success(request, user, errors, tmpl='pricelist_success.html'):

    # Render everything adding CSRF protection.    
    c = {'settings': settings, 'user': user, 'errors': int(errors) }
    c.update(csrf(request))
    return render_to_response(tmpl, c)        


@has_profile(db)
def show_partner_pricelist(request, user, partner_id_str, tmpl='partner_pricelist.html'):
    partner_id = int(partner_id_str)

    # Make sure this is really a user's partner.
    trust = db.get_trust(user['trader_id'], partner_id)
    
    if trust:
        # Get user's deposited amounts.
        deposits = {}
        for row in db.get_deposit_list(user['trader_id'], partner_id):
            deposits[row['promise_id']] = row['amount']

        # Get the set of products that are included in user's shopping-list.
        chosen_products = set()
        for row in db.get_shopping_item_list(user['trader_id'], partner_id):
            chosen_products.add(row['promise_id'])
            
        # Get partners's pricelist.
        products = []
        offers = db.get_product_offer_list(partner_id)
        offers.sort(key=lambda row: (row['title'].lower(), row['unit'].lower(), row['promise_id']))
        for o in offers:
            promise_id = o['promise_id']
            p = { 'offer': o,
                  'amount': deposits.get(promise_id, 0.0),
                  'is_chosen': promise_id in chosen_products }
            products.append(p)

        # Render everything adding CSRF protection.            
        c = {'settings': settings, 'user': user, 'trust': trust, 'products': products }
        c.update(csrf(request))
        return render_to_response(tmpl, c)        

    return HttpResponseRedirect(reverse(
        'profiles-trader',
        args=[user['trader_id'], partner_id]))


@has_profile(db)
def show_product(request, user, issuer_id_str, promise_id_str, tmpl='product.html'):
    issuer_id  = int(issuer_id_str) 
    promise_id = int(promise_id_str)
    
    # Get product's description.
    request._cmbarter_trx_cost += 1.0
    product = db.get_product(issuer_id, promise_id)
    
    if product:
        if user['trader_id'] == issuer_id:
            trust = None
            owners = db.get_product_deposit_list(user['trader_id'], promise_id)
            allow_removal_from_pricelist = not owners and db.get_product_offer(issuer_id, 
                                                                               promise_id)
            allow_addition_to_shopping_list = False
        else:
            trust = db.get_trust(user['trader_id'], issuer_id)
            owners = []
            allow_removal_from_pricelist = False
            allow_addition_to_shopping_list = (
                bool(trust) and
                not db.get_shopping_item(user['trader_id'], issuer_id, promise_id))

        # Render everything adding CSRF protection.        
        c = {'settings': settings, 'user' : user, 'product': product, 'trust': trust, 
             'owners': owners, 'allow_removal_from_pricelist' : allow_removal_from_pricelist,
             'allow_addition_to_shopping_list': allow_addition_to_shopping_list,
             'actionref': request.GET.get('actionref', u''),
             'backref': request.GET.get('backref', u'') }
        c.update(csrf(request))
        return render_to_response(tmpl, c)        

    else:
        return HttpResponseRedirect(reverse(
            show_unknown_product,
            args=[user['trader_id'], issuer_id]))


@has_profile(db)
def show_unknown_product(request, user, issuer_id_str, tmpl='unknown_product.html'):
    issuer_id  = int(issuer_id_str) 

    # Render everything adding CSRF protection.
    c = {'settings': settings, 'user' : user, 'issuer_id': issuer_id }
    c.update(csrf(request))
    return render_to_response(tmpl, c)


@has_profile(db)
@curiousorm.retry_on_deadlock
def add_shopping_list_item(request, user, issuer_id_str, promise_id_str):
    issuer_id  = int(issuer_id_str) 
    promise_id = int(promise_id_str)
    
    if request.method == 'POST':
        if 'add' in request.POST:
            request._cmbarter_trx_cost += 8.0
            db.insert_shopping_item(user['trader_id'], issuer_id, promise_id)

            actionref = urllib.quote(request.GET.get('actionref', u''))
            redirect_to = actionref or reverse(
                update_shopping_list,
                args=[user['trader_id']])
        else:
            backref = urllib.quote(request.GET.get('backref', u''))
            redirect_to = backref or reverse(
                show_partner_pricelist,
                args=[user['trader_id'], issuer_id])
        
        return HttpResponseRedirect(redirect_to)


    return HttpResponseNotAllowed(['POST'])


@has_profile(db)
@curiousorm.retry_on_deadlock
def remove_pricelist_item(request, user, promise_id_str):
    promise_id = int(promise_id_str)
    
    if request.method == 'POST':
        if 'remove' in request.POST:
            request._cmbarter_trx_cost += 4.0
            db.delete_product_offer(user['trader_id'], promise_id)

            actionref = urllib.quote(request.GET.get('actionref', u''))
            redirect_to = actionref or reverse(
                update_pricelist,
                args=[user['trader_id']])
        else:
            backref = urllib.quote(request.GET.get('backref', u''))
            redirect_to = backref or reverse(
                update_pricelist,
                args=[user['trader_id']])
        
        return HttpResponseRedirect(redirect_to)

    return HttpResponseNotAllowed(['POST'])


@has_profile(db)
@curiousorm.retry_on_deadlock
def update_shopping_list(request, user, tmpl='shopping_list.html'):
    if request.method == 'POST':

        # Process all form fields.
        errors = []
        request._cmbarter_trx_cost += 1.0
        with db.Transaction() as trx:
            for field_name in request.POST:
                hfn = HAVE_FIELD_NAME.match(field_name)
                if not hfn:
                    continue
                suffix = hfn.group(1)
                need_str = request.POST.get("need-" + suffix, u'')
                price_str = request.POST.get("price-" + suffix, u'')
                if ( need_str==request.POST.get("old-need-" + suffix, u'') and
                     price_str==request.POST.get("old-price-" + suffix, u'' ) ):
                    continue
                issuer_id, promise_id = [int(x) for x in suffix.split('-')]
                have_amount = _parse_float(request.POST[field_name])
                if have_amount is None:
                    continue

                need_amount = _parse_float(need_str, have_amount, error_log=errors)

                if request._cmbarter_trx_cost > 500.0:
                    # This seems to be a DoS attempt, so we stop here.
                    break
                elif price_str.strip() in ('REMOVE', 'remove', 'Remove'):
                    request._cmbarter_trx_cost += 2.0
                    trx.delete_shopping_item(user['trader_id'], issuer_id, promise_id)
                else:
                    recipient_price = _parse_price(price_str, error_log=errors)
                    request._cmbarter_trx_cost += 1.0
                    trx.update_shopping_item(
                        user['trader_id'], issuer_id, promise_id,
                        need_amount, recipient_price)
        
        return HttpResponseRedirect(reverse(
            report_update_shopping_list_success,
            args=[user['trader_id'], len(errors)]))

    # Get user's shopping list.
    items = db.get_shopping_item_list(user['trader_id'])
    items.sort(key=lambda row: (
            row['name'].lower(), row['title'].lower(), row['unit'].lower(), row['promise_id']))

    # Render everything adding CSRF protection.            
    c = {'settings': settings, 'user': user, 'items' : items }
    c.update(csrf(request))
    return render_to_response(tmpl, c)        


@has_profile(db)
def report_update_shopping_list_success(request, user, errors, tmpl='shopping_list_success.html'):
    
    # Render everything adding CSRF protection.        
    c = {'settings': settings, 'user': user, 'errors': int(errors) }
    c.update(csrf(request))
    return render_to_response(tmpl, c)        
