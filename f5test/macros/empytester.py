# -*- coding: utf-8 -*-
'''
Created on Aug 31, 2012

@author: jono
'''
from f5test.macros.base import Macro
from f5test.base import Options
from f5test.interfaces.icontrol.em import EMInterface
from f5test.defaults import ADMIN_PASSWORD, ADMIN_USERNAME
import logging
import re
from pprint import pprint


LOG = logging.getLogger(__name__)
__version__ = '1.0'


class EmpyTester(Macro):

    def __init__(self, options, address=None, params=None):
        self.options = Options(options.__dict__)
        self.params = params

        self.icparams = Options(device=self.options.device,
                         address=address, timeout=self.options.timeout,
                         username=self.options.username,
                         password=self.options.password,
                         port=self.options.port)
        self.icparams.debug = 1 if options.verbose else 0

        super(EmpyTester, self).__init__()

    def setup(self):

        with EMInterface(**self.icparams) as emifc:
            ic = emifc.api
            apiname, method = re.split(r'[\./:]{1,2}', self.params[0], 1)

            limited_globals = dict(__builtins__=None)
            #limited_globals = dict()

            params = []
            for param in self.params[1:]:
                param = param.decode('utf-8')

                if '=' in param:
                    name, value = param.split('=', 1)
                    # Convert the command-line arguments to Python objects.
                    try:
                        obj = eval(value, limited_globals)
                        params.append("%s=%s" % (name, obj))
                    except (NameError, SyntaxError):
                        if value.startswith('[') or value.startswith('{'):
                            LOG.warning("Did you forget quotes around %s?", value)
                        params.append("%s=%s" % (name, repr(value)))
                else:
                    try:
                        obj = eval(param, limited_globals)
                        params.append(repr(obj))
                    except (NameError, SyntaxError):
                        if param.startswith('[') or param.startswith('{'):
                            LOG.warning("Did you forget quotes around %s?", param)
                        params.append(repr(param))

            api = ic.get_by_name("%sAPI" % apiname)
            LOG.debug(u"Calling: {2}.{0}({1})".format(method, ', '.join(params),
                                                     apiname))
            x = eval(u"api.{0}({1})".format(method, ','.join(params)),
                     limited_globals, {'api': api})
            pprint(x)


def main():
    import optparse
    import sys

    usage = """%prog [options] <address> <API>.<method> [param]...""" \
    u"""
  Examples:
  %prog 172.27.58.94 -pf5site02 SmtpConfig.smtpConfigGetNames
  %prog 172.27.58.94 -pf5site02 SmtpConfig.smtpConfigSetName /Common/mail.f5net.com
  %prog 172.27.58.94 -pf5site02 Discovery.discoverByAddress '' '' "[{'address':'172.27.58.130', 'username':'a', 'password':'a'}]"
    """

    formatter = optparse.TitledHelpFormatter(indent_increment=2,
                                             max_help_position=60)
    p = optparse.OptionParser(usage=usage, formatter=formatter,
                            version="Empython Tester %s" % __version__
        )
    p.add_option("-v", "--verbose", action="store_true",
                 help="Debug logging")

    p.add_option("-u", "--username", metavar="USERNAME",
                 default=ADMIN_USERNAME, type="string",
                 help="Admin username (default: %s)"
                 % ADMIN_USERNAME)
    p.add_option("-p", "--password", metavar="PASSWORD",
                 default=ADMIN_PASSWORD, type="string",
                 help="Admin password (default: %s)"
                 % ADMIN_PASSWORD)

    p.add_option("", "--port", metavar="INTEGER", type="int", default=443,
                 help="SSL Port (default: 443)")
    p.add_option("-t", "--timeout", metavar="SECONDS", type="int", default=60,
                 help="Timeout (default: 60)")
    p.add_option("-s", "--session", metavar="INTEGER", type="int",
                 help="Session identifier for 11.0+ devices")

    options, args = p.parse_args()

    if options.verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO
        logging.getLogger('f5test').setLevel(logging.INFO)
        logging.getLogger('f5test.macros').setLevel(logging.INFO)

    LOG.setLevel(level)
    logging.basicConfig(level=level)

    if len(args) < 2:
        p.print_version()
        p.print_help()
        sys.exit(2)

    cs = EmpyTester(options=options, address=args[0], params=args[1:])
    cs.run()


if __name__ == '__main__':
    main()
