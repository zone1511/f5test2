# -*- coding: utf-8 -*-
'''
Created on Jan 23, 2012

@author: jono
'''
from f5test.macros.base import Macro
from f5test.base import Options
from f5test.interfaces.icontrol import IcontrolInterface
from f5test.defaults import ADMIN_PASSWORD, ADMIN_USERNAME
from f5test.utils.parsers.python_arguments import parser
import logging
import re


LOG = logging.getLogger(__name__)
__version__ = '1.1'


class Ictester(Macro):

    def __init__(self, options, method, address=None, params=None):
        self.options = Options(options)
        self.method = method
        if isinstance(params, basestring):
            self.params = []
            if params.strip():
                for name, value in parser(params):
                    self.params.append("%s=%r" % (name, value))
        else:
            self.params = params

        self.icparams = Options(device=self.options.device,
                         address=address, timeout=self.options.timeout,
                         username=self.options.username,
                         password=self.options.password,
                         port=self.options.port)
        self.icparams.debug = 1 if options.verbose else 0

        super(Ictester, self).__init__()

    def setup(self):
        with IcontrolInterface(**self.icparams) as icifc:
            if self.options.session:
                icifc.set_session(self.options.session)

            ic = icifc.api
            method = re.sub(r'[\./:]{1,2}', r'.', self.method)

            limited_globals = dict(__builtins__={'True': True,
                                                 'False': False,
                                                 'None': None})

            params = []
            for param in self.params:
                param = param.decode('utf-8')
                name, value = param.split('=', 1)
                # Convert the command-line arguments to Python objects.
                try:
                    obj = eval(value, limited_globals)
                    params.append("%s=%r" % (name, obj))
                except (NameError, SyntaxError) as e:
                    LOG.debug(e)
                    if value.startswith('[') or value.startswith('{'):
                        LOG.warning("Did you forget quotes around %s?", value)
                    params.append("%s=%s" % (name, repr(value)))

            LOG.debug(u"Calling: {0}({1})".format(method, ', '.join(params)))
            x = eval(u"ic.{0}({1})".format(method, ','.join(params)),
                     limited_globals, {'ic': ic})
            # print "--- RETURN ---"
            if self.options.yaml:
                import yaml
                result = yaml.safe_dump(x, default_flow_style=False, indent=4,
                                     allow_unicode=True)
            elif self.options.json:
                import json
                result = json.dumps(x, sort_keys=True, indent=4,
                                 ensure_ascii=False)
            else:
                import pprint
                result = pprint.pformat(x)

            return result


def main():
    import optparse
    import sys

    usage = """%prog [options] <address> <method> [param]...""" \
    u"""

  SDK Help: http://172.27.32.101/iControl-11.2.0/sdk/api_reference/iControl.html

  Examples:
  %prog 172.27.58.94 System.SystemInfo.get_version
  %prog 172.27.58.94 Management.KeyCertificate.get_certificate_list mode=MANAGEMENT_MODE_DEFAULT -y
  %prog 172.27.58.94 System.Services.set_service services="['SERVICE_BIG3D']" service_action=SERVICE_ACTION_RESTART
  %prog 172.27.58.94 Management.Device.set_comment devices='["device-172.27.58.94"]' comments='[u"UTF-8 \\"Ionuţ\\""]'"""

    formatter = optparse.TitledHelpFormatter(indent_increment=2,
                                             max_help_position=60)
    p = optparse.OptionParser(usage=usage, formatter=formatter,
                            version="iControl Tester %s" % __version__
        )
    p.add_option("-v", "--verbose", action="store_true",
                 help="Debug logging")
    p.add_option("-j", "--json", action="store_true",
                 help="JSON output")
    p.add_option("-y", "--yaml", action="store_true",
                 help="YAML output")

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

    cs = Ictester(options=options, method=args[1], address=args[0],
                  params=args[2:])
    print cs.run()

if __name__ == '__main__':
    main()
