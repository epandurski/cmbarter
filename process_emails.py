#! /usr/bin/env python
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
## This file implements the email processing.
##
from __future__ import with_statement
import sys, os, getopt, base64, datetime, re, time
import smtplib
import pytz
from cmbarter.settings import CMBARTER_HOST, CMBARTER_DSN
from cmbarter.modules import curiousorm
from cmbarter.modules import messages
from cmbarter.modules.utils import send_email, get_ugettext, wrap_text


USAGE = """Usage: process_emails.py [OPTIONS]
Fetches pending messages to the outgoing e-mail server.

  -h, --help                display this help and exit
  --smtp=SMTP_HOST          supply SMTP server name

                            If omitted, the value of the SMTP_HOST
                            environment variable is used. If it is
                            empty "localhost" is presumed.

  --smtp-username=USERNAME  supply SMTP login name (default: no authentication)
  --smtp-password=PASSWORD  supply SMTP password
  --dsn=DSN                 give explicitly the database source name
  --site-domain=DOMANNAME   give explicitly the site's domainname

Example:
  $ ./process_emails.py --smtp=mail.foo.com --smtp-username=cmbarter --smtp-password='mypassword'
"""


deadline = time.time() + 600.0  # The script will exit after 10 minutes at most.



def exit_if_deadline_has_been_passed():
    if time.time() > deadline:
        sys.exit()



def parse_args(argv):
    global site_domain, dsn, smtp_host, smtp_username, smtp_password
    try:                                
        opts, args = getopt.gnu_getopt(argv, 'h', [
                'smtp=', 'smtp-username=','smtp-password=', 
                'site-domain=', 'dsn=', 'help'])
    except getopt.GetoptError:
        print(USAGE)
        sys.exit(2)

    if len(args) != 0:
        print(USAGE)
        sys.exit(2)

    for opt, arg in opts:
        if opt in ('-h', '--help'):
            print(USAGE)
            sys.exit()                  
        elif opt == '--dsn':
            dsn = arg
        elif opt == '--smtp':
            smtp_host = arg
        elif opt == '--smtp-username':
            smtp_username = arg
        elif opt == '--smtp-password':
            smtp_password = arg
        elif opt == '--site-domain':
            site_domain = arg



def process_email_validations(db):
    trader_records = curiousorm.Cursor(dsn, """
        SELECT ev.trader_id, ev.email, ts.last_request_language_code
        FROM email_verification ev, trader_status ts
        WHERE
          ev.email_verification_code IS NULL AND
          ts.trader_id=ev.trader_id AND
          ts.max_email_verification_count> 0
        """, dictrows=True)

    for trader_id, email, lang_code in trader_records:

        exit_if_deadline_has_been_passed()
        
        with db.Transaction() as trx:
            trx.set_asynchronous_commit()
            has_email_verification_rights = trx.acquire_email_verification_rights(trader_id)
            
        if has_email_verification_rights:
            
            # Generate a verification secret.
            email_verification_code = base64.urlsafe_b64encode(os.urandom(15)).decode('ascii')

            # Compose an email message containing the secret.
            _ = get_ugettext(lang_code)
            subject = _(messages.ADDRESS_VERIFICATION_SUBJECT)
            content = _(messages.ADDRESS_VERIFICATION_CONTENT) % {
                "site_domain": site_domain,
                "traderid": str(trader_id).zfill(9),
                "email": email,
                "secret_code": email_verification_code }
            orig_date = datetime.datetime.now(pytz.utc)

            with db.Transaction() as trx:
                trx.set_asynchronous_commit()
                
                if trx.update_email_verification_code(trader_id, email, email_verification_code):
                    
                    # Only when the verification secret is written to
                    # user's profile, we insert the composed message
                    # into the "outgoing_email" table.
                    trx.insert_outgoing_email(
                        subject, wrap_text(content), orig_date,
                        "noreply@%s" % site_domain, site_domain,  # From
                        email, '',  # To
                        '', '', '', '')



