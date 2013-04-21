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
## This file implements finding cycles in digraphs.
##


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


if __name__ == '__main__':
    import doctest
    doctest.testmod()
