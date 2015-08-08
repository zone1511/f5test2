#!/usr/bin/env python
'''
Created on Jan 28, 2015

@author: jwong
'''
from __future__ import absolute_import
from f5test.macros.base import Macro, MacroError
from f5test.interfaces.ssh import SSHInterface
from f5test.interfaces.config import ConfigInterface
from f5test.interfaces.rest.emapi import EmapiInterface, EmapiResourceError
from f5test.commands.shell import WIPE_STORAGE
from f5test.base import Options as O
from f5test.defaults import (ROOT_USERNAME, ROOT_PASSWORD, ADMIN_USERNAME,
                             ADMIN_PASSWORD)
from netaddr import IPAddress, ipv6_full
from f5test.utils.wait import wait_args
from f5test.interfaces.rest.emapi.objects import DeviceResolver
import f5test.commands.shell as SCMD
import logging
import sys
import datetime

__version__ = 1.0

DEFAULT_ROOT_USERNAME = ROOT_USERNAME
DEFAULT_ROOT_PASSWORD = ROOT_PASSWORD
DEFAULT_ADMIN_USERNAME = ADMIN_USERNAME
DEFAULT_ADMIN_PASSWORD = ADMIN_PASSWORD
DEFAULT_TIMEOUT = 180
LICENSE_FILE = '/config/bigip.license'
LOG = logging.getLogger(__name__)


class ScaleCheck(Macro):

    def __init__(self, options, address=None, address_iq=None, *args, **kwargs):
        self.context = O()
        self.options = O(options)

        self.options.setifnone('timeout', DEFAULT_TIMEOUT)
        self.options.setifnone('skip_ping', False)

        if self.options.device:
            self.device = ConfigInterface().get_device(options.device)
            self.address = self.device.address
        else:
            self.device = None
            self.address = address
            self.options.setifnone('username', DEFAULT_ROOT_USERNAME)
            self.options.setifnone('password', DEFAULT_ROOT_PASSWORD)
            self.options.setifnone('admin_username', DEFAULT_ADMIN_USERNAME)
            self.options.setifnone('admin_password', DEFAULT_ADMIN_PASSWORD)

        if self.options.device_biq:
            self.device_biq = ConfigInterface().get_device(options.device_biq)
            self.address_biq = self.device_biq.address
        else:
            self.device_biq = None
            self.address_biq = address_iq
            self.options.setifnone('username_iq', DEFAULT_ROOT_USERNAME)
            self.options.setifnone('password_iq', DEFAULT_ROOT_PASSWORD)

        super(ScaleCheck, self).__init__(*args, **kwargs)

    def prep(self):
        self.sshifc = SSHInterface(device=self.device,
                                   address=self.address,
                                   username=self.options.username,
                                   password=self.options.password,
                                   timeout=self.options.timeout,
                                   port=self.options.ssh_port)
        self.sshifc.open()

        self.sshifc_biq = SSHInterface(device=self.options.device_biq,
                                       address=self.address_biq,
                                       username=self.options.username_iq,
                                       password=self.options.password_iq,
                                       timeout=self.options.timeout,
                                       port=self.options.ssh_port)
        self.sshifc_biq.open()

    def wait_prompt(self):
        return SCMD.ssh.GetPrompt(ifc=self.sshifc)\
                   .run_wait(lambda x: x not in ('INOPERATIVE',),
                             progress_cb=lambda x: 'Still %s...' % x,
                             timeout=self.options.timeout, interval=10)

    def make_context(self):
        ctx = self.context
        ctx.version = SCMD.ssh.get_version(ifc=self.sshifc)
        ctx.status = self.wait_prompt()
        LOG.info('Version: {0.product.to_tmos} {0.version} {0.build}'.format(ctx.version))
        return ctx

    def call(self, command):
        ret = SCMD.ssh.generic(command=command, ifc=self.sshifc)

        if ret and ret.status:
            LOG.warn(ret)
        else:
            LOG.debug(ret)
        return ret

    def clean_storage(self, ctx):
        has_restjavad = None
        with EmapiInterface(device=self.device,
                            username=self.options.admin_username,
                            password=self.options.admin_password,
                            port=self.options.ssl_port,
                            address=self.address) as rstifc:
            try:
                if ctx.version < "bigip 11.5.0":
                    has_restjavad = rstifc.api.get(DeviceResolver.URI)
            except EmapiResourceError:
                LOG.warning("This pre 11.5.0 device hasn't had latest"
                            " REST Framework upgrades")
                pass

        self.call("rm -rf /var/log/rest*")
        self.call("find /var/log -name '*.gz' -exec rm {} \;")
