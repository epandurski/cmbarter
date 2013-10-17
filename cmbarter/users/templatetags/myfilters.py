import re, datetime
from django import template
from django.conf import settings
from django.utils import translation
from django.template.defaultfilters import stringfilter
from cmbarter.modules.utils import truncate, get_tzinfo
from cmbarter.modules import captcha
import pytz

register = template.Library()


@register.simple_tag
def deal_value(amount, price):
    return "%.2f" % (amount * float(price))


@register.simple_tag
def show_captcha(error=None):
    return captcha.displayhtml(settings.RECAPTCHA_PUBLIC_KEY, use_ssl=True, error=error)


def truncate_amount(amount, epsilon, negate=False):
    return truncate(-amount if negate else amount, epsilon)

register.simple_tag(truncate_amount)


@register.simple_tag
def truncate_amount_for_url(amount, epsilon, negate=False):
    tamt = truncate(-amount if negate else amount, epsilon)
    return unicode(tamt).replace('+', '')


def truncate_abs_amount(amount, epsilon):
    return truncate(abs(amount), epsilon)

register.simple_tag(truncate_abs_amount)


@register.simple_tag
def bad_price(need_amount, have_amount, epsilon, iprice, rprice):
    amt = need_amount - have_amount
    bad_price = (
        amt < (- epsilon) and not (iprice and rprice and rprice <= iprice) or
        amt > (+ epsilon) and not (iprice and rprice and rprice >= iprice))
    if bad_price:
        return '<span class="noprint">*</span>'
    else:
        return ''


def dealts(ts, time_zone='UTC'):
    tz = get_tzinfo(time_zone)
    mark = _get_bidi_mark()
    loc_ts = ts.astimezone(tz)
    return ''.join((
        mark, loc_ts.strftime('%Y-%m-%d'), ' ',
        loc_ts.strftime('%H:%M:%S'), mark
        ))

register.simple_tag(dealts)


@register.filter
@stringfilter
def traderid(value):
    return value.zfill(9)


@register.filter
@stringfilter
def phonenumber(value):
    return value.replace(' ', '').replace('.', '').replace('(', '').replace(')', '')


@register.filter
def absvalue(value):
    return abs(value)


@register.filter
def kilobytes(value):
    return value // 1024


def _get_bidi_mark():
    if settings.CMBARTER_INSERT_BIDI_MARKS:
        return u'\u200F' if translation.get_language_bidi() else u'\u200E'
    else:
        return ''


@register.simple_tag
def default_direction():
    return 'rtl' if translation.get_language_bidi() else 'ltr'


@register.filter
def product(value):
    mark = _get_bidi_mark()
    return "%s %s[%s]%s" % (value['title'], mark, value['unit'], mark)


@register.filter
def next_turn_local_ts(value):
    return dealts(value['next_turn_start_ts'], value['time_zone'])


@register.filter
def local_now_ts(value):
    return dealts(datetime.datetime.now(pytz.utc), value['time_zone'])


@register.filter
def order_truncate_amount(value):
    return truncate_amount(value['amount'], value['epsilon'])


@register.filter
def transaction_truncate_abs_amount(value):
    return truncate_abs_amount(value['amount'], value['epsilon'])


@register.filter
def partner_deposit_truncate_amount(value):
    return truncate_amount(value['amount'], value['offer']['epsilon'])
