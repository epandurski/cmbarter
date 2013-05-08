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
## This file contains messages that have to be translated. Its purpose
## is to make translation tools include these messages in generated
## the PO-file.
##
import gettext

_ = gettext.gettext

_ = lambda msg: msg

ADDRESS_VERIFICATION_SUBJECT = _("Email address verification")
ADDRESS_VERIFICATION_CONTENT = _(
    "You have a registered user account on %(site_domain)s, and you have "
    "specified this address (%(email)s) as user contact.\n\n"
    "If you did not do this, please ignore this message.\n\n"
    "To confirm that this address is correct, please follow this link:\n\n"
    "https://%(site_domain)s/confirm/%(traderid)s/%(secret_code)s/\n\n"
    "Regards,\n"
    "The %(site_domain)s team\n"
    )

CUSTOMER_BROADCAST_SIGNATURE = _(
    "You received this message because you have a user "
    "account on %(site_domain)s, and you have added "
    "%(partner_name)s to your list of trading partners. "
    "If you do not want to receive any more messages "
    "from %(site_domain)s, please follow this link and "
    "unsubscribe:\n"
    "https://%(site_domain)s/cancel/%(traderid)s/%(secret_code)s/\n"
    ) 

NOTIFICATION_SUBJECT = _("Transaction notification")
NOTIFICATION_CONTENT = _(
    "There are one or more new transactions on your user account at "
    "%(site_domain)s.\n\n"
    "Please, log in to your account and examine the new transactions.\n\n"
    "https://%(site_domain)s/login/\n\n\n"
    "-- \n"
    "You received this message because you have a user account on "
    "%(site_domain)s. If you do not want to receive any more messages "
    "from %(site_domain)s, please follow this link and unsubscribe:\n"
    "https://%(site_domain)s/cancel/%(traderid)s/%(secret_code)s/\n"
    ) 
