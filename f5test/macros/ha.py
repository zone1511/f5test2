#!/usr/bin/env python
'''
Created on May 31, 2011

@author: jono
'''
from f5test.macros.base import Macro
from f5test.base import Options
from f5test.interfaces.icontrol import IcontrolInterface
import f5test.commands.icontrol as ICMD
from f5test.interfaces.config import DeviceAccess, DeviceCredential, ADMIN_ROLE
from f5test.defaults import DEFAULT_PORTS
from f5test.utils.wait import wait
from netaddr import IPAddress, IPNetwork
import logging
import uuid


DEFAULT_DG = '/Common/f5test.ha-dg'
DEFAULT_DG_TYPE = 'DGT_FAILOVER'
RESERVED_GROUPS = ('gtm', 'device_trust_group')
DEFAULT_TG = 'traffic-group-1'
LOG = logging.getLogger(__name__)
__version__ = '0.2'


class FailoverMacro(Macro):

    def __init__(self, options, authorities=None, peers=None, groups=None):
        self.options = Options(options)
        self.authorities_spec = list(authorities or [])
        self.peers_spec = list(peers or [])
        self.cas = []
        self.peers = []
        self.groups_specs = groups or []

        super(FailoverMacro, self).__init__()

    def set_devices(self):
        default_username = self.options.username
        default_password = self.options.password
        self.cas = []
        self.peers = []

        def parse_spec(specs, alias=None):
            bits = specs.split('@', 1)
            groups = None
            if len(bits) > 1:
                groups = set(bits[1].split(','))
            bits = bits[0].split(',')

            if len(bits[0].split(':')) > 1:
                address, port = bits[0].split(':')
            else:
                address, port = bits[0], DEFAULT_PORTS['https']

            cred = Options()
            if len(bits) == 1:
                cred.common = DeviceCredential(default_username, default_password)
                device = DeviceAccess(address, {ADMIN_ROLE: cred})
            elif len(bits) == 2:
                cred.common = DeviceCredential(default_username, bits[1])
                device = DeviceAccess(address, {ADMIN_ROLE: cred})
            elif len(bits) == 3:
                cred.common = DeviceCredential(bits[1], bits[2])
                device = DeviceAccess(address, {ADMIN_ROLE: cred})
            else:
                raise ValueError('Invalid specs: %s', specs)

            device.ports['https'] = port
            device.set_groups(groups)
            return device

        for (src, dst) in ((self.authorities_spec, self.cas),
                           (self.peers_spec, self.peers)):
            count = 0
            for specs in src:
                count += 1
                if isinstance(specs, basestring):
                    device = parse_spec(specs)
                else:
                    device = specs

                if device.ports['https'] != DEFAULT_PORTS['https']:
                    device.alias = "device-{0}-{1}".format(device.address,
                                                           device.ports['https'])
                else:
                    device.alias = "device-%s" % device.address

                if not device.groups:
                    device.set_groups(DEFAULT_DG)

                dst.append(device)

    def set_groups(self):
        groups = {}
        for spec in self.groups_specs or [DEFAULT_DG]:
            if isinstance(self.groups_specs, (list, tuple, set)):
                bits = spec.split(':')
                if len(bits) > 1:
                    if bits[1] in ('s', 'so', 'config-sync'):
                        groups[bits[0]] = 'DGT_SYNC_ONLY'
                    else:
                        groups[bits[0]] = 'DGT_FAILOVER'
                else:
                    groups[bits[0]] = 'DGT_FAILOVER'
            else:
                # Assume it is a dict
                groups[spec] = self.groups_specs[spec]
        self.groups = groups

    def do_reset_all(self):
        devices = self.cas + self.peers
        groups = self.groups.keys()

        for device in devices:
            cred = device.get_admin_creds()
            with IcontrolInterface(address=device.address, username=cred.username,
                                   password=cred.password,
                                   port=device.ports['https']) as icifc:
                ic = icifc.api
                v = ICMD.system.get_version(ifc=icifc)
                if v.product.is_bigip and v < 'bigip 11.0':
                    raise NotImplemented('Not working for < 11.0')

                # In 11.2.0 the device cannot be renamed while it's in the Trust
                v = icifc.version
                if v.product.is_bigip and v >= 'bigip 11.2.0' or \
                   v.product.is_em and v >= 'em 3.0.0' or \
                   v.product.is_bigiq:
                    device_name = ic.Management.Device.get_local_device()
                else:
                    device_name = uuid.uuid4().hex

                LOG.info('Resetting trust on %s...', device.alias)
                ic.Management.Trust.reset_all(device_object_name=device_name,
                                              keep_current_authority='false',
                                              authority_cert='',
                                              authority_key='')

                dgs = ic.Management.DeviceGroup.get_list()
                for dg in groups:
                    dg = '/Common/%s' % dg
                    if dg in dgs:
                        LOG.info('Removing %s from %s...', dg, device.alias)
                        ic.Management.DeviceGroup.remove_all_devices(device_groups=[dg])
                        ic.Management.DeviceGroup.delete_device_group(device_groups=[dg])

    def do_BZ364939(self):
        devices = self.cas + self.peers
        devices.reverse()

        for device in devices:
            cred = device.get_admin_creds()
            with IcontrolInterface(address=device.address, username=cred.username,
                                   password=cred.password,
                                   port=device.ports['https']) as icifc:

                v = icifc.version
                if v.product.is_bigip and v >= 'bigip 11.2.0' or \
                   v.product.is_em and v >= 'em 3.0.0' or \
                   v.product.is_bigiq:
                    continue

                #if icifc.version.product.is_bigip and icifc.version < 'bigip 11.2':
                ic = icifc.api
                LOG.info('Working around BZ364939 on %s...', device.alias)
                ic.System.Services.set_service(services=['SERVICE_TMM'],
                                               service_action='SERVICE_ACTION_RESTART')
                wait(ic.System.Failover.get_failover_state,
                     lambda x: x != 'FAILOVER_STATE_OFFLINE')

    def do_prep_cmi(self, icifc, device, ipv6=False):
        ic = icifc.api
        selfips = ic.Networking.SelfIPV2.get_list()
        addresses = ic.Networking.SelfIPV2.get_address(self_ips=selfips)
        states = ic.Networking.SelfIPV2.get_floating_state(self_ips=selfips)
        vlans = ic.Networking.SelfIPV2.get_vlan(self_ips=selfips)
        selfips = [(x[3], x[1]) for x in zip(selfips, addresses, states,
                                             vlans)
                   if IPAddress(x[1]).version == (6 if ipv6 else 4) and
                      x[2] == 'STATE_DISABLED']

        vlan_ip_map = dict(selfips)
        LOG.debug("VLAN map: %s", vlan_ip_map)
        internal_selfip = vlan_ip_map['/Common/internal']

        LOG.info('Resetting trust on %s...', device.alias)
        ic.Management.Trust.reset_all(device_object_name=device.alias,
                                      keep_current_authority='false',
                                      authority_cert='',
                                      authority_key='')

        # XXX: Why does it remember the old device name?!
        # Because a check for duplicate device name is not done here.
