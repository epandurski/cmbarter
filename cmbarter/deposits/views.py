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
## related to making deposits and withdrawal.
##
from __future__ import with_statement
import decimal, re
from django.conf import settings
from django.shortcuts import render_to_response
from django.core.urlresolvers import reverse
from django.core.context_processors import csrf
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseNotAllowed, Http404
from django.utils.translation import ugettext_lazy as _
from cmbarter.users.decorators import has_profile
from cmbarter.deposits import forms
from cmbarter.modules import curiousorm, utils


db = curiousorm.Database(settings.CMBARTER_DSN)

TRX_FIELD = re.compile('^trx-(\d{1,15})$')
HANDOFF_FIELD = re.compile('^handoff-(\d{1,9})$')


@has_profile(db)
def find_customer(request, user, tmpl='find_customer.html'):
    if request.method == 'POST':
        form = forms.FindCustomerForm(request.POST)
        if form.is_valid():
            request._cmbarter_trx_cost += 1.0
            if db.get_profile(form.cleaned_data['id']):
                
                return HttpResponseRedirect(reverse(
                    show_deposits,
                    args=[user['trader_id'], form.cleaned_data['id']]))
            else:
                form.wrong_trader_id = True
    else:
        form = forms.FindCustomerForm()

    # Render everything adding CSRF protection.
    c = {'settings': settings, 'user': user, 'form': form }
    c.update(csrf(request))
    return render_to_response(tmpl, c)        


@has_profile(db)
def show_deposits(request, user, customer_id_str, tmpl='deposits.html'):
    customer_id = int(customer_id_str)

    # Get customer's profile.
    request._cmbarter_trx_cost += 1.0
    trader = db.get_profile(customer_id)
    
    if trader:
        # Get customer's list of deposits.
        deposits = db.get_deposit_list(customer_id, user['trader_id'])

        # Render everything adding CSRF protection.        
        c = {'settings': settings, 'user': user, 'trader': trader, 'deposits': deposits }
        c.update(csrf(request))
        return render_to_response(tmpl, c)
    
    raise Http404


@has_profile(db)
@curiousorm.retry_transient_errors
def make_deposit(request, user, customer_id_str, tmpl='make_deposit.html'):
    customer_id = int(customer_id_str)

    if request.method == 'POST':
        form = forms.MakeDepositForm(request.POST)
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
                return HttpResponseRedirect("%s?backref=%s" % (
                    reverse(report_transaction_commit, args=[user['trader_id']]),
                    request.GET.get('backref', '/') ))
            else:
                form.insufficient_amount = True
    else:
        form = forms.MakeDepositForm(initial={'subtract': user['trader_id'] != customer_id })

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
        # There are no active product-offers, so we redirect the user to his pricelist.
        return HttpResponseRedirect(reverse(
            'products-pricelist',
            args=[user['trader_id']]))

    # Get customer's profile.
    request._cmbarter_trx_cost += 1.0
    trader = db.get_profile(customer_id)

    if trader:
        # Render everything adding CSRF protection.    
        c = {'settings': settings, 'user' : user, 'trader': trader, 'form' : form }
        c.update(csrf(request))
        return render_to_response(tmpl, c)
    
    raise Http404


