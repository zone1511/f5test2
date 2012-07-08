#!/usr/bin/env python
from f5test.macros.base import Macro
from f5test.base import Options
from f5test.interfaces.config import ConfigInterface
from f5test.interfaces.ssh import SSHInterface
from f5test.defaults import ROOT_PASSWORD, ROOT_USERNAME
import logging


LOG = logging.getLogger(__name__)
__version__ = '0.1'


class KeySwap(Macro):

    def __init__(self, options, address=None):
        self.options = Options(options.__dict__)

        if self.options.device:
            self.address = ConfigInterface().get_device_address(options.device)
        else:
            self.address = address

        LOG.info('Doing: %s', self.address)
        super(KeySwap, self).__init__()

    def setup(self):
        with SSHInterface(device=self.options.device,
                          address=self.address, timeout=self.options.timeout,
                          username=self.options.username,
                          password=self.options.password,
                          port=self.options.port) as ssh:
            return ssh.api.exchange_key()


def main():
    import optparse
    import sys

    usage = """%prog [options] <address>"""

    formatter = optparse.TitledHelpFormatter(indent_increment=2, 
                                             max_help_position=60)
    p = optparse.OptionParser(usage=usage, formatter=formatter,
                            version="SSH Key Exchange Tool v%s" % __version__
        )
    p.add_option("-v", "--verbose", action="store_true",
                 help="Debug messages")
    
    p.add_option("-u", "--username", metavar="USERNAME",
                 default=ROOT_USERNAME, type="string",
                 help="An user with root rights (default: %s)"
                 % ROOT_USERNAME)
    p.add_option("-p", "--password", metavar="PASSWORD",
                 default=ROOT_PASSWORD, type="string",
                 help="An user with root rights (default: %s)"
                 % ROOT_PASSWORD)
    
    p.add_option("", "--port", metavar="INTEGER", type="int", default=22,
                 help="SSH Port (default: 22)")
    p.add_option("-t", "--timeout", metavar="TIMEOUT", type="int", default=60,
                 help="Timeout. (default: 60)")

    options, args = p.parse_args()

    if options.verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO
        logging.getLogger('paramiko.transport').setLevel(logging.ERROR)
        logging.getLogger('f5test').setLevel(logging.ERROR)
        logging.getLogger('f5test.macros').setLevel(logging.INFO)

    LOG.setLevel(level)
    logging.basicConfig(level=level)
    
    if not args:
        p.print_version()
        p.print_help()
        sys.exit(2)
    
    cs = KeySwap(options=options, address=args[0])
    cs.run()


if __name__ == '__main__':
    main()
