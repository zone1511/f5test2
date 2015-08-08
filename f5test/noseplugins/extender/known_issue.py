'''
Created on Aug 3, 2015

@author: jono
'''
from nose.plugins.errorclass import ErrorClass, ErrorClassPlugin
from . import ExtendedPlugin


class KnownIssueTest(Exception):
    """Raise this exception to mark a test as deprecated.
    """
    pass


class KnownIssue(ExtendedPlugin, ErrorClassPlugin):
    """
    Installs a DEPRECATED error class for the DeprecatedTest exception. Enabled
    by default.
    """
    enabled = True
    known_issue = ErrorClass(KnownIssueTest,
                             label='KNOWNISSUE',
                             isfailure=True)

    def options(self, parser, env):
        """Register commandline options.
        """
        env_opt = 'NOSE_WITHOUT_KNOWNISSUE'
        parser.add_option('--no-knownissue', action='store_true',
                          dest='noKnownIssue', default=env.get(env_opt, False),
                          help="Disable special handling of KnownIssueTest "
                          "exceptions.")

    def configure(self, options, conf):
        """Configure plugin.
        """
        if not self.can_configure:
            return
        self.conf = conf
        disable = getattr(options, 'noKnownIssue', False)
        if disable:
            self.enabled = False
