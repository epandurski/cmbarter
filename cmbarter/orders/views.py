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
## related to user's delivery orders.
##
import re
from decimal import Decimal
from django.conf import settings
from django.shortcuts import render_to_response
from django.core.urlresolvers import reverse
try:
    from django.template.context_processors import csrf
except:
    from django.core.context_processors import csrf
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseNotAllowed, Http404
from cmbarter.users.decorators import has_profile
from cmbarter.orders import forms
from cmbarter.modules import curiousorm, utils


db = curiousorm.Database(settings.CMBARTER_DSN, dictrows=True)


@has_profile(db)
@curiousorm.retry_on_deadlock
def create_order(request, user, partner_id_str, promise_id_str, tmpl='create_order.html'):
    partner_id = int(partner_id_str)
    promise_id = int(promise_id_str)
    
    if request.method == 'POST':
        form = forms.CreateOrderForm(request.POST)
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
                return HttpResponseRedirect(reverse(
                    show_my_order,
                    args=[user['trader_id'], order_id]))
            else:
                form.avl_amount = db.get_deposit_avl_amount(user['trader_id'], partner_id, 
                                                            promise_id)
                form.show_avl_amount = form.avl_amount < form.cleaned_data['amount']
                form.insufficient_amount = True
    else:
        form = forms.CreateOrderForm()

    # Get partner's name.
    trust = db.get_trust(user['trader_id'], partner_id)
    if not trust:
        raise Http404

    # Get product's information.
    product = db.get_product(partner_id, promise_id)
    if not product:
        raise Http404

    # Get user's list of partners.
    partners = db.get_trust_list(user['trader_id'])

    # Truncate form.avl_amount
    if hasattr(form, 'avl_amount'):
        form.avl_amount = utils.truncate(form.avl_amount, product['epsilon'])

    # Render everything adding CSRF protection.        
    c = {'settings': settings, 'user': user, 'trust': trust, 'product': product, 
         'partners': partners, 'form': form }
    c.update(csrf(request))
    return render_to_response(tmpl, c)


@has_profile(db)
def show_my_order_list(request, user, tmpl='my_orders.html'):
    # Get user's list of active orders.
    orders = db.get_active_delivery_order_list(user['trader_id'])
    
    # Render everything adding CSRF protection.    
    c = {'settings': settings, 'user': user, 'orders' : orders }
    c.update(csrf(request))
    return render_to_response(tmpl, c)


@has_profile(db)
@curiousorm.retry_on_deadlock
def show_my_order(request, user, order_id_str, tmpl='my_order.html'):
    order_id = int(order_id_str)

    if request.method == 'POST':
        form = forms.RemoveOrderForm(request.POST)
        if form.is_valid():
            if form.cleaned_data['remove']:
                request._cmbarter_trx_cost += 6.0
                execution_ts = db.deactivate_delivery_order(user['trader_id'], order_id)

                if ('pending_payment' in request.POST) and (execution_ts is not None):
                    # The payment order has been executed beneath user's
                    # feet, so we have to report this to him.
                    return HttpResponseRedirect(reverse(
                        report_my_order_unexpected_execution,
                        args=[user['trader_id'], order_id]))

            return HttpResponseRedirect(reverse(
                show_my_order_list,
                args=[user['trader_id']]))
    else:
        form = forms.RemoveOrderForm()

    # Get order info.
    order = db.get_active_delivery_order(user['trader_id'], order_id)

    if order:

        # Render everything adding CSRF protection.        
        c = {'settings': settings, 'user': user, 'order': order, 'form': form }
        c.update(csrf(request))
        return render_to_response(tmpl, c)

    # Say that the order has been deleted if it can not be found.
    return HttpResponseRedirect(reverse(
        report_my_order_deleted,
        args=[user['trader_id'], order_id]))


@has_profile(db)
def report_my_order_deleted(request, user, order_id_str, tmpl='my_order_deleted.html'):
    order_id = int(order_id_str)
    
    # Render everything adding CSRF protection.    
    c = {'settings': settings, 'user': user, 'order_id' : order_id }
    c.update(csrf(request))
    return render_to_response(tmpl, c)


@has_profile(db)
def report_my_order_unexpected_execution(request, user, order_id_str, 
                                         tmpl='my_order_executed.html'):
    order_id = int(order_id_str)
    
    # Render everything adding CSRF protection.    
    c = {'settings': settings, 'user': user, 'order_id' : order_id }
    c.update(csrf(request))
    return render_to_response(tmpl, c)


@has_profile(db)
def show_customer_order_list(request, user, customer_id_str, tmpl='customer_orders.html'):
    customer_id = int(customer_id_str)

    # Get customer's profile.
    request._cmbarter_trx_cost += 1.0
    trader = db.get_profile(customer_id)
    
    if trader:
        # Get customer's list of orders.
        orders = db.get_customer_delivery_order_list(user['trader_id'], customer_id)

        # Render everything adding CSRF protection.        
        c = {'settings': settings, 'user': user, 'trader': trader, 'orders': orders }
        c.update(csrf(request))
        return render_to_response(tmpl, c)
    
    raise Http404


@has_profile(db)
@curiousorm.retry_on_deadlock
def review_customer_order(request, user, customer_id_str, order_id_str, 
                          tmpl='customer_order.html'):
    customer_id = int(customer_id_str)
    order_id = int(order_id_str)

    if request.method == 'POST':
        form = forms.CompleteOrderForm(request.POST)
        if form.is_valid():
            if form.cleaned_data['complete']:
                request._cmbarter_trx_cost += 6.0
                db.execute_delivery_order(user['trader_id'], customer_id, order_id, '')

            return HttpResponseRedirect(reverse(
                show_customer_order_list,
                args=[user['trader_id'], customer_id]))
    else:
        form = forms.CompleteOrderForm()

    # Get customer's profile.
    request._cmbarter_trx_cost += 1.0
    trader = db.get_profile(customer_id)

    if trader:
        # Get order info.
        order = db.review_customer_delivery_order(user['trader_id'], customer_id, order_id)

        if order:
            # Render everything adding CSRF protection.        
            c = {'settings': settings, 'user': user, 'trader': trader, 'order': order, 
                 'form': form }
            c.update(csrf(request))
            return render_to_response(tmpl, c)

        else:
            return HttpResponseRedirect(reverse(
                show_customer_order_list,
                args=[user['trader_id'], customer_id]))

    raise Http404


@has_profile(db)
@curiousorm.retry_on_deadlock
def show_payments(request, user, partner_id_str, promise_id_str, tmpl='pending_payments.html'):
    partner_id = int(partner_id_str)
    promise_id = int(promise_id_str)

    if request.method == 'POST':
        try:
            payer_id = int(request.POST.get('payer_id', u'')[:30])
            order_id = int(request.POST.get('order_id', u'')[:30])
            if not (1 <= payer_id <= 999999999 and 1 <= payer_id <= 999999999):
                raise ValueError()
        except ValueError:
            error_code = 100
        else:
            request._cmbarter_trx_cost += 30.0
            error_code = db.accept_payment(user['trader_id'], payer_id, order_id)
            if error_code==0:
                return HttpResponseRedirect("%s?payments=%s" % (
                    reverse('deposits-unconfirmed-transactions', args=[user['trader_id']]),
                    reverse(show_payments, args=[user['trader_id'], partner_id, promise_id]) ))
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

    # Render everything adding CSRF protection.        
    c = {'settings': settings, 'user': user, 'trust': trust,
         'product': product, 'payments': payments, 'error_code': error_code }
    c.update(csrf(request))
    return render_to_response(tmpl, c)