#        LOG.info('Resetting trust (again) on %s...', device)
#        ic.Management.Trust.reset_all(device_object_name=device.alias,
#                                      keep_current_authority='false',
#                                      authority_cert='',
#                                      authority_key='')

        LOG.info('Setting config sync address on %s to %s...', device.alias,
                 internal_selfip)
        ic.Management.Device.set_configsync_address(devices=[device.alias],
                                                    addresses=[internal_selfip])

        LOG.info('Setting multicast failover on %s...', device.alias)
        ic.Management.Device.set_multicast_address(devices=[device.alias],
                                                   addresses=[dict(interface_name='eth0',
                                                                  address=dict(address='224.0.0.245',
                                                                               port=62960)
                                                                  )]
                                                   )

        LOG.info('Setting unicast failover on %s...', device.alias)
        address = dict(address=icifc.address, port=1026)
        ic.Management.Device.set_unicast_addresses(devices=[device.alias],
                                                   addresses=[[dict(effective=address,
                                                               source=address)]])

        LOG.info('Setting primary mirror address on %s to %s...', device.alias,
                 internal_selfip)
        ic.Management.Device.set_primary_mirror_address(devices=[device.alias],
                                                        addresses=[internal_selfip])

        if vlan_ip_map.get('/Common/external'):
            external_selfip = vlan_ip_map['/Common/external']
            LOG.info('Setting secondary mirror address on %s to %s...',
                     device.alias, external_selfip)
            ic.Management.Device.set_secondary_mirror_address(devices=[device.alias],
                                                              addresses=[external_selfip])

    # TODO: optimize to work with multiple groups at once.
    def do_prep_dgs(self, icifc, device, groups):
        ic = icifc.api
        dgs = ic.Management.DeviceGroup.get_list()

        for reserved_group in RESERVED_GROUPS:
            if '/Common/%s' % reserved_group in dgs:
                dgs.remove('/Common/%s' % reserved_group)

        if dgs:
            LOG.info('Removing groups %s on %s...', dgs, device.alias)
            ic.Management.DeviceGroup.remove_all_devices(device_groups=dgs)
            ic.Management.DeviceGroup.delete_device_group(device_groups=dgs)

        for group_name, group_type in groups.items():
            LOG.info('Creating %s on %s...', group_name, device.alias)
            ic.Management.DeviceGroup.create(device_groups=[group_name],
                                                 types=[group_type])
            if group_type == 'DGT_FAILOVER':
                LOG.info('Enabling failover on %s...', group_name)
                ic.Management.DeviceGroup.set_network_failover_enabled_state(device_groups=[group_name],
                                                                                 states=['STATE_ENABLED'])
            elif group_type == 'DGT_SYNC_ONLY':
                LOG.info('Enabling auto-sync on %s...', group_name)
                ic.Management.DeviceGroup.set_autosync_enabled_state(device_groups=[group_name],
                                                                         states=['STATE_ENABLED'])

    def do_get_active(self):
        device_accesses = self.cas + self.peers
        devices_map = dict(map(lambda x: (x.address, x), device_accesses))

        cred = device_accesses[0].get_admin_creds()
        with IcontrolInterface(address=device_accesses[0].address,
                               username=cred.username,
                               password=cred.password,
                               port=device_accesses[0].ports['https']) as icifc:
            ic = icifc.api
            devices = ic.Management.Device.get_list()
            fostates = ic.Management.Device.get_failover_state(devices=devices)
            mgmtaddrs = ic.Management.Device.get_management_address(devices=devices)

        trios = map(lambda x: (devices_map.get(x[2]), x[1], x[0]), zip(devices,
                                                                       fostates,
                                                                       mgmtaddrs))
        LOG.debug(trios)
        active_devices = list(filter(lambda x: x[1] == 'HA_STATE_ACTIVE', trios))
        return active_devices

    def do_config_sync(self):
        groups = self.groups.keys()

        # Wait for at least one Active device.
        active_devices = wait(self.do_get_active, timeout=30, interval=2)
        # Will initiate config sync only from the first Active device.
        first_active_device = active_devices[0]
        LOG.info("Doing Config Sync to group %s...", groups)

        cred = first_active_device[0].get_admin_creds()
        with IcontrolInterface(address=first_active_device[0].address,
                               username=cred.username,
                               password=cred.password,
                               port=first_active_device[0].ports['https']) as icifc:
            ic = icifc.api
            for dg in groups:
                ic.System.ConfigSync.synchronize_to_group(group=dg)

    def do_set_active(self):
        if isinstance(self.options.set_active, DeviceAccess):
            desired_active = self.options.set_active.address
        else:
            desired_active = self.options.set_active
        active_devices = wait(self.do_get_active, timeout=30, interval=2)
        device_map = {}

        for device in active_devices:
            if not device[0]:
                LOG.warning('No configuration found for device %s', device[2])
                continue
            cred = device[0].get_admin_creds()
            with IcontrolInterface(address=device[0].address,
                                   username=cred.username,
                                   password=cred.password,
                                   port=device[0].ports['https']) as icifc:
                v = icifc.version
                if v.product.is_bigip and v < 'bigip 11.2.0' or \
                   v.product.is_em and v < 'em 3.0.0':
                    LOG.warning('Set active not supported on this version (%s).', v)

                ic = icifc.api
                devices = ic.Management.Device.get_list()
                mgmtaddrs = ic.Management.Device.get_management_address(devices=devices)
                device_map = dict(zip(mgmtaddrs, devices))

                if device_map.get(desired_active):
                    LOG.info("Current Active device is %s.", device[2])
                    LOG.info("Setting %s to Active...", device_map[desired_active])
                    ic.System.Failover.set_standby_to_device(device=device_map[desired_active])

        def _is_desired_device_active(devices):
            return [x for x in devices if x[1] == 'HA_STATE_ACTIVE'
                                       and x[2] == device_map[desired_active]]
        if device_map.get(desired_active):
            LOG.info("Waiting for Active status...")
            wait(self.do_get_active, _is_desired_device_active, timeout=10,
                 interval=1)

    def do_config_all(self):
        peers = self.peers
        groups = self.groups
        ipv6 = self.options.ipv6
        cas = self.cas

        if not cas:
            LOG.warning('No CAs specified, NOOP!')
            return

        ca_cred = cas[0].get_admin_creds()
        with IcontrolInterface(address=cas[0].address, username=ca_cred.username,
                               password=ca_cred.password,
                               port=cas[0].ports['https']) as caicifc:
            ca_api = caicifc.api
            v = ICMD.system.get_version(ifc=caicifc)
            if v.product.is_bigip and v < 'bigip 11.0':
                raise NotImplementedError('Not working for < 11.0: %s' % caicifc.address)

            self.do_prep_dgs(caicifc, cas[0], groups)
            self.do_prep_cmi(caicifc, cas[0], ipv6)

            for peer in cas[1:]:
                cred = peer.get_admin_creds()
                with IcontrolInterface(address=peer.address, username=cred.username,
                                       password=cred.password,
                                       port=peer.ports['https']) as peericifc:

                    v = ICMD.system.get_version(ifc=peericifc)
                    if v.product.is_bigip and v < 'bigip 11.0':
                        raise NotImplemented('Not working for < 11.0')

                    self.do_prep_cmi(peericifc, peer, ipv6)
                    peer_address = peericifc.api.Networking.AdminIP.get_list()[0]

                LOG.info('Adding CA device %s to trust...', peer)
                ca_api.Management.Trust.add_authority_device(address=peer_address,
                                                             username=cred.username,
                                                             password=cred.password,
                                                             device_object_name=peer.alias,
                                                             browser_cert_serial_number='',
                                                             browser_cert_signature='',
                                                             browser_cert_sha1_fingerprint='',
                                                             browser_cert_md5_fingerprint='')
            for peer in peers:
                cred = peer.get_admin_creds()
                with IcontrolInterface(address=peer.address, username=cred.username,
                                       password=cred.password,
                                       port=peer.ports['https']) as peericifc:

                    v = ICMD.system.get_version(ifc=peericifc)
                    if v.product.is_bigip and v < 'bigip 11.0':
                        raise NotImplemented('Not working for < 11.0')

                    self.do_prep_cmi(peericifc, peer, ipv6)
                    peer_address = peericifc.api.Networking.AdminIP.get_list()[0]

                LOG.info('Adding non-CA device %s to trust...', peer)
                ca_api.Management.Trust.add_non_authority_device(address=peer_address,
                                                             username=cred.username,
                                                             password=cred.password,
                                                             device_object_name=peer.alias,
                                                             browser_cert_serial_number='',
                                                             browser_cert_signature='',
                                                             browser_cert_sha1_fingerprint='',
                                                             browser_cert_md5_fingerprint='')

            group_2_devices = {}
            for device in cas + peers:
                for group in device.groups:
                    group_2_devices.setdefault(group, [])
                    group_2_devices[group].append(device.alias)

            device_groups, devices = zip(*group_2_devices.items())

            LOG.info('Adding devices %s to %s...', devices, device_groups)
            ca_api.Management.DeviceGroup.add_device(device_groups=device_groups,
                                                     devices=devices)

            if self.options.floatingip:
                LOG.info('Adding floating ip to %s...', DEFAULT_TG)
                ip = IPNetwork(self.options.floatingip)
                if ip.prefixlen == 32:
                    raise ValueError("Did you forget the /16 prefix?")

