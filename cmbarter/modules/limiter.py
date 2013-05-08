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
## This file implements a simple request limiter used for DoS attack
## prevention.
##
from __future__ import with_statement
import time, os
from fcntl import lockf, LOCK_EX
from random import random


O_BINARY = getattr(os, 'O_BINARY', 0)


class Limiter:
    """Limits the number or allowed requests per second.

    Uses a file to keep track of the number of recently allowed
    requests, so as to determine if the next request should be allowed
    or not.
    """

    def __init__(self, filename, max_per_second, max_burst=0.0, log_ratio=None):

        # "max_burst" is the number of consecutive requests that will
        # be allowed, no matter how fast they come.
        assert max_per_second > 0 and max_burst >= 0

        if log_ratio is None:
            log_ratio = 16.0 / (16.0 + max_burst)
        else:
            assert 0.0 < log_ratio <= 1.0

        self.filename = filename
        self.max_per_second = float(max_per_second)
        self.max_burst = float(max_burst)
        self.log_ratio = float(log_ratio)
        self._count_increment = 1.0 / self.log_ratio
        self._count_limit = max_burst + 5.0 * max_per_second


    def allow_request(self):
        """Return True if the request should be allowed, False otherwise."""

        fd = os.open(self.filename, os.O_CREAT | os.O_RDONLY | O_BINARY, 0644)
        with os.fdopen(fd, 'rb') as f:
            curr_count, curr_time = self._read_from_file(f)

        if curr_count > self.max_burst:
            return False
        elif random() < self.log_ratio:
            # Only "self.log_ratio" of the permitted requests are
            # logged, so as to avoid unnecessary file writes.
            self._log_request()

        return True


    def _log_request(self):
        fd = os.open(self.filename, os.O_CREAT | os.O_RDWR | O_BINARY, 0644)
        with os.fdopen(fd, 'r+b') as f:
            lockf(f, LOCK_EX)
            curr_count, curr_time = self._read_from_file(f)

            # Override the old content of the file:
            f.seek(0)
            f.write("%.1f@%.3f" % (curr_count + self._count_increment, curr_time))
            f.truncate()


    def _read_from_file(self, f):
        l = f.read().split('@')
        try:
            if len(l) != 2:
                raise ValueError
            c, t = float(l[0]), float(l[1])
        except ValueError:
            c, t = 0.0, 0.0

        curr_time = time.time()

        # We have to make sure that even when the data from the file
        # is broken, we will not continue to reject requests for more
        # that 5 seconds.
        if t > curr_time + 5.0:
            t = 0.0
        if c > self._count_limit:
            c = self._count_limit

        return max(0.0, c - self.max_per_second * (curr_time - t)), curr_time
