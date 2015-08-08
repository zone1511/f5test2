#!/usr/bin/env python
'''
Created on Feb 10, 2015

@author: jwong
'''
from f5test.macros.base import Macro
from f5test.base import Options
from f5test.interfaces.rest.emapi import EmapiInterface
from f5test.interfaces.ssh import SSHInterface
from f5test.interfaces.config import (DeviceAccess, DeviceCredential,
                                      ADMIN_ROLE, ROOT_ROLE)
from f5test.interfaces.rest.emapi.objects.shared import NetworkDiscover
from f5test.defaults import DEFAULT_PORTS
import f5test.commands.rest as RCMD
import f5test.commands.shell as SCMD
import logging
import netaddr

DEFAULT_DG = RCMD.device.DEFAULT_ALLBIGIQS_GROUP
LOG = logging.getLogger(__name__)
__version__ = '1.0'


class HABigiqMacro(Macro):

    def __init__(self, options, default=None, peers=None):
        self.options = Options(options)
        self.default = default
        self.peers = peers

        super(HABigiqMacro, self).__init__()

    def setup_devices(self, default, peers):
        def convert_device(string):
            default_admin_username = self.options.admin_username
            default_admin_password = self.options.admin_password
            default_root_username = self.options.root_username
            default_root_password = self.options.root_password

            bits = string.split(',')

            if len(bits[0].split(':')) > 1:
                address, discover_address = bits[0].split(':')
            else:
                address, discover_address = bits[0], None
            specs = Options()
            specs['discover address'] = discover_address

            admin_cred = Options()
            root_cred = Options()
            if len(bits) == 1:
                admin_cred.common = DeviceCredential(default_admin_username,
                                                     default_admin_password)
                root_cred.common = DeviceCredential(default_root_username,
                                                    default_root_password)
            elif len(bits) == 3:
                admin_cred.common = DeviceCredential(bits[1], bits[2])
                root_cred.common = DeviceCredential(default_root_username,
                                                    default_root_password)
            elif len(bits) == 5:
                admin_cred.common = DeviceCredential(bits[1], bits[2])
                root_cred.common = DeviceCredential(bits[3], bits[4])
            else:
                raise ValueError('Invalid specs: %s', string)

            creds = {ADMIN_ROLE: admin_cred, ROOT_ROLE: root_cred}
            device = DeviceAccess(address, credentials=creds, specs=specs)

            for spec in self.options.https_ports.split(','):
                if len(spec.split(':')) != 2 and spec:
                    raise ValueError('Invalid https input: %s', spec)

            for spec in self.options.ssh_ports.split(','):
                if len(spec.split(':')) != 2 and spec:
                    raise ValueError('Invalid ssh input: %s', spec)

            def create_port_specs(string):
                ret = dict()
                if string:
                    for x in string.split(','):
                        x = x.strip().split(':')
                        ret.update({x[0]: x[1]})
                return ret

            https_by_address = create_port_specs(self.options.https_ports)
            ssh_by_address = create_port_specs(self.options.ssh_ports)

            device.ports['https'] = https_by_address.get(address,
                                                         DEFAULT_PORTS['https'])
            device.ports['ssh'] = ssh_by_address.get(address,
                                                     DEFAULT_PORTS['ssh'])
            device.alias = "device-%s" % device.address

            return device

        if isinstance(default, basestring):
            self.default = convert_device(default)

        temp = list()
        for peer in peers:
            if isinstance(peer, basestring):
                temp.append(convert_device(peer))

        if temp:
            self.peers = temp

    def setup_ha(self):
        # Setting HA communication address
        for device in [self.default] + self.peers:
            LOG.info("Setting up HA Communication: {}".format(device))
            with EmapiInterface(device=device) as rstifc:
                self_addr = netaddr.IPAddress(device.get_discover_address())
                payload = NetworkDiscover()
                payload.discoveryAddress = self_addr.format(netaddr.
                                                            ipv6_full)
                rstifc.api.put(NetworkDiscover.URI, payload=payload)

        with EmapiInterface(device=self.default) as rstifc:
            if self.options.ha_passive:
                LOG.info("Setting up Active/Passive HA")
                RCMD.system.setup_ha(self.peers, ifc=rstifc)
            else:
                LOG.info("Setting up Active/Active HA")
                RCMD.cloud.setup_ha(self.peers, ifc=rstifc)

        with SSHInterface(device=self.default) as sshifc:
            SCMD.bigiq.ha.wait_ha([self.default] + self.peers,
                                  timeout=self.options.timeout, ifc=sshifc)

    def reset_all(self):
        for device in [self.default] + self.peers:
            with SSHInterface(device=device) as sshifc:
                LOG.info('Wiping storage on {0}'.format(device))
                SCMD.ssh.generic(SCMD.bigiq.ha.HA_WIPE_COMMAND, ifc=sshifc)

        with EmapiInterface(device=device) as rstifc:
            RCMD.system.wait_restjavad([self.default] + self.peers, ifc=rstifc)

    def setup(self):
        self.setup_devices(self.default, self.peers)

        if self.options.reset:
            # Delete AA HA
            self.reset_all()

        else:
            # Set AA HA
            self.setup_ha()


def main():
    import optparse
    import sys

    usage = """%prog [options] <default address>[,<default admin username>,<default admin password>[,<default root username>, <default root password>]]] peer1 [peer2]...\n
    <peer address>[:discover address][,<peer admin username>,<peer admin password>[,<peer root username>, <peer root password>]]]"""

    formatter = optparse.TitledHelpFormatter(indent_increment=2,
                                             max_help_position=60)
    p = optparse.OptionParser(usage=usage, formatter=formatter,
                              version="BIG-IQ Active-Active Configurator: v%s" % __version__
                              )
    p.add_option("-v", "--verbose", action="store_true",
                 help="Debug messages")

    p.add_option("--admin-username", default='admin', type="string",
                 help="Default username. (default: admin)")
    p.add_option("--admin-password", default='admin', type="string",
                 help="Default password. (default: admin)")
    p.add_option("--root-username", default='root', type="string",
                 help="Default username. (default: root)")
    p.add_option("--root-password", default='default', type="string",
                 help="Default password. (default: default)")
    p.add_option("-r", "--reset", action="store_true", default=False,
                 help="Deletes HA by wiping storage on all BIG-IQs.")

    p.add_option("-t", "--timeout", metavar="TIMEOUT", type="int", default=180,
                 help="Timeout. (default: 60)")
    p.add_option("--https-ports", type="string", default='',
                 help="Usage: '<ip1>:<port number>, <ip2>:<port number>'")
    p.add_option("--ssh-ports", type="string", default='',
                 help="Usage: '<ip1>:<port number>, <ip2>:<port number>'")

    p.add_option("", "--ha-passive",
                 action="store_true",
                 help="Active/Passive (4.6.0+) Active/Standby (pre-4.6.0) HA?")

    options, args = p.parse_args()

    if options.verbose:
        level = logging.DEBUG
        LOG.setLevel(level)
        logging.basicConfig(level=level)

    if not args or not args[1:]:
        p.print_version()
        p.print_help()
        sys.exit(2)

    default = args[0]

    peers = []
    for spec in args[1:]:
        peers.append(spec)

    cs = HABigiqMacro(options=options, default=default, peers=peers)
    cs.run()


if __name__ == '__main__':
    main()