#                from SOAPpy import SOAPBuilder
                ca_api.Networking.SelfIPV2.create(self_ips=['int_floating'],
                                                  vlan_names=['internal'],
                                                  addresses=[str(ip.ip)],
                                                  netmasks=[str(ip.netmask())],
                                                  traffic_groups=[DEFAULT_TG],
                                                  floating_states=['STATE_ENABLED']
                                                  )

            # BUG: BZ364939 (workaround restart tmm on all peers)
            # 01/22: Appears to work sometimes in 11.2 955.0
            self.do_BZ364939()

    def setup(self):
        self.set_devices()
        self.set_groups()

        if self.options.reset:
            self.do_reset_all()

        if self.options.config:
            self.do_config_all()

        if self.options.set_active:
            self.do_set_active()

        if self.options.sync:
            self.do_config_sync()


def main():
    import optparse
    import sys

    usage = """%prog [options] <CA address>[:port][,<CA username>[,<CA password>]] [peer1] [~][peer2]..."""
    """<peer address>[:port][,<peer username>[,<peer password>]] [<peer address>...]"""
    """[-g dg1[:dgtype]] [-g ...]"""

    formatter = optparse.TitledHelpFormatter(indent_increment=2,
                                             max_help_position=60)
    p = optparse.OptionParser(usage=usage, formatter=formatter,
                            version="CMI Device Trust Configurator v%s" % __version__
        )
    p.add_option("-v", "--verbose", action="store_true",
                 help="Debug messages")

    p.add_option("-u", "--username", metavar="USERNAME", default='admin',
                 type="string", help="Default username. (default: admin)")
    p.add_option("-p", "--password", metavar="PASSWORD", default='admin',
                 type="string", help="Default password. (default: admin)")
    p.add_option("-g", "--dg", metavar="DEVICEGROUP", type="string",
                 action="append",
                 help="Device Group(s) and type. (default: %s)" % DEFAULT_DG)
    p.add_option("-6", "--ipv6", action="store_true", default=False,
                 help="Use only IPv6 self IPs as ConfigSync IPs.")
    p.add_option("-f", "--floatingip", metavar="IP/PREFIX", type="string",
                 help="Floating self IP for the default TG.")

    p.add_option("-c", "--config", action="store_true", default=False,
                 help="Configure Trust and Device Groups.")
    p.add_option("-r", "--reset", action="store_true", default=False,
                 help="Reset trust on all devices.")
    p.add_option("-s", "--sync", action="store_true", default=False,
                 help="Do the initial config sync.")
    p.add_option("-a", "--set-active", metavar="ADDRESS", type="string",
                 help="Set this device Active on all Traffic Groups.")

    p.add_option("-t", "--timeout", metavar="TIMEOUT", type="int", default=60,
                 help="Timeout. (default: 60)")

    options, args = p.parse_args()

    if options.verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO
        #logging.getLogger('paramiko.transport').setLevel(logging.ERROR)
        logging.getLogger('f5test').setLevel(logging.INFO)
        logging.getLogger('f5test.macros').setLevel(logging.INFO)

    LOG.setLevel(level)
    logging.basicConfig(level=level)

    if not args:
        p.print_version()
        p.print_help()
        sys.exit(2)

    cas = args[:1]
    if cas[0].startswith('~'):
        cas[0] = cas[0][1:]

    peers = []
    for spec in args[1:]:
        if spec.startswith('~'):
            cas.append(spec[1:])
        else:
            peers.append(spec)

    # Backward compatibility:
    # Assume config action is desired when no other actions are set.
    if not (options.config or options.reset or options.sync or
            options.set_active):
        options.config = True

    cs = FailoverMacro(options=options, authorities=cas, peers=peers,
                       groups=options.dg)
    cs.run()


if __name__ == '__main__':
    main()