@has_profile(db)
@curiousorm.retry_transient_errors
def make_withdrawal(request, user, customer_id_str, promise_id_str, tmpl='make_withdrawal.html'):
    customer_id = int(customer_id_str)
    promise_id = int(promise_id_str)

    if request.method == 'POST':
        form = forms.MakeWithdrawalForm(request.POST)
        if form.is_valid():
            request._cmbarter_trx_cost += 12.0
            if db.insert_transaction(
                  user['trader_id'],
                  customer_id,
                  promise_id,
                  (- form.cleaned_data['amount']),
                  form.cleaned_data['reason'],
                  False, None, None, None, None, None):

                return HttpResponseRedirect("%s?backref=%s" % (
                    reverse(report_transaction_commit, args=[user['trader_id']]),
                    request.GET.get('backref', '/') ))
            else:
                form.insufficient_amount = True
    else:
        form = forms.MakeWithdrawalForm(initial={
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

        # Render everything adding CSRF protection.            
        c = {'settings': settings, 'user' : user, 'trader': trader, 'product': product, 'form' : form }
        c.update(csrf(request))
        return render_to_response(tmpl, c)        

    return HttpResponseRedirect(reverse(
        'products-unknown-product',
        args=[user['trader_id'], user['trader_id']]))


@has_profile(db)
@curiousorm.retry_transient_errors
def report_transaction_commit(request, user, tmpl='transaction_commit.html'):
    backref = request.GET.get('backref')
    
    if request.method == 'POST':

        # Process all form fields.
        request._cmbarter_trx_cost += 1.0
        with db.Transaction() as trx:
            for field_name in request.POST:
                hof = HANDOFF_FIELD.match(field_name)
                if not hof:
                    continue  # This is not a transaction-field.

                request._cmbarter_trx_cost += 2.0
                trx.confirm_receipt(user['trader_id'], int(hof.group(1)))

        redirect_to = backref or reverse(
            report_receipts_confirmation,
            args=[user['trader_id']])
            
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
    
    # Render everything adding CSRF protection.        
    c = {'settings': settings, 'user': user, 'profile': profile, 'receipts': receipts, 'items': items, 'backref': backref }
    c.update(csrf(request))
    return render_to_response(tmpl, c)


@has_profile(db)
def report_receipts_confirmation(request, user, tmpl='receipt_confirmation.html'):

    # Render everything adding CSRF protection.
    c = {'settings': settings, 'user': user }
    c.update(csrf(request))
    return render_to_response(tmpl, c)


def show_unconfirmed_receipts(request, user, tmpl='unconfirmed_receipt.html'):
    return report_transaction_commit(request, user, tmpl)


@has_profile(db)
@curiousorm.retry_transient_errors
def show_unconfirmed_transactions(request, user, tmpl='unconfirmed_transactions.html'):
    if request.method == 'POST':
        
        confirmed = 0
        with db.Transaction() as trx:
            for field_name in request.POST:
                tf = TRX_FIELD.match(field_name)
                if tf:
                    trx.confirm_transaction(user['trader_id'], int(tf.group(1)))
                    confirmed += 1
        request._cmbarter_trx_cost += (1.0 + 10.0 * confirmed)
        
        return HttpResponseRedirect(reverse(
            report_transactions_confirmation,
            args=[user['trader_id'], confirmed]))

    # Get user's list of unconfirmed transactions.    
    transactions = db.get_unconfirmed_transaction_list(user['trader_id'])
    
    # Render everything adding CSRF protection.
    c = {'settings': settings, 'user': user, 'transactions' : transactions,
         'pending_payments_link': request.GET.get('payments') }
    c.update(csrf(request))
    return render_to_response(tmpl, c)        


@has_profile(db)
def report_transactions_confirmation(request, user, count_str, tmpl='transactions_confirmation.html'):

    # Render everything adding CSRF protection.            
    c = {'settings': settings, 'user': user, 'count': int(count_str) }
    c.update(csrf(request))
    return render_to_response(tmpl, c)


@has_profile(db)
def show_customer_transactions(request, user, customer_id_str, tmpl='customer_transactions.html'):
    customer_id = int(customer_id_str)

    # Get customer's profile.
    request._cmbarter_trx_cost += 1.0
    trader = db.get_profile(customer_id)
    
    if trader:
        # Get customer's list of recent transactions.
        transactions = db.get_recent_nonpayment_transaction_list(customer_id, user['trader_id'])
    
        # Render everything adding CSRF protection.        
        c = {'settings': settings, 'user': user, 'trader': trader, 'transactions': transactions }
        c.update(csrf(request))
        return render_to_response(tmpl, c)
    
    raise Http404


@has_profile(db)
def show_partner_transactions(request, user, partner_id_str, tmpl='partner_transactions.html'):
    partner_id = int(partner_id_str)

    # Make sure this is really a user's partner.
    trust = db.get_trust(user['trader_id'], partner_id)
    
    if trust:
        # Get partners's list of recent transactions.
        transactions = db.get_recent_transaction_list(user['trader_id'], partner_id)

        # Render everything adding CSRF protection.            
        c = {'settings': settings, 'user': user, 'trust': trust, 'transactions': transactions }
        c.update(csrf(request))
        return render_to_response(tmpl, c)        

    raise Http404