#         # Remove all files that are: blabla.1.blabla or blabla.1
#         self.call("find /var/log -regex '.*[.][1-9].*' -exec rm '{}' \\;")
        self.call(WIPE_STORAGE)

        # Because of a bug where restjavad not knowing about icrd, BZ504333.
        if self.sshifc.version.product.is_bigip:
            self.call("bigstart restart icrd")

        with EmapiInterface(device=self.device,
                            username=self.options.admin_username,
                            password=self.options.admin_password,
                            port=self.options.ssl_port,
                            address=self.address) as rstifc:
            if has_restjavad:
                wait_args(rstifc.api.get, func_args=[DeviceResolver.URI],
                          progress_message="Waiting for restjavad...",
                          timeout=300,
                          timeout_message="restjavad never came back up after {0}s")

    def relicense(self, ctx):
        if ctx.status != 'NO LICENSE':
            license_date = self.call('grep "License end" %s | cut -d: -f2' %
                                     LICENSE_FILE).stdout.strip()
            license_key = self.call('grep "Registration Key" %s | cut -d: -f2' %
                                    LICENSE_FILE).stdout.strip()

            date_format = "%Y%m%d"
            expire_date = datetime.datetime.strptime(license_date, date_format)
            delta = expire_date - datetime.datetime.now()

            if delta > datetime.timedelta(days=15):
                LOG.debug("%s is NOT within 15 days of being expired. "
                          "Expiration date: %s" % (self.device, license_date))
            else:
                LOG.info("Re-licensing %s. Expiration date: %s" %
                         (self.device, license_date))
                ret = self.call('SOAPLicenseClient --verbose --basekey %s' %
                                license_key)
                LOG.debug("SOAPLicenseClient returned: %s", ret)

        else:
            raise MacroError("%s does not have a license. Expect BIG-IP to be "
                             "functional" % self.device)

    def ping_check(self):
        bip_selfips = SCMD.tmsh.list("net self", ifc=self.sshifc)
        self_ips = [x['address'].split('/')[0] for x in bip_selfips.values()]
        for self_ip in self_ips:
            self_ip = IPAddress(self_ip)
            if self_ip.version == 4:
                COMMAND = "ping -c 1 %s" % self_ip.format(ipv6_full)
            elif self_ip.version == 6:
                COMMAND = "ping6 -c 1 %s" % self_ip.format(ipv6_full)
                # TODO: Find out why we can't ping using ipv6 address on Lowell's BIG-IQs
                continue
            else:
                LOG.info("You got some weird IP address that isn't ipv4 or ipv6")

            LOG.info("Ping %s from %s" % (self_ip, self.options.device_biq
                                          if self.options.device_biq
                                          else self.address_biq))
            resp = SCMD.ssh.generic(COMMAND, ifc=self.sshifc_biq)

            if '100% packet loss' in resp.stdout:
                LOG.info("device: %s not reachable" % self.device)
                LOG.debug("device: %s - %s" % (self.device, resp))
                raise Exception("device: %s not reachable" % self.device)

        if self.device:
            self_ip = IPAddress(self.device.get_discover_address())
            LOG.info("Verify given %s from yaml matches one on BIG-IP" % self_ip)
            for a in bip_selfips.values():
                bip_ip = IPAddress(a['address'].split('/')[0])
                if a['vlan'] == 'internal' and \
                   self_ip.version == bip_ip.version:
                    internal_ip = bip_ip
                    break

            if self_ip.format(ipv6_full) != internal_ip.format(ipv6_full):
                LOG.info("Internal mismatch: %s. %s != %s." % (self.device, self_ip,
                                                               internal_ip))
        else:
            LOG.info("This isn't ran as stages so skipping internal selfip check")

    def setup(self):
        ctx = self.make_context()

        LOG.info("Deleting rest logs, *.gz files, and wiping storage")
        if ctx.version.product.is_bigip:
            self.clean_storage(ctx)

        # Check license and re-license if almost expired
        self.relicense(ctx)

        # Check if BIG-IQ can reach BIG-IP
        if not self.options.skip_ping:
            self.ping_check()

        # bigstart restart if BIG-IP is something else other than 'Active'
        LOG.info("State: %s" % ctx.status)
        if ctx.status != 'Active':
            LOG.info("bigstart restart on {0}..".format(self.device if self.device
                                                        else self.address_biq))
            self.call("bigstart restart")
            self.wait_prompt()

    def cleanup(self):
        self.sshifc.close()
        self.sshifc_biq.close()


