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
## This file implements the whitelist showing command-line tool.
##
import sys, getopt
from cmbarter.settings import CMBARTER_DSN
from cmbarter.modules.curiousorm import Cursor


USAGE = """Usage: show_whitelist.py [OPTIONS]
Print a list of "whitelisted" IP addresses.

  -h, --help           display this help and exit
  -u, --unique         eliminate duplicate entries (consumes more memory)
  -4, --ipv4           show IPv4 addresses only
  -6, --ipv6           show IPv6 addresses only
  --dsn=DSN            give explicitly the database source name

Examples:
  $ ./show_whitelist.py -4
"""


def parse_args(argv):
    global dsn, unique, addr_type
    try:                                
        opts, args = getopt.gnu_getopt(argv, 'hu46', ['dsn=', 'help', 'unique', 'ipv4', 'ipv6'])
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
        if opt in ('-u', '--unique'):
            unique = True
        if opt in ('-4', '--ipv4'):
            addr_type = 'ipv4'
        if opt in ('-6', '--ipv6'):
            addr_type = 'ipv6'
        elif opt == '--dsn':
            dsn = arg


def add_to_whitelist(ip):
    if addr_type == 'ipv4' and ':' in ip:
        return
    if addr_type == 'ipv6' and ':' not in ip:
        return
    if unique:
        whitelist.add(ip)
    else:
        print ip


if __name__ == "__main__":
    unique = False
    dsn = CMBARTER_DSN
    addr_type = 'all'
    whitelist = set()
    parse_args(sys.argv[1:])

    for row in Cursor(dsn, """
      SELECT network_address
      FROM whitelist_entry
      WHERE insertion_ts > CURRENT_TIMESTAMP - INTERVAL '3 months'
      """):
        add_to_whitelist(row.network_address)
    for ip in whitelist:
        print ip
