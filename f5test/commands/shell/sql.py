"""Mysql query command."""

from .base import SSHCommand, SSHCommandError
from ..base import WaitableCommand
from ...defaults import EM_MYSQL_USERNAME, EM_MYSQL_PASSWORD, F5EM_DB
from ...utils.parsers.xmlsql import parse_xmlsql, parse_xmlsql_row_dict

import logging

LOG = logging.getLogger(__name__) 


class SQLCommandError(SSHCommandError):
    """Thrown when mysql doesn't like the query.""" 
    def __init__(self, query, message):
        self.query = query
        self.message = message

    def __str__(self):
        return "[%s]: %s" % (self.query, self.message)


class SQLProcedureError(SSHCommandError):
    """Thrown when mysql doesn't like the query.""" 
    def __init__(self, error_code, error_string):
        self.error_code = error_code
        self.error_string = error_string

    def __str__(self):
        return "[%s]: %s" % (self.error_code, self.error_string)


query = None
class Query(WaitableCommand, SSHCommand):
    """Run a one-shot SQL query as a parameter to mysql.
    
    >>> list(sql.query('SELECT 1 AS cool'))
    [{u'cool': u'1'}]

    @param query: the SQL query
    @type query: str
    @param database: the database to run against
    @type database: str
    @param sql_username: mysql username
    @type sql_username: str
    @param sql_password: mysql password
    @type sql_password: str
    """
    def __init__(self, query, database=F5EM_DB, sql_username=EM_MYSQL_USERNAME, 
                 sql_password=EM_MYSQL_PASSWORD, *args, **kwargs):
        super(Query, self).__init__(*args, **kwargs)
        self.query = query
        self.database = database
        self.sql_username = sql_username
        self.sql_password = sql_password

    def __repr__(self):
        parent = super(Query, self).__repr__()
        return parent + "(query=%(query)s database=%(database)s " \
               "sql_username=%(sql_username)s sql_password=%(sql_password)s)" % self.__dict__
   
    def setup(self):
        #LOG.info('querying `%s`...', self.query)
        query = self.query.replace('"', r'\"')
        query = query.replace('`', r'\`')
        args = []
        args.append('mysql')
        # -u, --user=name     User for login if not current user.
        args.append('-u%s' % self.sql_username)
        # -p, --password[=name] Password to use when connecting to server.
        if self.sql_password:
            args.append("-p%s" % self.sql_password)
        # -D, --database=name Database to use.
        if self.database:
            args.append('-D %s' % self.database)
        # -B, --batch      Don't use history file. Disable interactive behavior.
        args.append('-B')
        # -X, --xml        Produce XML output.
        args.append('-X')
        # -e, --execute=name  Execute command and quit.
        args.append('-e "%s"' % query)
        
        ret = self.api.run(' '.join(args))
        if not ret.status:
            results = parse_xmlsql(ret.stdout)
            if results is None:
                return []
            #return parse_xmlsql_row_dict(results)
            return list(parse_xmlsql_row_dict(results))
        else:
            LOG.error(ret)
            raise SQLCommandError(query, ret.stderr)


call_routine = None
class CallRoutine(Query):
    """Returns the metrics count calculated live.
    
    @param sp_name: The stored procedure name
    @type sp_name: str
    @param params: Parameters list
    @type params: list
    @param handle_errors: (NOT YET SUPPORTED) If set it the command will throw an exception in 
                          case the SP fails.
    @type handle_errors: bool
    """
    def __init__(self, sp_name, params=None, handle_errors=True, 
                 is_function=False, *args, **kwargs):
        if params is None:
            params = []
        self.sp_name = sp_name
        self.params = params
        self.handle_errors = handle_errors
        self.is_function = is_function
        super(CallRoutine, self).__init__(query=None, *args, **kwargs)

    def setup(self):
        params = []
        for param in self.params:
            if isinstance(param, basestring):
                params.append("'%s'" % param)
            else:
                params.append(param)
        
        if self.is_function:
            self.query = "SELECT %s(%s);" % (self.sp_name, ','.join(params))
            return super(CallRoutine, self).setup()[0].values()[0]
        else:
            error_sql = '' #@UnusedVariable
            if self.handle_errors:
                params.append('@o_error_code')
                params.append('@o_error_string')
                error_sql = 'SELECT @o_error_code, @o_error_string' #@UnusedVariable
            
            self.query = "CALL %s(%s);" % (self.sp_name, ','.join(params))
            #ret = super(CallSp, self).setup()
            #if self.handle_errors:
            #    error = ret[1][0]
            #    if error.o_error_code is not None:
            #        raise SQLProcedureError(error.o_error_code, error.o_error_string)
            #    ret = ret[0]
    
            return super(CallRoutine, self).setup()
