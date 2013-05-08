# -*- coding: utf-8 -*-

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
## This file contains code implementing miscellaneous
## utility-functions.
##

import os, gettext, re, datetime
import smtplib
import fcntl
import email.utils
from email.mime.text import MIMEText
from email.header import Header
from decimal import Decimal
from math import log10, floor
from StringIO import StringIO
import string, random, hashlib, base64, pytz
from cmbarter.modules import curiousorm



_PASSWORD_SALT_CHARS = string.digits + string.letters + string.punctuation



_deps_cache = {}

def _calc_deps(f):
    global _deps_cache

    if f not in _deps_cache:
        i = int(f)
        if 0 < i:
            i = 3*(i // 3)
        deps = Decimal((0, (1,), i))  # Equals 10**i and carries no significant digits.
        _deps_cache[f] = (deps, float(deps))

    return _deps_cache[f]



def truncate(amount, epsilon):
    deps, feps = _calc_deps(floor(log10(epsilon)))
    tamt = int(amount / feps) * deps
    return tamt.to_eng_string() if tamt else '0'



def get_tzinfo(tz_name):
    try:
        tz = pytz.timezone(tz_name)
    except pytz.UnknownTimeZoneError:
        tz = pytz.utc
    return tz



def generate_password_salt():
    salt = ''
    while len(salt) < 16:
        salt += random.choice(_PASSWORD_SALT_CHARS)
    return salt
    


def calc_crypt_hash(message):
    sha = hashlib.sha256()
    sha.update(message.encode('utf-8'))
    return base64.urlsafe_b64encode(sha.digest())



#######################################################
# Constants used by Verhoeff's check-digit functions
#######################################################

_F = [ [ 0, 1, 2, 3, 4, 5, 6, 7, 8, 9], [ 1, 5, 7, 6, 2, 8, 3, 0, 9, 4 ] ]

for i in range(2, 8):
    _F.append(10 * [None])
    for j in range(10):
        _F[ i ][ j ] = _F[ i - 1 ][ _F[ 1 ][ j ]]
        
_OP = [ [ 0, 1, 2, 3, 4, 5, 6, 7, 8, 9 ],
        [ 1, 2, 3, 4, 0, 6, 7, 8, 9, 5 ],
	[ 2, 3, 4, 0, 1, 7, 8, 9, 5, 6 ],
	[ 3, 4, 0, 1, 2, 8, 9, 5, 6, 7 ],
	[ 4, 0, 1, 2, 3, 9, 5, 6, 7, 8 ],
	[ 5, 9, 8, 7, 6, 0, 4, 3, 2, 1 ],
	[ 6, 5, 9, 8, 7, 1, 0, 4, 3, 2 ],
	[ 7, 6, 5, 9, 8, 2, 1, 0, 4, 3 ],
	[ 8, 7, 6, 5, 9, 3, 2, 1, 0, 4 ],
	[ 9, 8, 7, 6, 5, 4, 3, 2, 1, 0 ] ]

_INV = [ 0, 4, 3, 2, 1, 5, 6, 7, 8, 9 ]



def vh_check(num):
    """Perform Verhoeff's check-digit validation."""
    a = [int(x) for x in unicode(num).rjust(8, '0')]
    a.reverse()
    check = 0
    for i in range(len(a)):
        check = _OP[ check ][ _F[ i % 8 ][ a[i] ] ]
    return (check == 0)



def vh_compute(num):
    """Append a Verhoeff's check-digit to a given number."""
    a = [int(x) for x in unicode(num).rjust(7, '0')] + ['x']
    a.reverse()
    check = 0
    for i in range(1, len(a)):
        check = _OP[ check ][ _F[ i % 8 ][ a[i] ] ];
    return 10 * num + _INV[ check ]



#######################################################
# Utility functions for sending email.
#######################################################

_CTRL_CHARS = re.compile(r'[\001-\037\177]')  # These are all control characters
_SPECIALS = re.compile(r'[][\\()<>@,:;".]')
_WEEKDAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]



