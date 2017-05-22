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
## This file defines some global decorators.
##
from __future__ import with_statement
import re
import datetime
from random import random
try:
    from django.urls import reverse
except:
    from django.core.urlresolvers import reverse
try:
    from django.template.context_processors import csrf
except:
    from django.core.context_processors import csrf
from django.http import HttpResponseRedirect, HttpResponseForbidden, Http404
from django.conf import settings
from django.shortcuts import render_to_response
from django.utils.translation import get_language
from django.views.decorators.csrf import csrf_protect
from functools import wraps
from cmbarter.modules import curiousorm
import pytz


A_TURN_IS_RUNNING = re.compile(r'a turn is running')
YEAR_1900 = datetime.datetime(1900, 1, 1)
SII = datetime.timedelta(minutes=settings.CMBARTER_SESSION_INVALIDATION_MINUTES)
SESSION_TOUCH_INTERVAL = SII // 4


class CmbAppError(Exception):
    pass


def report_transaction_cost(db, trader_id, trx_cost):
    # If there is a transaction cost attached to the
    # request, we must record this fact in the database.
    # We must take care, so that the record-keeping itself
    # does not result in more than 5% performance
    # overhead.
    try:
        if trx_cost >= 20.0:
            with db.Transaction() as trx:
                trx.set_asynchronous_commit()
                trx.report_transaction_cost(trader_id, trx_cost)
        elif trx_cost > 0.0 and random() < 0.05 * trx_cost:
            with db.Transaction() as trx:
                trx.set_asynchronous_commit()
                trx.report_transaction_cost(trader_id, 20.0)
    except curiousorm.PgError, e:
        if getattr(e, 'pgcode', '') not in (curiousorm.SERIALIZATION_FAILURE,
                                            curiousorm.DEADLOCK_DETECTED):
            raise  # transaction serialization errors are being ignored


def logged_in(view):
    """View decorator that ensures the user is correctly logged in."""

    view = csrf_protect(view)

    @wraps(view)
    def fn(request, trader_id_str, *args, **kargs):
        try:
            ts = request.session.get('ts', YEAR_1900)
            now = datetime.datetime.now(pytz.utc)
            trader_id = int(trader_id_str)
            if trader_id == request.session.get('trader_id') and now < ts + SII:
                # Update session's timestamp if necessary.
                if now >= ts + SESSION_TOUCH_INTERVAL:
                    request.session['ts'] = now

                # Render the response with some HTTP-headers added.
                response = view(request, trader_id, *args, **kargs)
                if 'Cache-Control' not in response:
                    response['Cache-Control'] = 'no-cache'
                response['X-Frame-Options'] = 'deny'
                return response
            else:
                return HttpResponseRedirect(reverse('users-login'))
            
        except curiousorm.PgError, e:
            if (getattr(e, 'pgcode', '')==curiousorm.RAISE_EXCEPTION and 
                    A_TURN_IS_RUNNING.search(getattr(e, 'pgerror', ''))):
                # Render "turn is running" page with CSRF protection.
                c = {'settings': settings, 'trader_id': trader_id }
                c.update(csrf(request))
                return render_to_response(settings.CMBARTER_TURN_IS_RUNNING_TEMPLATE, c)
            else:
                raise
            
    return fn


def has_profile(db):
    """View decorator that ensures the user has entered a profile."""

    def decorator(view):
        @wraps(view)
        @logged_in
        def fn(request, trader_id, *args, **kargs):
            userinfo = db.get_userinfo(trader_id, get_language())
            if not userinfo:
                return HttpResponseRedirect(reverse('users-login'))
            elif not userinfo['has_profile']:
                return HttpResponseRedirect(reverse('users-profile', args=[trader_id]))
            elif (userinfo['banned_until_ts'] > datetime.datetime.now(pytz.utc)
                  or userinfo['accumulated_transaction_cost'] > settings.CMBARTER_TRX_COST_QUOTA):
                return HttpResponseForbidden()
            else:
                if not hasattr(request, '_cmbarter_trx_cost'):
                    request._cmbarter_trx_cost = 0.0
                try:
                    # The next call may affect request._cmbarter_trx_cost
                    response = view(request, userinfo, *args, **kargs)
                except (Http404, CmbAppError):
                    report_transaction_cost(db, trader_id, request._cmbarter_trx_cost)
                    request._cmbarter_trx_cost = 0.0
                    raise
                else:
                    report_transaction_cost(db, trader_id, request._cmbarter_trx_cost)
                    request._cmbarter_trx_cost = 0.0
                    return response
                            
        return fn
    
    return decorator


def max_age(sec):
    """View decorator that sets the cahce-control header."""

    def decorator(view):
        @wraps(view)
        def fn(request, *args, **kargs):
            response = view(request, *args, **kargs)
            if 200==response.status_code:
                response['Cache-Control'] = "max-age=%i, public" % sec
            return response
        return fn
    
    return decorator
