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
## related to viewing user's deals.
##
from __future__ import with_statement
import decimal, re, datetime
from django.conf import settings
from django.shortcuts import render_to_response
from django.core.urlresolvers import reverse
from django.core.context_processors import csrf
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseNotAllowed, Http404
from cmbarter.users.decorators import has_profile
from cmbarter.modules import curiousorm, utils
import pytz


db = curiousorm.Database(settings.CMBARTER_DSN, dictrows=True)

HISTORY_HORIZON = datetime.timedelta(days=settings.CMBARTER_HISTORY_HORISON_DAYS)
DEAL_FIELD = re.compile(r'^deal-([0-9]{1,9})-([0-9]{1,9})-([0-9]{1,9})$')


def _nearest_midnights(year, month, day, timezone=pytz.utc):
    base_date = datetime.date(year, month, day)
    for i in (-1, 0, 1):
        date = base_date + datetime.timedelta(days=i)
        yield timezone.localize(datetime.datetime(date.year, date.month, date.day))
         
        

@has_profile(db)
@curiousorm.retry_on_deadlock
def show_unconfirmed_deals(request, user, tmpl='unconfirmed_deals.html'):
    if request.method == 'POST':

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
            report_deals_confirmation,            
            args=[user['trader_id'], confirmed]))

    # Get user's list of unconfirmed deals.
    deals = db.get_unconfirmed_deal_list(user['trader_id'])

    # Render everything adding CSRF protection.
    c = {'settings': settings, 'user': user, 'deals' : deals }
    c.update(csrf(request))
    return render_to_response(tmpl, c)        


@has_profile(db)
def report_deals_confirmation(request, user, count_str, tmpl='deals_confirmation.html'):

    # Render everything adding CSRF protection.            
    c = {'settings': settings, 'user': user, 'count': int(count_str) }
    c.update(csrf(request))
    return render_to_response(tmpl, c)


@has_profile(db)
def show_customer_deals(request, user, year, month, day, tmpl='customer_deals.html'):
    prev_date, date, next_date = _nearest_midnights(
        int(year), int(month), int(day),
        timezone=utils.get_tzinfo(user['time_zone']))

    now = datetime.datetime.now(pytz.utc)
    
    if date > now - HISTORY_HORIZON:
        # Get user's customer deals for the given period of time.
        deals = db.get_customer_recent_deal_list(user['trader_id'], date, next_date)
    else:
        # This day is outside our history horizon.
        deals = None

    # Render everything adding CSRF protection.
    c = { 'settings': settings, 'user': user, 'prev_date': prev_date, 'date': date,
          'next_date': next_date if next_date <= now else None,
          'deals': deals }
    c.update(csrf(request))
    return render_to_response(tmpl, c)


@has_profile(db)
def show_todays_customer_deals(request, user):

    # Get current timestamp in user's time zone.    
    tz = utils.get_tzinfo(user['time_zone'])    
    today = datetime.datetime.now(tz)

    return HttpResponseRedirect(reverse(
        show_customer_deals,
        args=[user['trader_id'], today.year, today.month, today.day]))


@has_profile(db)
def show_my_deals(request, user, year, month, day, tmpl='my_deals.html'):
    prev_date, date, next_date = _nearest_midnights(
        int(year), int(month), int(day),
        timezone=utils.get_tzinfo(user['time_zone']))

    now = datetime.datetime.now(pytz.utc)
    
    if date > now - HISTORY_HORIZON:
        # Get user's own deals for the given period of time.
        deals = db.get_recent_deal_list(user['trader_id'], date, next_date)
    else:
        # This day is outside our history horizon.
        deals = None

    # Render everything adding CSRF protection.
    c = { 'settings': settings, 'user': user, 'prev_date': prev_date, 'date': date,
          'next_date': next_date if next_date <= now else None,
          'deals': deals }
    c.update(csrf(request))
    return render_to_response(tmpl, c)


@has_profile(db)
def show_my_todays_deals(request, user):

    # Get current timestamp in user's time zone.    
    tz = utils.get_tzinfo(user['time_zone'])    
    today = datetime.datetime.now(tz)

    return HttpResponseRedirect(reverse(
        show_my_deals,
        args=[user['trader_id'], today.year, today.month, today.day]))
