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
## This file implements the garbage collection of stale sessions.
##
import sys, os, os.path, getopt, time
from cmbarter.settings import CMBARTER_SESSION_DIR


USAGE = """Usage: check_sessions.py [OPTIONS]
Delete old session files.

  -h, --help           display this help and exit
  --dir=DIRECTORY      give the session directory explicitly
  --prefix=PREFIX      specify the session file prefix (default: 'sessionid')
  --maxage=SECONDS     specify the maximum session age (default: 3600 seconds)

Example:
  $ ./check_sessions.py --maxage=10000
"""


def parse_args(argv):
    global prefix, directory, duration
    try:                                
        opts, args = getopt.gnu_getopt(argv, 'h', ['prefix=', 'dir=', 'maxage=', 'help'])
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
        elif opt == '--prefix':
            prefix = arg
        elif opt == '--dir':
            directory = arg
        elif opt == '--maxage':
            try:
                duration = float(arg)
            except ValueError:
                print(USAGE)
                sys.exit()                  


if __name__ == "__main__":
    prefix = 'sessionid'
    directory = CMBARTER_SESSION_DIR
    duration = 3600.0
    parse_args(sys.argv[1:])
    currtime = time.time()

    for fname in os.listdir(directory):
        if fname.startswith(prefix):
            fabsname = os.path.join(directory, fname)
            try:
                mtime = os.path.getmtime(fabsname)
                if currtime - mtime > duration:
                    os.unlink(fabsname)
            except OSError:
                sys.exit()
