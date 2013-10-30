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
from fcntl import lockf, LOCK_EX, LOCK_NB
from cmbarter.settings import CMBARTER_SESSION_DIR, CMBARTER_PROJECT_DIR


USAGE = """Usage: check_sessions.py [OPTIONS]
Delete old session files.

Will exit immediately if another copy of the program is already
running. In this case, the process ID of the currently running process
can be found in the ./cmbarter/check_sessions.lock file.

  -h, --help           display this help and exit
  --dir=DIRECTORY      give the session directory explicitly
  --prefix=PREFIX      specify the session file prefix (default: 'sessionid')
  --maxage=SECONDS     specify the maximum session age (default: 2400 seconds)
  --maxfiles=NUMBER    specify the maximum number of files in a directory 
                       that the OS can handle without serious performance
                       degradation (default: 50000 files)

  --repeat-interval=N  if N=0 (the default), the program will exit after one 
                       check is done;

                       if N>0, the program will continue to execute checks 
                       "ad infinitum" with idle intervals of N seconds between
                       the checks.

Example:
  $ ./check_sessions.py --maxage=10000
"""


def parse_args(argv):
    global prefix, directory, duration, maxfiles, repeat_interval
    try:                                
        opts, args = getopt.gnu_getopt(argv, 'h', ['prefix=', 'dir=', 'maxage=', 
                                                   'maxfiles=', 'repeat-interval=', 'help'])
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
        elif opt == '--maxfiles':
            try:
                maxfiles = int(arg)
            except ValueError:
                print(USAGE)
                sys.exit(2)                  
        elif opt == '--repeat-interval':
            try:
                repeat_interval = int(arg)
            except ValueError:
                print(USAGE)
                sys.exit(2)                  
        elif opt == '--maxage':
            try:
                duration = float(arg)
            except ValueError:
                print(USAGE)
                sys.exit(2)


def examine_sessions():
    while True:
        current_time = time.time()
        fname_list = os.listdir(directory)
        aggressive = len(fname_list) > maxfiles
        for fname in fname_list:
            if fname.startswith(prefix):
                fabsname = os.path.join(directory, fname)
                try:
                    if ( (aggressive and os.path.getsize(fabsname) < 1000) or
                         (current_time - os.path.getmtime(fabsname) > duration) ):
                        os.unlink(fabsname)
                except OSError:
                    pass
        if repeat_interval == 0:
            break
        else:
            time.sleep(repeat_interval)


if __name__ == "__main__":
    prefix = 'sessionid'
    directory = CMBARTER_SESSION_DIR
    duration = 2400.0
    maxfiles = 50000
    repeat_interval = 0
    parse_args(sys.argv[1:])

    # try to obtain exclusive lock on ./cmbarter/check_sessions.lock
    f = open(os.path.join(CMBARTER_PROJECT_DIR, 'check_sessions.lock'), 'r+')
    try:
        lockf(f, LOCK_EX | LOCK_NB)
    except IOError:
        if repeat_interval == 0:
            print '%s: another copy of the program is already running' % __file__
            sys.exit(2)
        else:
            sys.exit()  # no error message, otherwise 'cron' would email it
    else:
        f.write('%i\n' % os.getpid())
        f.truncate()

    examine_sessions()
