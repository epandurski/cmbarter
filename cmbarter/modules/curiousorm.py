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
## This file implements an extremely simple, but very elegant
## object-relational mapper.
##
from __future__ import with_statement
from contextlib import contextmanager
from functools import wraps
import time, itertools

# Try to import psycopg2. If not possible, try psycopg2cffi.
try:
    import psycopg2
except ImportError:
    from psycopg2cffi import compat
    compat.register()
    import psycopg2

import psycopg2.extensions
from psycopg2.extras import DictCursor
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from psycopg2.errorcodes import SERIALIZATION_FAILURE, DEADLOCK_DETECTED, RAISE_EXCEPTION

psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)

PgError = psycopg2.Error



def Binary(s):
    return psycopg2.Binary(s)



class MultipleRowsError(Exception):
    """A single row was expected but multiple rows had been encountered."""



def _compose_query_from_kargs(kargs, table):
    columns= '*'
    predicate = ''
    order=''
    values = []
    for k in kargs.keys():
        if k == '__order_by':
            order = ' ORDER BY %s' % kargs[k]
        elif k == '__columns':
            columns = kargs[k]
        else:
            cond = '%s=%s' % (k, '%s')
            predicate += (' AND %s' if predicate else ' WHERE %s') % cond
            values.append(kargs[k])
    query = "SELECT %s FROM %s%s%s" % (columns, table, predicate, order)
    return query, values



def _pick_one_row_at_most(rows):
    if len(rows) == 1:
        row = rows[0]
        if len(row) == 1:
            return row.values()[0]
        elif len(row) == 0:
            return None
        else:
            return row
    elif len(rows) == 0:
        return None
    else:
        raise MultipleRowsError()



def _get_cursor_from_connection(connection):
    # The returned cursor object must fetch dict-like records.
    return connection.cursor(cursor_factory=DictCursor)  # This is psycopg2-specific!



class AbstractMapper(object):
    """An extremely simple object-relational mapper.

    This ORM uses a very minimalistic approach.  The general idea is
    that the database schema is defined elsewhere (writing the SQL by
    hand or using some specialized software) and all the transactions
    are implemented as stored procedures.  This ORM just allows you to
    more easily call your stored procedures and do simple queries.

    >>> import curiousorm
    >>> db = curiousorm.Database(dsn='dbname=curiousorm')
    >>> db.clear_all()  # calls a stored procedure
    0
    >>> foo_id = db.put_new_item('foo')  # calls another stored procedure
    >>> l = db.select_table1_list()  # selects all rows of 'table1'.
    >>> l[0]['field1']
    u'foo'
    >>> db.select_table1(id=foo_id)['field1']  # selects a row with a given id.
    u'foo'
    >>> trx = db.start_transaction()
    >>> trx.select_xyz_list()
    Traceback (most recent call last):
        ...
    ProgrammingError: relation "xyz" does not exist
    LINE 1: SELECT * FROM xyz
                          ^
    <BLANKLINE>
    >>> q = trx.complex_query_list()  # calls a stored procedure returning list.
    >>> q[0]['field1']
    u'foo'
    """

    __PREFIXES = ['select_']
    __SUFFIXES = ['_list']


    def execute(self, query, values=[], onerow=False):
        return self.__execute(lambda c: c.execute(query, values), onerow)


    def callproc(self, name, args=[], onerow=False):
        return self.__execute(lambda c: c.callproc(name, args), onerow)


    def cursor(self):
        return _get_cursor_from_connection(self._get_connection())


    def __getattr__(self, full_name):
        name, prefix, suffix = self.__shorten_name(full_name)
        method = getattr(self, '_%sX%s' % (prefix, suffix))
        return lambda *args, **kargs: method(name)(*args, **kargs)


    def __shorten_name(self, name):
        for p in self.__PREFIXES:
            if name.startswith(p):
                prefix = p
                name = name[len(prefix):]
                break
        else:
            prefix = ''
        for s in self.__SUFFIXES:
            if name.endswith(s):
                suffix = s
                name = name[:-len(suffix)]
                break
        else:
            suffix = ''
        return name, prefix, suffix


    def __execute(self, perform_cursor_action, onerow):
        o = self._get_connection()
        try:
            c = _get_cursor_from_connection(o)
            perform_cursor_action(c)
            try:
                rows = c.fetchall()
            except psycopg2.Error:
                rows = []  # the executed command returned no result-set
            c.close()
        except psycopg2.Error:
            o.rollback()  # restores the connection to a proper state
            # The re-raised error must be an instance of PgError and must have "pgcode" and "pgerror" fields.
            raise  # This is psycopg2-specific!
        finally:
            self._release_connection(o)

        return _pick_one_row_at_most(rows) if onerow else rows


    def _X(self, name):
        return lambda *args : self.callproc(name, args, onerow=True)        


    def _X_list(self, name):
        return lambda *args : self.callproc(name, args)
        

    def _select_X(self, name):
        def f(**kargs):
            query, values = _compose_query_from_kargs(kargs, table=name)
            return self.execute(query, values, onerow=True)
        return f


    def _select_X_list(self, name):
        def f(**kargs):
            query, values = _compose_query_from_kargs(kargs, table=name)
            return self.execute(query, values)
        return f