def main(*args, **kwargs):
    import optparse
    usage = """%prog [options] <address>  <bigiq_address>"""

    formatter = optparse.TitledHelpFormatter(indent_increment=2,
                                             max_help_position=60)
    p = optparse.OptionParser(usage=usage, formatter=formatter,
                              version="Remote BIG-IP Checker v%s" % __version__
                              )
    p.add_option("", "--verbose", action="store_true",
                 help="Debug messages")

    p.add_option("", "--username", metavar="USERNAME",
                 default=DEFAULT_ROOT_USERNAME, type="string",
                 help="root user for BIG_IP (default: %s)"
                 % DEFAULT_ROOT_USERNAME)
    p.add_option("", "--password", metavar="PASSWORD",
                 default=DEFAULT_ROOT_PASSWORD, type="string",
                 help="root password for BIG-IP (default: %s)"
                 % DEFAULT_ROOT_USERNAME)
    p.add_option("", "--admin-username", metavar="USERNAME",
                 default=ADMIN_USERNAME, type="string",
                 help="An user with administrator rights (default: %s)"
                 % ADMIN_USERNAME)
    p.add_option("", "--admin-password", metavar="PASSWORD",
                 default=ADMIN_PASSWORD, type="string",
                 help="An user with administrator rights (default: %s)"
                 % ADMIN_PASSWORD)
    p.add_option("", "--username-iq", metavar="USERNAMEIQ",
                 default=DEFAULT_ROOT_USERNAME, type="string",
                 help="root user for BIG-IQ (default: %s)"
                 % DEFAULT_ROOT_USERNAME)
    p.add_option("", "--password-iq", metavar="PASSWORDIQ",
                 default=DEFAULT_ROOT_PASSWORD, type="string",
                 help="root user for BIG-IQ (default: %s)"
                 % DEFAULT_ROOT_USERNAME)
    p.add_option("", "--ssl-port", metavar="INTEGER", type="int", default=443,
                 help="SSL Port. (default: 443)")
    p.add_option("", "--ssh-port", metavar="INTEGER", type="int", default=22,
                 help="SSH Port. (default: 22)")

    options, args = p.parse_args()

    if options.verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO
        # Shut paramiko's mouth
        logging.getLogger('paramiko.transport').setLevel(logging.ERROR)
        logging.getLogger('f5test').setLevel(logging.ERROR)
        logging.getLogger('f5test.macros').setLevel(logging.INFO)

    LOG.setLevel(level)
    logging.basicConfig(level=level)

    if len(args) < 2:
        p.print_version()
        p.print_help()
        sys.exit(2)  # @UndefinedVariable

    m = ScaleCheck(options, address=args[0], address_iq=args[1])
    m.run()

if __name__ == '__main__':
    main()
