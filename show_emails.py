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
## This file implements the command-line tool that shows all
## customers's emails.
##
import sys, getopt
from cmbarter.settings import CMBARTER_DSN
from cmbarter.modules.utils import encode_domain_as_idna
from cmbarter.modules.curiousorm import Cursor


USAGE = """Usage: show_emails.py [OPTIONS]
Print all customers' email addresses.

  -h, --help           display this help and exit
  --dsn=DSN            give explicitly the database source name

Examples:
  $ ./show_emails.py
"""


def parse_args(argv):
    global dsn
    try:                                
        opts, args = getopt.gnu_getopt(argv, 'h', ['dsn=', 'help'])
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


if __name__ == "__main__":
    dsn = CMBARTER_DSN
    parse_args(sys.argv[1:])

    emails = set()
    for row in Cursor(dsn, 'SELECT email FROM verified_email'):
        emails.add(encode_domain_as_idna(row.email))
    for e in emails:
        print e
