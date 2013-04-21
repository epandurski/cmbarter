from __future__ import division
import random, time, sys
from multiprocessing import Process, Queue, cpu_count
from Queue import Empty, Full
from heapq import heappush, heappop
from collections import deque

CPU_COUNT = 1



class Digraph:
    """Directed graph.

    We create a graph:
    >>> graph = Digraph()

    Add some arcs:
    >>> graph.add_arc(1, 2)
    >>> graph.add_arc(1, 3)
    >>> graph.vmap
    {1: set([2, 3])}

    Remove arcs we just have added:
    >>> graph.remove_arc(1,2)
    >>> graph.vmap
    {1: set([3])}
    >>> graph.has_arc(1, 3)
    True
    >>> graph.has_arc(3, 1)
    False
    >>> graph.remove_arc(1,3)
    >>> graph.vmap
    {}

    Let add more new arcs:
    >>> graph.add_arc(-1, 2)
    >>> graph.add_arc(2, -2)
    >>> graph.add_arc(-2, 3)
    >>> graph.add_arc(3, -3)    
    >>> graph.add_arc(-3, 1)
    >>> graph.add_arc(99, 99)    

    Now we try to find path in the graph we just defined starting from
    vertex '-1' and ending at vertex '1'.
    >>> path = graph.find_path(-1, 1)
    
    Display the path we just found.
    >>> path
    [-1, 2, -2, 3, -3, 1]

    Trying to find a non-existing path:
    >>> graph.find_path(-1, -1) == None
    True

    Finding a trivial cycle:
    >>> graph.find_path(99, 99)
    [99, 99]
    """
    
    def __init__(self):
        self.vmap = {}

    def has_arc(self, u, v):
        """Retrurn True if (u --> v) exists, False otherwise."""
        
        if u in self.vmap:
            if v in self.vmap[u]:
                return True
        return False

    def add_arc(self, u, v):
        """Add arc (u --> v)."""
        
        if u in self.vmap:
            self.vmap[u].add(v)
        else:
            self.vmap[u] = set([v])

    def remove_arc(self, u, v):
        """Remove the arc (u --> v) if exists."""
        
        if u in self.vmap:
            self.vmap[u].discard(v)
            if not self.vmap[u]:
                del self.vmap[u]

    def find_path(self, u, v):
        """Return a path from u to v if exists.

        The path is returned as a list of vertices [u...v]. If no path
        has been found, returns None.
        """

        visited_vertices = set()
        visited_vertices.add(u)
        empty_set = set()

        # These lists will hold the data for our working-stack. We
        # over-allocate to avoid trivial re-allocations:
        path = [u, None, None, None, None, None, None, None]
        vertex_iterators = [iter(self.vmap.get(u, ())), None, None, None, None, None, None, None]

        stack_length = 1

        while stack_length > 0:
            try:
                # Get the next vertex to visit from the
                # vertex-iterator sitting at the top of the stack:
                next = vertex_iterators[stack_length-1].next()
                if next == v:
                    return path[:stack_length] + [next]  # A path is found.

                # Make sure this vertex has not been visited already:
                if next in visited_vertices: 
                    continue
                else:
                    visited_vertices.add(next)

                # Push this vertex and an iterator on its
                # successor-vertices to the stack:
                try:
                    path[stack_length] = next
                except IndexError:
                    # Extend the lists holding the stack, then retry:
                    padding = [None] * len(path)
                    path.extend(padding)
                    vertex_iterators.extend(padding)
                    path[stack_length] = next
                vertex_iterators[stack_length] = iter(self.vmap.get(next, empty_set))
                stack_length += 1

            except StopIteration:
                # Pops the stack.
                #
                # We never physically remove elements from the stack
                # so as to avoid memory re-allocations due to
                # repetitive list-expansion and list-shrinkage.
                stack_length -= 1

        return None



def create_list(cls, length):
    return [cls() for i in range(length)]