class AbstractConnectionMapper(AbstractMapper):
    """Single connection mapper."""
    
    def __init__(self, o):
        self._connection = o


    def _get_connection(self):
        return self._connection


    def commit(self):
        self._connection.commit()


    def rollback(self):
        self._connection.rollback()



class TransactionMapper(AbstractConnectionMapper):
    """Rich transaction mapper."""
    
    def _release_connection(self, o):
        assert o is self._connection


    def set_asynchronous_commit(self):
        self.execute("SET LOCAL synchronous_commit TO OFF")



class AutocommitMapper(AbstractConnectionMapper):
    """Single connection autocommit mapper."""

    def _release_connection(self, o):
        assert o is self._connection



class SmartcommitMapper(AbstractConnectionMapper):
    """Single connection smartcommit mapper."""

    def _release_connection(self, o):
        assert o is self._connection
        o.commit()


    def start_transaction(self):
        return TransactionMapper(self._connection)


    @contextmanager
    def Transaction(self):
        trx = self.start_transaction()
        try:
            yield trx
        except:
            trx.rollback()
            raise
        else:
            trx.commit()



class AutocommitConnection(AutocommitMapper):
    """Rich autocommit connection object."""

    def __init__(self, dsn):
        AutocommitMapper.__init__(self, connect(dsn, autocommit=True))


    def close(self):
        self._connection.close()



class SmartcommitConnection(SmartcommitMapper):
    """Rich smartcommit connection object."""

    def __init__(self, dsn):
        SmartcommitMapper.__init__(self, connect(dsn))


    def close(self):
        self._connection.close()



_database_connection_pool = {}

class Database(SmartcommitMapper):
    """Rich smartcommit connection object from a database connection pool."""

    def __init__(self, dsn):
        if dsn in _database_connection_pool:
            connection = _database_connection_pool[dsn]
        else:
            connection = _database_connection_pool[dsn] = connect(dsn)
            
        SmartcommitMapper.__init__(self, connection)



def Connection(dsn, autocommit=False):
    return AutocommitConnection(dsn) if autocommit else SmartcommitConnection(dsn)



def connect(dsn, autocommit=False):
    """Return an initialized psycopg2 database connection object."""
    
    o = psycopg2.connect(dsn)
    o.set_client_encoding('UTF8')  # This is psycopg2-specific!
    if autocommit:
        o.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)  # This is psycopg2-specific!
    return o



_cursor_name_generator = ("curiousorm_unnamed_cursor_%i" % i for i in itertools.count(1))

def create_server_side_cursor(connection, name=None):
    """Return a server-side cursor for a given database connection."""

    if name is None:
        name = _cursor_name_generator.next()
    return connection.cursor(name, cursor_factory=DictCursor)  # This is psycopg2-specific!



def retry_transient_errors(action):
    """Keep executing 'action' until a fatal error has occurred."""

    @wraps(action)
    def fn(*args, **kargs):
        while 1:
            try:
                return action(*args, **kargs)
            except PgError, e:
                if getattr(e, 'pgcode', '') in (SERIALIZATION_FAILURE, DEADLOCK_DETECTED):
                    time.sleep(0.1)
                    continue
                else:
                    raise
    return fn



if __name__ == '__main__':
    import doctest
    doctest.testmod()
