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
## This file implements an algorithm for finding cycles in directed
## graphs.
##
from __future__ import division


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
    return b0 | (b1 << 8) | (b2 << 16) | (b3 << 24)


def pair2str(a, b):
    """
    Transforms two positive 32-bit integers to interned string.

    >>> s1 = pair2str(1, 234567)
    >>> s2 = pair2str(1, 234567)
    >>> s1 is s1
    True
    """
    assert a > 0 and b >= 0
    return intern(_int2str(a) + _int2str(b))


def str2pair(s):
    """
    Restores the integers (a, b) if given the string produced by pair2str(a, b).

    Example:
    >>> str2pair(pair2str(123, 456))
    (123, 456)
    """
    return _str2int(s[0:4]), _str2int(s[4:8])


ROOT_VERTEX = intern(8 * chr(0))


class Digraph:
    """
    A directed graph.

    Create a graph:
    >>> graph = Digraph()

    Add some arcs:
    >>> graph.add_arc(1, 2)
    >>> graph.add_arc(1, 3)

    Display all outgoing arcs from a given vertex:
    >>> graph._vmap[1]
    [2, 3]

    Remove some arcs:
    >>> graph.remove_arc(1, 2)
    >>> graph._vmap[1]
    [None, 3]
    >>> graph.has_arc(3, 1)
    False
    >>> graph.has_arc(1, 3)
    True
    >>> graph.remove_arc(1, 3)
    >>> graph._vmap[1]
    [None, None]

    Remove all outgoing arcs from a given vertex:
    >>> graph._sink_vertex(1)
    >>> 1 in graph._vmap
    False
    """
    
    def __init__(self):
        self._vmap = {ROOT_VERTEX: []}

    def has_arc(self, u, v):
        assert u != ROOT_VERTEX
        assert v is not None
        if u in self._vmap:
            if v in self._vmap[u]:
                return True
        return False

    def add_arc(self, u, v):
        assert v is not None
        assert v != ROOT_VERTEX
        if u in self._vmap:
            self._vmap[u].append(v)
        else:
            self._vmap[u] = [v]
            self._vmap[ROOT_VERTEX].append(u)

    def remove_arc(self, u, v):
        assert u != ROOT_VERTEX
        try:
            vlist = self._vmap[u]
            vlist[vlist.index(v)] = None
        except (KeyError, ValueError):
            pass

    def _sink_vertex(self, v):
        if v != ROOT_VERTEX:
            try:
                del self._vmap[v]
            except KeyError:
                pass


class IterationNode(object):
    __slots__ = ['vertex', 'vlist_index']

    def __init__(self, vertex):
        self.vertex = vertex
        self.vlist_index = 0


class CycleFinder:
    """
    Can find cycles in a given directed graph. (It removes arcs from the graph!)

    Create the graph:
    >>> graph = Digraph()
    >>> graph.add_arc(-1, 2)
    >>> graph.add_arc(2, -2)
    >>> graph.add_arc(-2, 3)
    >>> graph.add_arc(3, -3)    
    >>> graph.add_arc(-3, 1)
    >>> graph.add_arc(1, -1)
    >>> graph.add_arc(99, 99)    

    Create a cycle finder for the graph:
    >>> cf = CycleFinder(graph)
    >>> cf.find_cycle()
    [2, -2, 3, -3, 1, -1]
    >>> cf.find_cycle()
    [2, -2, 3, -3, 1, -1]

    >>> graph.remove_arc(1, -1)
    >>> cf.find_cycle()
    [99]
    """

    def __init__(self, graph):
        self.graph = graph
        self._listed_vertices = set()
        self._listed_vertices.add(ROOT_VERTEX)
        self._node_list = [IterationNode(ROOT_VERTEX)]
        self._top = 0

    def _pop_node(self):
        vertex = self._node_list[self._top].vertex
        self._listed_vertices.discard(vertex)
        self._top -= 1
        return vertex
        
    def _push_node(self, vertex):
        self._listed_vertices.add(vertex)
        self._top += 1
        try:
            node = self._node_list[self._top]
        except IndexError:
            padding = [None] * len(self._node_list)
            self._node_list.extend(padding)
            node = None
        if node is None:
            self._node_list[self._top] = IterationNode(vertex)
        else:
            node.vertex = vertex
            node.vlist_index = 0

    def find_cycle(self):
        while self._top >= 0:
            top_node = self._node_list[self._top]
            next_vertex = None
            try:
                top_node_vlist = self.graph._vmap[top_node.vertex]
                while next_vertex is None:
                    next_vertex = top_node_vlist[top_node.vlist_index]
                    top_node.vlist_index += 1
            except (KeyError, IndexError):
                self.graph._sink_vertex(top_node.vertex)
                self._pop_node()
                continue

            if next_vertex in self._listed_vertices:
                # We've got a cycle!
                path = [next_vertex]
                while top_node.vertex != next_vertex:
                    path.append(top_node.vertex)
                    self._pop_node()
                    top_node = self._node_list[self._top]
                top_node.vlist_index -= 1
                path.reverse()
                return path

            if next_vertex in self.graph._vmap:
                self._push_node(next_vertex)


