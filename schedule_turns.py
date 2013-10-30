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
## This file implements the turn scheduling command-line tool.
##
import sys, getopt
from datetime import date, datetime
from cmbarter.settings import CMBARTER_DSN
from cmbarter.modules import curiousorm


USAGE = """Usage: schedule_turns.py NEXT_TURN_TIME [OPTIONS]
Set trading turns' time and period.

  -h, --help           display this help and exit
  --period=HOUSRS      set the period between turns in hours (default: 24)
  --dsn=DSN            give explicitly the database source name

Examples:
  $ ./schedule_turns.py 2:30
  $ ./schedule_turns.py 2013-02-10T12:25:30 --period=0.01
"""


def parse_args(argv):
    global time, dsn, period_seconds
    try:                                
        opts, args = getopt.gnu_getopt(argv, 'h', ['period=', 'dsn=', 'help'])
    except getopt.GetoptError:
        print(USAGE)
        sys.exit(2)

    if len(args) != 1:
        print(USAGE)
        sys.exit(2)

    # Construct the time-string from the passed argument:
    time_str = args[0]
    if not 'T' in time_str:
        time_str = '%sT%s' % (date.today().isoformat(), time_str)

    # Parse the time-string:
    for fmt in ['%Y-%m-%dT%H:%M', '%Y-%m-%dT%H:%M:%S']:
        try:
            time = datetime.strptime(time_str, fmt)
        except ValueError:
            continue
        else:
            break
    else:
        print(USAGE)
        sys.exit(2)

    for opt, arg in opts:
        if opt in ('-h', '--help'):
            print(USAGE)
            sys.exit()
        elif opt == '--period':
            try:
                period_seconds = int(3600 * float(arg))
                if period_seconds < 1:
                    raise ValueError
            except ValueError:
                print(USAGE)
                sys.exit(2)                  
        elif opt == '--dsn':
            dsn = arg


if __name__ == "__main__":
    dsn = CMBARTER_DSN
    period_seconds = 24 * 60 * 60
    parse_args(sys.argv[1:])

    db = curiousorm.Connection(dsn, dictrows=True)
    db.update_solver_schedule(time, period_seconds)
    db.close()
