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
from contextlib import contextmanager
from functools import wraps
import time, threading, collections

# Try to import psycopg2. If not possible, try psycopg2cffi.
try:
    import psycopg2
except ImportError:
    try:
        from psycopg2cffi import compat
    except ImportError:
        pass
    else:
        compat.register()
    import psycopg2

import psycopg2.extensions
from psycopg2.extras import DictCursor, NamedTupleCursor
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from psycopg2.errorcodes import (SERIALIZATION_FAILURE, DEADLOCK_DETECTED,
                                 RAISE_EXCEPTION)
psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
psycopg2.extensions.register_type(psycopg2.extensions.UNICODEARRAY)


def _connect(dsn, autocommit=False):
    o = psycopg2.connect(dsn)
    try:
        o.set_client_encoding('UTF8')
        if autocommit:
            o.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    except:
        o.close()
        raise
    else:
        return o


def _compose_select(kwargs, table):
    # This function removes "__return" and "__order_by" keys from the
    # received "kwargs" dictionary. This side effect is ugly, but
    # turns out to be useful. This applies to "_compose_insert" also.
    columns = kwargs.pop('__return', '*')
    order = kwargs.pop('__order_by', '')
    if order:
        order = ' ORDER BY ' + order
    predicate = ' AND '.join(
        ['"{0}"=%s'.format(k.replace('"', '""')) for k in kwargs.keys()])
    if predicate:
        predicate = ' WHERE ' + predicate
    query = 'SELECT %s FROM "%s"%s%s' % (
        columns, table.replace('"', '""'), predicate, order)
    return query, list(kwargs.values())


def _compose_insert(kwargs, table):
    returning = kwargs.pop('__return', '')
    if returning:
        returning = ' RETURNING ' + returning
    if kwargs:
        columns = ','.join(
            ['"{0}"'.format(k.replace('"', '""')) for k in kwargs.keys()])
        placeholders = ','.join(len(kwargs) * ['%s'])
        query = 'INSERT INTO "%s" (%s) VALUES (%s)%s' % (
            table.replace('"', '""'), columns, placeholders, returning)
    else:
        query = 'INSERT INTO "%s" DEFAULT VALUES%s' % (
            table.replace('"', '""'), returning)
    return query, list(kwargs.values())


def _compose_delete(pkey, table):
    predicate = ' AND '.join(
        ['"{0}"=%s'.format(k.replace('"', '""')) for k in pkey.keys()])
    query = 'DELETE FROM "%s" WHERE %s' % (
        table.replace('"', '""'), predicate)
    return query, list(pkey.values())


def _compose_update(pkey, fields, table):
    field_setters = ','.join(
        ['"{0}"=%s'.format(k.replace('"', '""')) for k in fields.keys()])
    predicate = ' AND '.join(
        ['"{0}"=%s'.format(k.replace('"', '""')) for k in pkey.keys()])
    if predicate:
        predicate = ' WHERE ' + predicate
    query = 'UPDATE "%s" SET %s%s' % (
        table.replace('"', '""'), field_setters, predicate)
    return query, list(fields.values()) + list(pkey.values())


def _pick_one_row_at_most(rows):
    if len(rows) == 1:
        row = rows[0]
        if len(row) == 1:
            return row[0]
        elif len(row) == 0:
            return None
        else:
            return row
    elif len(rows) == 0:
        return None
    else:
        raise MultipleRowsError()


class MultipleRowsError(Exception):
    """A single row was expected, but multiple were encountered."""


