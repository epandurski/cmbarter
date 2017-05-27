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
from cmbarter.settings import CMBARTER_REGISTRATION_KEY_PREFIX, SECRET_KEY

USAGE = """Usage: generate_regkeys.py --start=INTEGER --count=INTEGER
Print a sequence of valid registration keys.

  --start=INTEGER     the sequential number of the first key in the
                      sequence (must be between 0 and 4294967295)
  --count=INTEGER     number of consecutive keys to be printed

Example:
  $ ./generate_regkeys.py --start=0 --count=100
  ... [Prints registration keys with sequence numbers 0-99]
"""


def parse_args(argv):
    global start, count

    try:                                
        opts, args = getopt.gnu_getopt(argv, 'h', ['start=', 'count=', 'help'])
    except getopt.GetoptError:
        print(USAGE)
        sys.exit(2)

    if len(args) != 0:
        print(USAGE)
        sys.exit(2)

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
    start = None
    count = 0
    parse_args(sys.argv[1:])
    if (start is None) or (count == 0):
        print(USAGE)
        sys.exit()

    gen = keygen.Keygen(SECRET_KEY, CMBARTER_REGISTRATION_KEY_PREFIX)
    for i in range(start, start + count):
        print gen.generate(i)