class solver:
    """
    A process that finds cycles in a digraph.

    You must not create instances of this class directly. Use the
    multiprocessing module instead.
    """

    def __init__(self, solver_index, arcs, request_q, response_q):
        assert 0 <= solver_index < CPU_COUNT
        self.solver_index = solver_index
        self.arc_iter = iter(arcs)
        self.request_q = request_q
        self.response_q = response_q
        self.graph = Digraph()
        self.request_heap = []
        self.removed_arcs = set()
        self.gen = 0
        self.reached_last_arc = False
        self.reached_last_request = False
        self.run()


    def wait_for_request(self):
        request = self.request_q.get()
        heappush(self.request_heap, request)


    def fetch_request_q(self):
        while True:
            try:
                request = self.request_q.get_nowait()
            except Empty:
                break
            heappush(self.request_heap, request)

 
    def process_request_heap(self):
        while True:
            try:
                gen, u, v = self.request_heap[0]
            except IndexError:
                break  # the heap is empty
            if gen > self.gen:
                break  # can not analyze future generations
            if gen == -2:
                self.reached_last_request = True
                break  # received command to exit
            request = heappop(self.request_heap)
            if gen == -1:
                self.graph.remove_arc(u, v)
                self.removed_arcs.add((u, v))
            elif self.graph.has_arc(u, v):
                path = self.graph.find_path(v, u)
                if path:
                    self.response_q.put((request, path))


    def add_new_arc(self):
        try:
            arc = next(self.arc_iter)
        except StopIteration:
            self.reached_last_arc = True
            self.response_q.put((None, []))  # signals "finished"
            return
        self.gen += 1
        if arc not in self.removed_arcs:
            self.graph.add_arc(*arc)
        if self.gen % CPU_COUNT == self.solver_index:
            heappush(self.request_heap, (self.gen, arc[0], arc[1]))


    def run(self):
        while not self.reached_last_request:
            if self.reached_last_arc:
                self.wait_for_request()
            else:
                self.add_new_arc()
                self.fetch_request_q()
            self.process_request_heap()



def queue_consumer(q):
    """
    A process that blindly consumes a queue.

    You must not call this function directly. Use the multiprocessing
    module instead.
    """

    while q.get() is not None:
        pass



class PathNotFound(Exception):
    """
    Raised when a circular path has not been found.
    """


class SolverPool:
    """
    An asynchronous pool of digraph cycle finders.

    Althought this class can be used directly, its main purpose is to
    be used by "BondSolver".

    Here is an example usage scenario:
    >>> arcs = [('A', 'B'), ('B', 'C'), ('C', 'A')]
    >>> p = SolverPool(arcs)
    >>> p.start()
    >>> path = p.wait_for_cycle()
    >>> sorted(path)
    ['A', 'B', 'C']
    >>> p.remove_arc('B', 'C')

    You may get non-existing cycles sometimes, but not forever:
    >>> while p.wait_for_cycle(): pass
    Traceback (most recent call last):
    ...
    PathNotFound

    It should be stopped at the end:
    >>> p.stop()
    """

    def __init__(self, arcs):
        self.request_q_list = create_list(Queue, CPU_COUNT)
        self.response_q = Queue(maxsize=10*CPU_COUNT)
        self.solver_p_list = []
        for i in xrange(CPU_COUNT):
            self.solver_p_list.append(
                Process(
                    target=solver,
                    args=(
                        i,
                        arcs,
                        self.request_q_list[i], 
                        self.response_q,
                        )))
        self.unfinished_solver_count = CPU_COUNT
        self.request_deque_list = create_list(deque, CPU_COUNT)
        self.request_dq_zip = zip(self.request_deque_list, self.request_q_list)
        self.pending_request = None


    def start(self):
        for p in self.solver_p_list:
            p.start()


    def wait_for_cycle(self):
        if self.pending_request:
            random.choice(self.request_deque_list).append(self.pending_request)
            self.pending_request = None
        while True:
            # We must be careful to prevent deadlocks!
            self.flush_request_deques()
            try:
                self.pending_request, path = self.response_q.get(timeout=5.0)
                if path:
                    return path
                else:
                    self.unfinished_solver_count -= 1
            except Empty:
                if self.unfinished_solver_count == 0:
                    raise PathNotFound


    def remove_arc(self, u, v):
        for d in self.request_deque_list:
            d.append((-1, u, v))


    def stop(self):
        consumer_p = Process(target=queue_consumer, args=(self.response_q,))
        consumer_p.start()
        if len(self.solver_p_list) > 0:
            for q in self.request_q_list:
                q.put((-2, None, None))  # forces solvers to quit
            for p in self.solver_p_list:
                p.join()
            self.solver_p_list = []
        self.response_q.put(None)  # forces the consumer to quit
        consumer_p.join()


    def flush_request_deques(self):
        for d, q in self.request_dq_zip:
            while True:
                try:
                    request = d.popleft()
                except IndexError:
                    break
                try:
                    q.put_nowait(request)
                except Full:
                    d.appendleft(request)
                    break


        