class RowUpdater(collections.MutableMapping):
    """A mutable dict-like object that knows which row it comes from."""

    def __init__(self, database, table, primary_key, fields):
        object.__setattr__(self, '_database', database)
        object.__setattr__(self, '_table', table)
        object.__setattr__(self, '_primary_key', primary_key)
        object.__setattr__(self, '_fields', fields)
        object.__setattr__(self, '_updated_fields', {})

    def __getitem__(self, key):
        return self._fields[key]

    def __setitem__(self, key, value):
        self._updated_fields[key] = self._fields[key] = value

    def __delitem__(self, key):
        del self._fields[key]
        self._updated_fields.pop(key, None)

    def __getattr__(self, name):
        return self[name]

    def __setattr__(self, name, value):
        self[name] = value

    def __iter__(self):
        return iter(self._fields)

    def __len__(self):
        return len(self._fields)

    def __str__(self):
        return str(self._fields)

    def update_row(self):
        if self._updated_fields:
            query, values = _compose_update(
                self._primary_key, self._updated_fields, table=self._table)
            self._database.execute(query, values)
            self._updated_fields.clear()

    def delete_row(self):
        query, values = _compose_delete(self._primary_key, table=self._table)
        self._database.execute(query, values)


class AbstractMapper(object):
    """Implements convenient methods for accessing databases."""

    __prefixes = ['select_', 'insert_', 'callproc_']
    __suffixes = ['_list', '_for_share', '_for_update']

    def execute(self, query, values=[], onerow=False):
        return self.__execute(lambda c: c.execute(query, values), onerow)

    def callproc(self, name, args=[], onerow=False):
        return self.__execute(lambda c: c.callproc(name, args), onerow)

    def __getattr__(self, full_name):
        name, prefix, suffix = self.__decompose_name(full_name)
        method = self.__getattribute__('_%sX%s' % (prefix, suffix))
        return method(name)

    def __decompose_name(self, name):
        for p in self.__prefixes:
            if name.startswith(p):
                prefix = p
                name = name[len(prefix):]
                break
        else:
            prefix = ''
        for s in self.__suffixes:
            if name.endswith(s):
                suffix = s
                name = name[:-len(suffix)]
                break
        else:
            suffix = ''
        return name, prefix, suffix

    def __execute(self, perform_cursor_action, onerow):
        o = self._acquire_connection()
        try:
            c = self._create_cursor(o)
            perform_cursor_action(c)
            try:
                rows = c.fetchall()
            except psycopg2.Error:
                rows = []
            c.close()
        finally:
            self._release_connection(o)
        return _pick_one_row_at_most(rows) if onerow else rows

    def _X(self, name):
        return lambda *args : self.callproc(name, args, onerow=True)        

    def _X_list(self, name):
        return lambda *args : self.callproc(name, args)

    _callproc_X = _X

    _callproc_X_list = _X_list
        
    def _select_X(self, name):
        def f(**kwargs):
            query, values = _compose_select(kwargs, table=name)
            return self.execute(query, values, onerow=True)
        return f

    def _select_X_list(self, name):
        def f(**kwargs):
            query, values = _compose_select(kwargs, table=name)
            return self.execute(query, values)
        return f

    def _select_X_for_share(self, name):
        def f(**kwargs):
            query, values = _compose_select(kwargs, table=name)
            return self.execute(query + ' FOR SHARE', values, onerow=True)
        return f

    def _insert_X(self, name):
        def f(*args, **kwargs):
            if kwargs:
                query, values = _compose_insert(kwargs, table=name)
                return self.execute(query, values, onerow=True)
            else:
                # Stored procedures named 'insert_X' are allowed
                # because those can be very convenient sometimes.
                return self.callproc('insert_' + name, args, onerow=True)
        return f


class TransactionMapper(AbstractMapper):
    def __init__(self, connection, dictrows):
        self.__connection = connection
        self.__dictrows = dictrows

    def _acquire_connection(self):
        return self.__connection

    def _release_connection(self, connection):
        assert connection is self.__connection

    def _create_cursor(self, connection):
        return connection.cursor(
            cursor_factory=DictCursor if self.__dictrows else NamedTupleCursor)

    def _select_X_for_update(self, name):
        def f(**kwargs):
            query, values = _compose_select(kwargs, table=name)
            rows = self.execute(query + ' FOR UPDATE', values)
            if len(rows) == 1:
                row = dict(rows[0]) if self.__dictrows else rows[0]._asdict()
                return RowUpdater(self, name, kwargs, row)
            elif len(rows) == 0:
                return None
            else:
                raise MultipleRowsError()
        return f

    def set_asynchronous_commit(self):
        self.execute('SET LOCAL synchronous_commit TO OFF')


