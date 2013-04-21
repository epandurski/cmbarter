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
from cmbarter.modules.digraph import Digraph
from cmbarter.modules.utils import buffered_cursor_iter


USAGE = """Usage: execute_turn.py [OPTIONS]
Executes a trading turn if the time has come.

  -h, --help
         Display this help and exit.

  -n, --no-cluster
         Does not perform database table clustering.

  --dsn=DSN
         Give explicitly the database source name.

  --timespan=MINUTES
         Set the duration of each calculation cycle.

         The "timespan" becomes important when the "level" setting is
         more complex than a single number.

         The default is: --timespan=60 (1 hour)

  --level=L1[+L2..+LN]  
         Set the order of magnitude of the MTV.

         MTV stands for "Minimum Transferable Value".  It is the value
         under which a trading cycle will not be considered worth it
         being executed.

         The default is: --level=0 (MTV=0.01)

         For example: "--level=3+1+1" means that:

           1. A calculation with a duration of "timespan" will start
              having MTV=10 (0.01 * 10^3).

           2. It will be followed by another calculation with a
              duration of "timespan", having MTV=100 (0.01 *
              10^(3+1)).

           3. A calculation of unlimited time will start having
              MTV=1000 (0.01 * 10^(3+1+1)).
                               
Example:
  $ ./execute_turn.py -n --timespan=90 --level=0+3+30
"""



def commitments():
    return buffered_cursor_iter(dsn, """
        SELECT recipient_id, issuer_id, promise_id, value
        FROM commitment
        ORDER BY ordering_number
        """)



class BufferedInserter:
    BUFFER_SIZE = 5000
    
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
            self.connection.execute(self.template % values_str)
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



class BondMatcher:
    """Generate cycles in response to a succession of bonds.

    The minial meaningful amount should be passed to the constructor.
    >>> cg = BondMatcher(100.0)

    We feed some bonds:
    >>> cg.register_bond(1, 2, 120.0)
    >>> cg.register_bond(2, 3, 150.0)

    The next call is void -- its amount is less than 100.0
    >>> cg.register_bond(3, 1, 1.0)
    >>> cg.bonds
    {(1, 2): 120.0, (2, 3): 150.0}

    This call closes the cycle:
    >>> cg.register_bond(3, 1, 250.0)
    >>> cg.pop_cycles()
    [([1, 2, 3], 120.0)]
    
    All amounts are decremented by 120.0. As a result two of them
    became void because thier remaining amount is now less than 100.0:
    >>> cg.bonds
    {(3, 1): 130.0}

    We cancel the ramaining bond:
    >>> cg.unregister_bond(3, 1)
    >>> cg.bonds
    {}
    """
    
    def __init__(self, min_mamt):
        assert (min_mamt > 0)
        self.min_mamt = min_mamt
        self.bonds = {}
        self.graph = Digraph()
        self.cycles = []


    def register_bond(self, u, v, mamt):
        if mamt >= self.min_mamt:
            is_new_bond = (u, v) not in self.bonds
            self.bonds[(u, v)] = mamt
            self.graph.add_arc(u, v)
            if is_new_bond:
                while self.graph.has_arc(u, v):
                    path = self.graph.find_path(v, u)
                    if path:
                        mamt, updated_bonds = self._calc_cycle(path)
                        self.cycles.append((path, mamt))
                        for bond in updated_bonds:
                            self.register_bond(*bond)
                    else:
                        break
        else:
            self.unregister_bond(u, v)


    def unregister_bond(self, u, v):
        self.graph.remove_arc(u, v)
        self.bonds.pop((u, v), None)


    def pop_cycles(self):
        cycles = self.cycles
        self.cycles = []
        return cycles


    def _calc_cycle(self, path):
        arcs = [(path[i-1], path[i]) for i in range(len(path))]        
        mamt = min(self.bonds[a] for a in arcs)
        bonds = [(a[0], a[1], self.bonds[a] - mamt) for a in arcs]
        return mamt, bonds



def _int2str(i):
    b_list = (
        i & 0x000000ff, 
        (i & 0x0000ff00) >> 8, 
        (i & 0x00ff0000) >> 16, 
        (i & 0x7f000000) >> 24,
        )
    return ''.join([chr(b) for b in b_list])



def _str2int(s):
    b0, b1, b2, b3 = [ord(c) for c in s]
    return b0 + (b1 << 8) + (b2 << 16) + (b3 << 24)



def pair2str(a, b):
    """
    Transforms two positive 32-bit integers to interned string.

    >>> s1 = pair2str(1, 234567)
    >>> s2 = pair2str(1, 234567)
    >>> s1 is s1
    True
    """

    return intern(_int2str(a) + _int2str(b))



def str2pair(s):
    """
    Restores the integers (a, b) if given the string produced by pair2str(a, b).

    Example:
    >>> str2pair(pair2str(123, 456))
    (123, 456)
    """

    return _str2int(s[0:4]), _str2int(s[4:8])



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
    global dsn, no_cluster, timespan, level
    try:                                
        opts, args = getopt.gnu_getopt(argv, 'hn', ['dsn=', 'timespan=', 'level=', 'help', 'no-cluster'])
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
        elif opt == '--timespan':
            try:
                timespan = max(int(arg), 1)
            except ValueError:
                print(USAGE)
                sys.exit()                  
        elif opt == '--level':
            try:
                level = [max(int(i), 0) for i in arg.split('+')]
            except ValueError:
                print(USAGE)
                sys.exit()
        elif opt in ('-n', '--no-cluster'):
            no_cluster = True



def cluster():
    o = curiousorm.Connection(dsn, autocommit=True)
    o.execute('CLUSTER')
    o.close()



def match_commitments(db):
    matcher = BondMatcher(Decimal('0.01'))
    bonds = (commitment2bond(*c) for c in commitments())
    matched_commitments = BufferedMatchedCommitmentInserter(db)
    timespan_level_idx = 0
    timespan_end = -1e99

    for b in bonds:
        now = time()
        if now > timespan_end:
            # Increase the minimal transferable value at the end of each timespan.
            try:
                matcher.min_mamt *= 10**level[timespan_level_idx]
            except IndexError:
                pass
            timespan_level_idx += 1
            timespan_end = now + 60.0 * timespan

        # Register the bond and try to find cycles.
        matcher.register_bond(*b)
        for path, amount in matcher.pop_cycles():
            matched_bonds = [(path[i-1], path[i], amount) for i in range(len(path))]
            for mb in matched_bonds:
                matched_commitments.insert(bond2commitment(*mb), flush_if_full=False)

        # Write the found cycles to the database.
        matched_commitments.flush_if_full()

    matched_commitments.flush()



if __name__ == "__main__":
    # Read command-line parameters.
    dsn = CMBARTER_DSN
    timespan = 60
    level = [0]
    no_cluster = False
    parse_args(sys.argv[1:])

    # See if we should perform a trading turn.
    db = curiousorm.Connection(dsn)
    should_perform_a_trading_turn = db._lock_solver()  # This will block and wait if another process is holding the lock.
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