def process_outgoing_customer_broadcasts(db):
    broadcasts = curiousorm.Cursor(dsn, """
        SELECT id, trader_id, from_mailbox, subject, content, insertion_ts
        FROM outgoing_customer_broadcast
        """, buffer_size=100, dictrows=True)

    for broadcast_id, issuer_id, issuer_mailbox, subject, content, orig_date in broadcasts:

        exit_if_deadline_has_been_passed()

        with db.Transaction() as trx:
            trx.set_asynchronous_commit()

            # We delete the "outgoing_customer_broadcast" record; then
            # we insert a record in the "outgoing_email" table for
            # each individual recipient of the message.
            if trx.delete_outgoing_customer_broadcast(broadcast_id):
                
                recipients = trx.get_broadcast_recipient_list(issuer_id)

                content = wrap_text(content)  # Transform the message to 72-columns

                for row in recipients:
                    
                     # Compose the email message.
                    _ = get_ugettext(row['last_request_language_code'])
                    signature = _(messages.CUSTOMER_BROADCAST_SIGNATURE) % {
                        "site_domain": site_domain,
                        "partner_name": row['issuer_display_name'],
                        "traderid": str(row['trader_id']).zfill(9),
                        "secret_code": row['email_cancellation_code'] }

                    trx.insert_outgoing_email(
                        subject,
                        "%s\n\n-- \n%s" % (content, wrap_text(signature)),
                        orig_date,
                        issuer_mailbox, row['issuer_display_name'],  # From
                        row['mailbox'], '',  # To
                        issuer_mailbox, '', # Reply-To
                        "noreply@%s" % site_domain, '')  # Sender
                    
            else:
                recipients = []

        for row in recipients:
            # This is rather ugly! We acquire the right to send the
            # mail after it have been sent already.  Nevertheless this
            # is OK, because "get_broadcast_recipient_list()" function
            # makes sure that traders that have exceeded their
            # receive-limit do not get emailed.  So, the only purpose
            # of the call bellow is to decrease the
            # "max_received_email_count" counter.
            with db.Transaction() as trx:
                trx.set_asynchronous_commit()
                trx.acquire_received_email_rights(row['trader_id'])



def process_notifications(db):
    notification_records = curiousorm.Cursor(dsn, """
        SELECT
          n.id, n.trader_id, n.to_mailbox, n.email_cancellation_code, 
          ts.last_request_language_code
        FROM outgoing_notification n, trader_status ts
        WHERE ts.trader_id=n.trader_id
        """, dictrows=True)

    for notification_id, trader_id, to_mailbox, email_cancellation_code, lang_code in \
            notification_records:

        exit_if_deadline_has_been_passed()

        # Compose the email message.
        _ = get_ugettext(lang_code)
        subject = _(messages.NOTIFICATION_SUBJECT)
        content = _(messages.NOTIFICATION_CONTENT) % {
            "site_domain": site_domain,
            "traderid": str(trader_id).zfill(9),
            "secret_code": email_cancellation_code }

        orig_date = datetime.datetime.now(pytz.utc)

        with db.Transaction() as trx:
            trx.set_asynchronous_commit()
            
            if trx.delete_outgoing_notification(notification_id):

                # Only if the notification record existed and has been
                # successfully deleted, we insert the composed message
                # into the "outgoing_email" table.
                trx.insert_outgoing_email(
                    subject, wrap_text(content), orig_date,
                    "noreply@%s" % site_domain, site_domain,  # From
                    to_mailbox, '',  # To
                    '', '', '', '')
                


def send_outgoing_emails(db):
    outgoing_emails = curiousorm.Cursor(dsn, """
        SELECT
          id, subject, content, orig_date,
          from_mailbox, from_display_name,
          to_mailbox, to_display_name,
          reply_to_mailbox, reply_to_display_name,
          sender_mailbox, sender_display_name
        FROM outgoing_email
        """, buffer_size=100, dictrows=True)

    smtp_connection = smtplib.SMTP(smtp_host)
    try:
        if smtp_username:
            smtp_connection.login(smtp_username, smtp_password)
        
        for m in outgoing_emails:
            
            exit_if_deadline_has_been_passed()
            
            try:
                send_email(smtp_connection, m)
            except (smtplib.SMTPRecipientsRefused, smtplib.SMTPSenderRefused):
                # This should never happen, but anyway, it does not brake anything.
                pass
            
            with db.Transaction() as trx:
                trx.set_asynchronous_commit()
                trx.delete_outgoing_email(m['id'])
                
    finally:
        smtp_connection.quit()
        


if __name__ == "__main__":
    smtp_host = os.environ.get('SMTP_HOST', 'localhost')
    smtp_username = ''
    smtp_password = ''
    site_domain = CMBARTER_HOST
    dsn = CMBARTER_DSN
    parse_args(sys.argv[1:])
    db = curiousorm.Connection(dsn, dictrows=True)

    # We must ensure that at most one process in running at a time, so
    # we try to obtain an advisory database lock. This lock is held by
    # execute_turn.py, so we are guaranteed that we will not take
    # precious system resources while a turn is running.
    if db.pg_try_advisory_lock(1):
        try:
            process_email_validations(db)
            process_outgoing_customer_broadcasts(db)
            process_notifications(db)
            send_outgoing_emails(db)
        finally:
            db.pg_advisory_unlock(1)

    db.close()