class BondSolver:
    """
    An asynchronous bond solver -- generates deals when loaded with bonds.

    The minial meaningful amount is passed to the constructor.
    >>> s = BondSolver(100)

    Register some bonds:
    >>> s.register_bond(1, 2, 120)
    >>> s.register_bond(2, 3, 150)
    >>> s._bonds
    {(1, 2): 120, (2, 3): 150}

    The next bond is void because its amount is less than 100:
    >>> s.register_bond(3, 1, 1)
    >>> s._bonds
    {(1, 2): 120, (2, 3): 150}

    This bond closes the cycle:
    >>> s.register_bond(3, 1, 250)

    Start the solver and wait for a deal:
    >>> s.start()
    >>> path, amount = s.wait_for_deal()
    >>> sorted(path)
    [1, 2, 3]
    >>> amount
    120
    
    All bond amounts were decremented by 120. As a result two of them
    became void because their remaining amount is less than 100:
    >>> s._bonds
    {(3, 1): 130}

    Try to find a deal again:
    >>> s.wait_for_deal()
    Traceback (most recent call last):
    ...
    PathNotFound

    Stop the solver:
    >>> s.stop()
    """
    
    def __init__(self, min_mamt):
        assert (min_mamt > 0)
        self._min_mamt = min_mamt
        self._bonds = {}
        self._is_started = False


    def register_bond(self, u, v, mamt):
        if self._is_started:
            raise Exception('can not register bonds after started')
        elif mamt >= self._min_mamt:
            self._bonds[(u, v)] = mamt
        else:
            self._bonds.pop((u, v), None)


    def start(self):
        if self._is_started:
            raise Exception('the bond solver is already started')
        self._pool = SolverPool(self._bonds)
        self._pool.start()
        self._is_started = True


    def wait_for_deal(self):
        while True:
            path = self._pool.wait_for_cycle()
            mamt, updated_bonds = self._calc_cycle(path)
            if mamt > 0:
                break
        for bond in updated_bonds:
            self._update_bond(*bond)
        return path, mamt


    def stop(self):
        if not self._is_started:
            raise Exception('the bond solver is not started')
        self._pool.stop()


    def _update_bond(self, u, v, mamt):
        if mamt >= self._min_mamt:
            self._bonds[(u, v)] = mamt
        else:
            self._bonds.pop((u, v), None)
            self._pool.remove_arc(u, v)


    def _calc_cycle(self, path):
        arcs = [(path[i-1], path[i]) for i in range(len(path))]        
        mamt = min(self._bonds.get(a, 0) for a in arcs)
        if mamt == 0:
            bonds = []
        else:
            bonds = [(a[0], a[1], self._bonds.get(a, 0) - mamt) for a in arcs]
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



if __name__ == '__main__':
    TRADER_COUNT = 40000
    BOND_COUNT = TRADER_COUNT * 5

    PRODUCT_COUNT = TRADER_COUNT // 10
    SELLERS_RATIO = 0.1
    AVG_SELL_AMOUNT = 100 * 1 / SELLERS_RATIO
    AVG_BUY_AMOUNT = SELLERS_RATIO * AVG_SELL_AMOUNT
    LOCALITY_DISTANCE = min(TRADER_COUNT, 10000)

    random.seed(1)
    lambd_sell = 1 / AVG_SELL_AMOUNT
    lambd_buy = 1 / AVG_BUY_AMOUNT
    trader_list = [(i, 0) for i in xrange(1, TRADER_COUNT+1)]
    producer_list = []
    for i in xrange(1, PRODUCT_COUNT+1):
        producer_list.append((random.randrange(1, TRADER_COUNT+1), i))

    bond_list = []
    while len(bond_list) < BOND_COUNT:
        producer = random.choice(producer_list)
        trader_list_index = (producer[0] - 1 + random.randrange(LOCALITY_DISTANCE+1)) % TRADER_COUNT
        trader = trader_list[trader_list_index]
        if random.random() < SELLERS_RATIO:
            amount = int(random.expovariate(lambd_sell))
            buyer, seller = producer, trader  # the switch is 2x slower!
        else:
            amount = int(random.expovariate(lambd_buy))
            buyer, seller = trader, producer
        bond_list.append((pair2str(*buyer), pair2str(*seller), amount))
    

    s = BondSolver(1)
    for b in bond_list:
        s.register_bond(*b)
    s.start()

    start_time = time.time()
    performed_deals = 0
    cleared_amount = 0
    while True:
        try:
            deal = s.wait_for_deal()
        except PathNotFound:
            break
        performed_deals += 1
        cleared_amount += len(deal[0]) * deal[1]
    s.stop()

    #print 'Performed deals = %i' % performed_deals
    #print 'Cleared amount = %i' % cleared_amount
    print 'CPU count = %i' % CPU_COUNT
    print 'Execution time = %f' % (time.time() - start_time)
    sys.exit()