#############################################################
#  Public interface:                                        #
#############################################################

__all__ = ['PgError', 'PgIntegrityError', 'Binary', 'Connection', 
           'Database', 'Cursor', 'retry_on_deadlock']


__doc__ =  """A very simple object-relational mapper for PostgreSQL.

    This ORM uses a very minimalistic approach. The general idea is
    that the database schema is defined elsewhere (writing the SQL
    directly, or using some specialized software), and all the
    transactions are implemented either as methods in sub-classes of
    "Database", or as stored procedures. 

    This ORM allows you to very easily: (1) implement complex database
    transactions, (2) call stored procedures, (3) do simple
    queries. For complex queries you should use database views and
    stored procedures that return tables. (This is exactly what they
    were invented for!)

    Here is a quick example:
    >>> from curiousorm import *
    >>> class TestDatabase(Database):
    ...    def create_account(self, balance):
    ...        return self.insert_account(balance=balance, __return='id')
    ...
    ...    def increase_account_balance(self, account_id, amount):
    ...        with self.Transaction():
    ...            account = self.select_account_for_update(id=account_id)
    ...            if account == None:
    ...                raise Exception('wrong account id')
    ...            else:
    ...                account.balance += amount
    ...                account.update_row()
    ...
    ...    def delete_account(self, account_id):
    ...        with self.Transaction():
    ...            account = self.select_account_for_update(id=account_id)
    ...            if account == None:
    ...                raise Exception('wrong account id')
    ...            elif account.balance != 0:
    ...                raise Exception('nonzero account balance')
    ...            else:
    ...                account.delete_row()
    ...        
    >>> db = TestDatabase('dbname=curiousorm_test')
    >>> db.execute('CREATE TABLE account (id serial, balance int)')
    []
    >>> account_id = db.create_account(10)
    >>> db.increase_account_balance(account_id, 100)
    >>> db.select_account_list()
    [Record(id=1, balance=110)]
    >>> a = db.select_account(id=1)
    >>> a.balance
    110
    >>> db.delete_account(1)
    Traceback (most recent call last):
    ...
    Exception: nonzero account balance
    >>> db.callproc_current_database()  # calls a stored procedure
    u'curiousorm_test'
    >>> db.current_database()  # calls the same stored procedure
    u'curiousorm_test'
    >>> db.current_database_list()  # the same, but returns a list instead
    [Record(current_database=u'curiousorm_test')]

    This ORM consists of less than 20KB of very clean, thread-safe
    code, so that it can be reviewed and understood with minimum
    effort. In fact, reading and understanding the code is the
    recommended way of mastering it.
    """


PgError = psycopg2.Error

PgIntegrityError = psycopg2.IntegrityError

Binary = psycopg2.Binary