class BondMatcher:
    """
    Can generate deals when loaded with bonds.

    The minial meaningful amount is passed to the constructor.
    >>> s = BondMatcher(100)

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

    Start the matcher and try to find a deal:
    >>> s.start()
    >>> path, amount = s.find_deal()
    >>> sorted(path)
    [1, 2, 3]
    >>> amount
    120
    
    All bond amounts were decremented by 120. As a result two of them
    became void because their remaining amount is less than 100:
    >>> s._bonds
    {(3, 1): 130}

    Try to find a deal again:
    >>> s.find_deal()
    """
    
    def __init__(self, min_amount):
        assert (min_amount > 0)
        self._min_amount = min_amount
        self._bonds = {}
        self._graph = None
        self._finder = None
        self._is_started = False

    def register_bond(self, u, v, amount):
        if self._is_started:
            raise Exception('can not register bonds after started')
        elif amount >= self._min_amount:
            self._bonds[(u, v)] = amount
        else:
            self._bonds.pop((u, v), None)

    def start(self):
        if self._is_started:
            raise Exception('the bond matcher is already started')
        self._graph = Digraph()
        for arc in self._bonds:
            self._graph.add_arc(*arc)
        self._finder = CycleFinder(self._graph)
        self._is_started = True

    def find_deal(self):
        path = self._finder.find_cycle()
        if path:
            amount, updated_bonds = self._calc_cycle(path)
            for bond in updated_bonds:
                self._update_bond(*bond)
            return path, amount

    def _update_bond(self, u, v, amount):
        if amount >= self._min_amount:
            self._bonds[(u, v)] = amount
        else:
            self._bonds.pop((u, v), None)
            self._graph.remove_arc(u, v)

    def _calc_cycle(self, path):
        arcs = [(path[i-1], path[i]) for i in range(len(path))]        
        amount = min(self._bonds[a] for a in arcs)
        bonds = [(a[0], a[1], self._bonds[a] - amount) for a in arcs]
        return amount, bonds


def _test_bond_matcher(trader_count, bond_count):
    """
    This function tests the whole module.

    >>> deal_count, amount, time = _test_bond_matcher(10000, 50000)
    >>> deal_count > 5000
    True
    >>> amount > 1e6
    True
    """
    import random, time

    product_count = trader_count // 10
    sellers_ratio = 0.1
    avg_sell_amount = 100 * 1 / sellers_ratio
    avg_buy_amount = sellers_ratio * avg_sell_amount
    locality_distance = min(trader_count, 10000)

    random.seed(1)
    lambd_sell = 1 / avg_sell_amount
    lambd_buy = 1 / avg_buy_amount
    trader_list = [(i, 0) for i in xrange(1, trader_count+1)]
    producer_list = []
    for i in xrange(1, product_count+1):
        producer_list.append((random.randrange(1, trader_count+1), i))

    bond_list = []
    while len(bond_list) < bond_count:
        producer = random.choice(producer_list)
        trader_list_index = (
            producer[0] - 1 + random.randrange(locality_distance+1)
            ) % trader_count
        trader = trader_list[trader_list_index]
        if random.random() < sellers_ratio:
            amount = int(random.expovariate(lambd_sell))
            buyer, seller = producer, trader  # the switch is 2x slower!
        else:
            amount = int(random.expovariate(lambd_buy))
            buyer, seller = trader, producer
        bond_list.append((pair2str(*buyer), pair2str(*seller), amount))

    zero_time = time.time()
    m = BondMatcher(1)
    for b in bond_list:
        m.register_bond(*b)
    m.start()
    performed_deals = 0
    cleared_amount = 0
    while True:
        deal = m.find_deal()
        if not deal:
            break
        performed_deals += 1
        cleared_amount += len(deal[0]) * deal[1]

    return performed_deals, cleared_amount, time.time() - zero_time


if __name__ == '__main__':
    import doctest
    doctest.testmod()