def _formataddr(mailbox, display_name=None, header_name=None):
    header = Header(header_name=header_name)
    if display_name:
        display_name_no_control_chars = remove_control_chars(display_name)
        header.append(display_name_no_control_chars)
        if _SPECIALS.search(str(header)):
            header = Header(header_name=header_name)
            header.append('"%s"' % email.utils.quote(display_name_no_control_chars))
        header.append("<%s>" % encode_domain_as_idna(mailbox))
    else:
        header.append(encode_domain_as_idna(mailbox))
    return header



def _formatdate(date):
    return "%s, %s" % (_WEEKDAY_NAMES[date.weekday()], date.strftime("%d %b %Y %H:%M:%S %z"))



def encode_domain_as_idna(s):
    if s and u'@' in s:
        parts = s.split(u'@')
        try:
            parts[-1] = parts[-1].encode('idna')
        except UnicodeError:
            pass
        return u'@'.join(parts)
    else:
        return s



def remove_control_chars(s):
    return re.sub(_CTRL_CHARS, ' ', s)



def compose_email(to_mailbox, from_mailbox, subject, content,
                 to_display_name = None, from_display_name = None,
                 reply_to_mailbox = None, reply_to_display_name = None,
                 sender_mailbox = None, sender_display_name = None,
                 id = None, orig_date = None, **kw):
    
    # Constructs the email and adds the content
    msg = MIMEText(content.encode('utf-8'), _charset='utf-8')

    # Add mandatory headers
    msg['Message-Id'] = email.utils.make_msgid(str(id)) if id else email.utils.make_msgid()
    msg['Date'] = _formatdate(orig_date if orig_date else datetime.datetime.now(pytz.utc))
    msg['To'] = _formataddr(to_mailbox, to_display_name, header_name="To")
    msg['From'] = _formataddr(from_mailbox, from_display_name, header_name="From")

    subject_header = Header(header_name="Subject")
    subject_header.append(remove_control_chars(subject))
    msg['Subject'] = subject_header

    # Add "Reply-To" if given
    if reply_to_mailbox:
        msg['Reply-To'] = _formataddr(reply_to_mailbox, reply_to_display_name, header_name="Reply-To")

    # Add "Sender" if given
    if sender_mailbox:
        msg['Sender'] = _formataddr(sender_mailbox, sender_display_name, header_name="Sender")

    return msg



def send_email(connection, email_dict):
    sender = email_dict['sender_mailbox']
    
    from_ = encode_domain_as_idna(sender) if sender else encode_domain_as_idna(email_dict['from_mailbox'])
    to_ = encode_domain_as_idna(email_dict['to_mailbox'])
    msg = compose_email(**email_dict)

    connection.sendmail(from_, [to_], msg.as_string())



def get_ugettext(lang):
    """Returns a 'ugettext' function for a given language code. """
    
    localedir = os.path.join(os.path.dirname(__file__), '../locale')
    translation = gettext.translation('django', localedir, [lang], fallback=True)
    return translation.ugettext



def wrap_line(s, width):
    assert 0 < width < 998
    lines = []

    while len(s) > width:
        max_len = min(998, len(s))  # we must never have a line longer than this
        
        # find position of nearest whitespace char, preferably to the
        # left of "width"
        marker, step = width, -1
        while not s[marker].isspace():
            marker += step
            if marker == 0:
                marker, step = width + 1, 1
            if marker == max_len:
                break

        # remove that part from original string and add it to the list
        # of lines -- skipping all trailing spaces
        lines.append(s[0:marker])
        while marker < len(s) and s[marker].isspace():
            marker += 1
        s = s[marker:]

    if s:
        lines.append(s)

    return '\n'.join(lines)



def wrap_text(s, width=72):
    s = re.sub(r'\r\n|\r|\n', '\n', s)  # normalize newlines
    lines = [wrap_line(l, width) for l in s.split('\n')]
    return '\n'.join(lines)



############################################################
# Utility functions for buffered database reading/writing.
############################################################

BUFFER_SIZE = 10000



def buffered_cursor_iter(dsn, query, query_params=[], buffer_size=BUFFER_SIZE):
    o = curiousorm.connect(dsn)
    try:
        c = curiousorm.create_server_side_cursor(o)
        c.arraysize = buffer_size
        c.execute(query, query_params)
        while True:
            rows = c.fetchmany(buffer_size)
            if rows:
                for row in rows:
                    yield row
            else:
                break
        c.close()

    finally:
        o.close()
