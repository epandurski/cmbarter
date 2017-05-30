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
## This file implements the registration key generation tool.
##
import sys, os, getopt
from cmbarter.modules import keygen

USAGE = """Usage: generate_regkeys.py [OPTIONS] [REGISTRATION_SECRET]
Print a sequence of registration keys.

  --start=INTEGER   the sequential number of the first key in the printed
                    sequence (between 0 and 4294967295, the default is 0)

  --count=INTEGER   number of consecutive keys to be printed (100 by default)

  If REGISTRATION_SECRET is omitted, the value of CMBARTER_REGISTRATION_SECRET
  environment variable will be used.

Example:
  $ ./generate_regkeys.py --start=10 --count=10 my-very-secret-string
  ... [Prints registration keys with sequence numbers 10-19]
"""


def parse_args(argv):
    global start, count, secret

    try:                                
        opts, args = getopt.gnu_getopt(argv, 'h', ['start=', 'count=', 'help'])
    except getopt.GetoptError:
        print(USAGE)
        sys.exit(2)

    if len(args) > 1:
        print(USAGE)
        sys.exit(2)
    try:
        secret = args[0]
    except IndexError:
        pass

    def srt2int(s):
        try:
            i = int(s)
            if not (0 <= i <= 0xffffffff):
                raise ValueError
        except ValueError:
            print(USAGE)
            sys.exit(2)
        else:
            return i

    for opt, arg in opts:
        if opt in ('-h', '--help'):
            print(USAGE)
            sys.exit()                  
        elif opt == '--start':
            start = srt2int(arg)
        elif opt == '--count':
            count = srt2int(arg)



if __name__ == '__main__':
    secret = os.environ.get('CMBARTER_REGISTRATION_SECRET')
    start = 0
    count = 100
    parse_args(sys.argv[1:])
    if not secret:
        print("ERROR: a registration secret must be supplied.")
        sys.exit()

    gen = keygen.Keygen(secret)
    for i in range(start, start + count):
        print gen.generate(i)
