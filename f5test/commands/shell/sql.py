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