class Connection(AbstractMapper):
    """A separate database connection, enriched with useful methods."""

    def __init__(self, dsn, dictrows=False):
        self.__connection = _connect(dsn, autocommit=True)
        self.__connection_lock = threading.RLock()
        self.__dictrows = dictrows
        self.__inside_transaction = False

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()

    def _acquire_connection(self):
        self.__connection_lock.acquire()
        return self.__connection

    def _release_connection(self, connection):
        assert connection is self.__connection
        self.__connection_lock.release()

    def _create_cursor(self, connection):
        return connection.cursor(
            cursor_factory=DictCursor if self.__dictrows else NamedTupleCursor)

    def _select_X_for_update(self, name):
        def f(**kwargs):
            query, values = _compose_select(kwargs, table=name)
            query += ' FOR UPDATE' if self.__inside_transaction else ''
            rows = self.execute(query, values)
            if len(rows) == 1:
                row = dict(rows[0]) if self.__dictrows else rows[0]._asdict()
                return RowUpdater(self, name, kwargs, row)
            elif len(rows) == 0:
                return None
            else:
                raise MultipleRowsError()
        return f

    def close(self):
        with self.__connection_lock:
            self.__connection.close()

    @contextmanager
    def Transaction(self):
        self.__connection_lock.acquire()
        assert not self.__inside_transaction, 'transactions can not be nested'
        self.__inside_transaction = True
        trx = TransactionMapper(self.__connection, self.__dictrows)
        try:
            trx.execute('BEGIN')
            yield trx
        except:
            trx.execute('ROLLBACK')
            raise
        else:
            trx.execute('COMMIT')
        finally:
            self.__inside_transaction = False
            self.__connection_lock.release()


class Database(Connection):
    """A shared database connection, enriched with useful methods."""

    __instances_lock = threading.Lock()
    __is_frozen = False

    def __new__(cls, dsn, dictrows=False):
        with Database.__instances_lock:
            attr_name = '_%s__instances' % cls.__name__
            if not hasattr(cls, attr_name):
                setattr(cls, attr_name, {})
            instances = getattr(cls, attr_name)
            if (dsn, dictrows) not in instances:
                instance = object.__new__(cls)
                Connection.__init__(instance, dsn, dictrows)
                instance._Database__is_frozen = True
                instances[(dsn, dictrows)] = instance
        return instances[(dsn, dictrows)]

    def __init__(self, dsn, dictrows=False):
        pass

    def __setattr__(self, key, value):
        if self.__is_frozen and key not in self.__dict__:
            raise TypeError('%r is a frozen instance' % self)
        object.__setattr__(self, key, value)

    def close(self):
        pass


class Cursor:
    """A server-side cursor iterator."""

    def __init__(self, dsn, query, query_params=[], buffer_size=10000, 
                 dictrows=False):
        self._dsn = dsn
        self._query = query
        self._query_params = query_params
        self._buffer_size = buffer_size
        self._dictrows = dictrows
        self._closed = False
        self._connection = _connect(dsn)
        self._cursor = None
        self._buffer = iter([])
        if __debug__:
            self._owning_thread = threading.current_thread()

    def __iter__(self):
        return self

    def __next__(self):
        assert self._owning_thread is threading.current_thread(), \
            "'Cursor' instances can not be shared between threads"
        try:
            return next(self._buffer)
        except StopIteration:
            if self._closed:
                raise
            else:
                self._fetch()
                return next(self._buffer)

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()

    def _create_named_cursor(self):
        c = self._connection.cursor(
            'curiousorm_cursor', 
            cursor_factory=DictCursor if self._dictrows else NamedTupleCursor
            )
        c.arraysize = self._buffer_size
        c.execute(self._query, self._query_params)
        return c

    def _fetch(self):
        if self._cursor is None:
            self._cursor = self._create_named_cursor()
        rows = self._cursor.fetchmany(self._buffer_size)
        if rows:
            self._buffer = iter(rows)
        else:
            self.close()

    next = __next__

    def close(self):
        assert self._owning_thread is threading.current_thread(), \
            "'Cursor' instances can not be shared between threads"
        if not self._closed:
            self._buffer = iter([])
            try:
                self._cursor.close()
            except:
                pass
            self._connection.close()
            self._closed = True


def retry_on_deadlock(action):
    """Function decorator that retries 'action' in case of a deadlock."""

    @wraps(action)
    def f(*args, **kwargs):
        while True:
            try:
                return action(*args, **kwargs)
            except PgError as e:
                error_code = getattr(e, 'pgcode', '')
                if error_code in (SERIALIZATION_FAILURE, DEADLOCK_DETECTED):
                    time.sleep(0.1)
                    continue
                else:
                    raise
    return f
