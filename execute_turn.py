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
## This file implements the trading turn execution procedure.
##
import sys, getopt
from decimal import Decimal
from time import time
from cmbarter.settings import CMBARTER_DSN
from cmbarter.modules import curiousorm
from cmbarter.modules.matcher import BondMatcher, pair2str, str2pair


USAGE = """Usage: execute_turn.py [OPTIONS]
Executes a trading turn if the time has come.

  -h, --help
         Display this help and exit.

  -n, --no-cluster
         Does not perform database table clustering.

  --dsn=DSN
         Give explicitly the database source name.

  --level=INTEGER
         Controls how big the MCV should be.

         MCV stands for "Minimum Cycle Value". It is the monetary
         value below which a trading cycle is considered not worthy of
         being executed. Bigger MCVs may speed up the execution of
         trading turns, but too big MCVs may miss worthy deals.

         Typical values:
         --level=0 (MCV=0.01 the default)
         --level=1 (MCV=0.1)
         --level=2 (MCV=1)
         --level=3 (MCV=10)
         --level=4 (MCV=100)
                               
Example:
  $ ./execute_turn.py -n --level=3
"""



def commitments():
    return curiousorm.Cursor(dsn, """
        SELECT recipient_id, issuer_id, promise_id, value
        FROM commitment
        ORDER BY ordering_number
        """, dictrows=True)



class BufferedInserter:
    BUFFER_SIZE = 10000
    
    def __init__(self, connection, template):
        self.connection = connection
        self.template = template
        self.rows = []

    def insert(self, row, flush_if_full=True):
        self.rows.append(row)
        if flush_if_full:
            self.flush_if_full()

    def flush(self):
        if self.rows:
            values = (','.join(map(str, row)) for row in self.rows)
            values_str = '),('.join(values)
            with self.connection.Transaction() as trx:
                trx.set_asynchronous_commit()
                trx.execute(self.template % values_str)
            self.rows = []

    def flush_if_full(self):
        if len(self.rows) > self.BUFFER_SIZE:
            self.flush()



class BufferedMatchedCommitmentInserter(BufferedInserter):
    def __init__(self, connection):
        BufferedInserter.__init__(self, connection, """
        INSERT INTO matched_commitment (recipient_id, issuer_id, promise_id, value)
        VALUES (%s)
        """)



def commitment2bond(recipient_id, issuer_id, promise_id, value):
    if value>=0:
        return pair2str(recipient_id, 0), pair2str(issuer_id, promise_id), value
    else:
        return pair2str(issuer_id, promise_id), pair2str(recipient_id, 0), -value



def bond2commitment(buyer, seller, max_value):
    buyer_id, buyer_slot_id = str2pair(buyer)
    seller_id, seller_slot_id = str2pair(seller)
    if seller_slot_id==0:
        assert buyer_slot_id!=0
        return seller_id, buyer_id, buyer_slot_id, -max_value
    else:
        assert buyer_slot_id==0
        return buyer_id, seller_id, seller_slot_id, max_value



def parse_args(argv):
    global dsn, no_cluster, level
    try:                                
        opts, args = getopt.gnu_getopt(argv, 'hn', ['dsn=', 'level=', 'help', 'no-cluster'])
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
        elif opt == '--level':
            try:
                level = max(int(arg), 0)
            except ValueError:
                print(USAGE)
                sys.exit(2)
        elif opt in ('-n', '--no-cluster'):
            no_cluster = True



def cluster():
    o = curiousorm.Connection(dsn, dictrows=True)
    o.execute('CLUSTER')
    o.close()



def match_commitments(db):
    bonds = (commitment2bond(*c) for c in commitments())
    matcher = BondMatcher(10**level)
    for buyer, seller, amount in bonds:
        matcher.register_bond(buyer, seller, int(amount.scaleb(2)))
    matcher.start()
    matched_commitments = BufferedMatchedCommitmentInserter(db)

    while True:
        deal = matcher.find_deal()
        if not deal:
            break
        path, amount = deal[0], Decimal(deal[1]).scaleb(-2)
        matched_bonds = [(path[i-1], path[i], amount) for i in range(len(path))]
        for b in matched_bonds:
            matched_commitments.insert(bond2commitment(*b), flush_if_full=False)
        matched_commitments.flush_if_full()

    matched_commitments.flush()



if __name__ == "__main__":
    # Read command-line parameters.
    dsn = CMBARTER_DSN
    level = 0
    no_cluster = False
    parse_args(sys.argv[1:])

    # See if we should perform a trading turn.
    db = curiousorm.Connection(dsn, dictrows=True)
    should_perform_a_trading_turn = db._lock_solver()  # will block if other process has the lock
    try:
        # "should_perform_a_trading_turn" can be False if the time for
        # the next trading turn has not yet come; or if the solver has
        # not been explicitly unlocked due to a prior server-crash.
        if should_perform_a_trading_turn==True:
            db._prepare_commitments()
            match_commitments(db)
            db._write_deals()
            db._perform_housekeeping()
            db._schedule_notifications()
            db._update_user_limits()
            no_cluster or cluster()
    finally:
        db._unlock_solver()
        db.close()
