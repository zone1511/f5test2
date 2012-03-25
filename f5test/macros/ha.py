#!/usr/bin/env python
'''
Created on May 31, 2011

@author: jono
'''
from f5test.macros.base import Macro
from f5test.base import Options
from f5test.interfaces.icontrol import IcontrolInterface
import f5test.commands.icontrol as ICMD
from f5test.interfaces.config import DeviceAccess, DeviceCredential
from f5test.utils.wait import wait
from IPy import IP
import logging
#import time
import uuid


DEFAULT_DG = '/Common/f5test.ha-dg'
DEFAULT_DG_TYPE = 'DGT_FAILOVER'
RESERVED_GROUPS = ('gtm', 'device_trust_group')
DEFAULT_TG = 'traffic-group-1'
LOG = logging.getLogger(__name__)
__version__ = '0.1'


class Failover(Macro):

    def __init__(self, options, authorities=None, peers=None, groups=None):
        self.options = Options(options.__dict__)
        #self.addresses = addresses
        self.authorities_spec = authorities
        self.peers_spec = peers
        self.cas = []
        self.peers = []
        self.groups_specs = groups

        super(Failover, self).__init__()

    def set_devices(self):
        default_username = self.options.username
        default_password = self.options.password
        self.cas = []
        self.peers = []
        
        def parse_spec(specs, alias=None):
            bits = specs.split('@', 1)
            if len(bits) > 1:
                groups = set(bits[1].split(','))
            else:
                groups = DEFAULT_DG
            bits = bits[0].split(':')

            if len(bits) == 1:
                cred = DeviceCredential(default_username, default_password)
                device = DeviceAccess(bits[0], (cred,))
            elif len(bits) == 2:
                cred = DeviceCredential(default_username, bits[1])
                device = DeviceAccess(bits[0], (cred,))
            elif len(bits) == 3:
                cred = DeviceCredential(bits[1], bits[2])
                device = DeviceAccess(bits[0], (cred,))
            else:
                raise ValueError('Invalid specs: %s', specs)
            
            #device.alias = alias or device.address
            device.alias = "device-%s" % device.address
            device.set_groups(groups)
            return device

        count = 0
        for specs in self.authorities_spec:
            count += 1
            if isinstance(specs, basestring):
                #device = parse_spec(specs, 'ca-%d' % count)
                device = parse_spec(specs)
            else:
                device = specs
            self.cas.append(device)

        count = 0
        for specs in self.peers_spec:
            count += 1
            if isinstance(specs, basestring):
                #device = parse_spec(specs, 'peer-%d' % count)
                device = parse_spec(specs)
            else:
                device = specs
            self.peers.append(device)

    def set_groups(self):
        groups = {}
        for spec in self.groups_specs:
            bits = spec.split(':')
            if len(bits) > 1:
                if bits[1] in ('s', 'so', 'config-sync'):
                    groups[bits[0]] = 'DGT_SYNC_ONLY'
                else:    
                    groups[bits[0]] = 'DGT_FAILOVER'
            else:
                groups[bits[0]] = 'DGT_FAILOVER'
        self.groups = groups
            
    def do_reset_all(self):
        devices = self.cas + self.peers
        groups = self.groups.keys()

        for device in devices:
            cred = device.credentials[0]
            with IcontrolInterface(address=device.address, username=cred.username,
                                   password=cred.password) as icifc:
                ic = icifc.api
                v = ICMD.system.get_version(ifc=icifc)
                if v.product.is_bigip and v < 'bigip 11.0':
                    raise NotImplemented('Not working for < 11.0')
                
                LOG.info('Resetting trust on %s...', device)
                ic.Management.Trust.reset_all(device_object_name=uuid.uuid4().hex, #device.alias,
                                              keep_current_authority='false',
                                              authority_cert='',
                                              authority_key='')

                dgs = ic.Management.DeviceGroup.get_list()
                for dg in groups:
                    if dg in dgs:
                        LOG.info('Removing %s from %s...', dg, device)
                        ic.Management.DeviceGroup.remove_all_devices(device_groups=[dg])
                        ic.Management.DeviceGroup.delete_device_group(device_groups=[dg])

    def do_BZ364939(self):
        devices = self.cas + self.peers
        devices.reverse()

        for device in devices:
            cred = device.credentials[0]
            with IcontrolInterface(address=device.address, username=cred.username,
                                   password=cred.password) as icifc:
                
                #if icifc.version.product.is_bigip and icifc.version < 'bigip 11.2':
                ic = icifc.api
                LOG.info('Working around BZ364939 on %s...', device)
                ic.System.Services.set_service(services=['SERVICE_TMM'],
                                               service_action='SERVICE_ACTION_RESTART')
                wait(ic.System.Failover.get_failover_state, 
                     lambda x:x != 'FAILOVER_STATE_OFFLINE')

    def do_prep_cmi(self, icifc, device, ipv6=False):
        ic = icifc.api
        selfips = ic.Networking.SelfIPV2.get_list()
        addresses = ic.Networking.SelfIPV2.get_address(self_ips=selfips)
        states = ic.Networking.SelfIPV2.get_floating_state(self_ips=selfips)
        vlans = ic.Networking.SelfIPV2.get_vlan(self_ips=selfips)
        selfips = [(x[3], x[1]) for x in zip(selfips, addresses, states, 
                                             vlans)
                   if IP(x[1]).version() == (6 if ipv6 else 4) and 
                      x[2] == 'STATE_DISABLED']
        
        vlan_ip_map = dict(selfips)
        LOG.debug("VLAN map: %s", vlan_ip_map)
        internal_selfip = vlan_ip_map['/Common/internal']

        LOG.info('Resetting trust on %s...', device)
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
        
        LOG.info('Setting config sync address on %s to %s...', device, 
                 internal_selfip)
        ic.Management.Device.set_configsync_address(devices=[device.alias],
                                                    addresses=[internal_selfip])

        LOG.info('Setting multicast failover on %s...', device)
        ic.Management.Device.set_multicast_address(devices=[device.alias],
                                                   addresses=[dict(interface_name='eth0',
                                                                  address=dict(address='224.0.0.245',
                                                                               port=62960)
                                                                  )]
                                                   )

        LOG.info('Setting primary mirror address on %s to %s...', device, 
                 internal_selfip)
        ic.Management.Device.set_primary_mirror_address(devices=[device.alias],
                                                        addresses=[internal_selfip])
        
        if vlan_ip_map.get('/Common/external'):
            external_selfip = vlan_ip_map['/Common/external']
            LOG.info('Setting secondary mirror address on %s to %s...', device, 
                     external_selfip)
            ic.Management.Device.set_secondary_mirror_address(devices=[device.alias],
                                                              addresses=[external_selfip])
    
    # TODO: optimize to work with multiple groups at once.
    def do_prep_dgs(self, icifc, device, groups):
        ic = icifc.api
        dgs = ic.Management.DeviceGroup.get_list()

        for reserved_group in RESERVED_GROUPS:
            if reserved_group in dgs:
                dgs.remove('/Common/%s' % reserved_group)
        
        LOG.info('Removing groups %s on %s...', dgs, device)
        ic.Management.DeviceGroup.remove_all_devices(device_groups=dgs)
        ic.Management.DeviceGroup.delete_device_group(device_groups=dgs)

        for group_name, group_type in groups.items():
            LOG.info('Creating %s on %s...', group_name, device)
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

    def do_initial_sync(self, icifc):
        groups = self.groups.keys()
        LOG.info("Doing initial sync to %s...", groups)
        ic = icifc.api
        for dg in groups:
            ic.System.ConfigSync.synchronize_to_group(group=dg)

    def setup(self):
        self.set_devices()
        self.set_groups()
        cas = self.cas
        peers = self.peers
        groups = self.groups
        ipv6 = self.options.ipv6
        
        if not cas:
            LOG.warning('No CAs specified, NOOP!')
            return
        
        if self.options.reset:
            return self.do_reset_all()
        
        ca_cred = cas[0].credentials[0]
        with IcontrolInterface(address=cas[0].address, username=ca_cred.username,
                               password=ca_cred.password) as caicifc:
            ca_api = caicifc.api
            v = ICMD.system.get_version(ifc=caicifc)
            if v.product.is_bigip and v < 'bigip 11.0':
                raise NotImplementedError('Not working for < 11.0: %s' % caicifc.address)
        
            self.do_prep_dgs(caicifc, cas[0], groups)
            self.do_prep_cmi(caicifc, cas[0], ipv6)

            for peer in cas[1:]:
                cred = peer.credentials[0]
                with IcontrolInterface(address=peer.address, username=cred.username,
                                       password=cred.password) as peericifc:
                
                    v = ICMD.system.get_version(ifc=peericifc)
                    if v.product.is_bigip and v < 'bigip 11.0':
                        raise NotImplemented('Not working for < 11.0')
                    
                    self.do_prep_cmi(peericifc, peer, ipv6)

                LOG.info('Adding CA device %s to trust...', peer)
                ca_api.Management.Trust.add_authority_device(address=peer.address,
                                                             username=cred.username,
                                                             password=cred.password,
                                                             device_object_name=peer.alias,
                                                             browser_cert_serial_number='',
                                                             browser_cert_signature='',
                                                             browser_cert_sha1_fingerprint='',
                                                             browser_cert_md5_fingerprint='')
            for peer in peers:
                cred = peer.credentials[0]
                with IcontrolInterface(address=peer.address, username=cred.username,
                                       password=cred.password) as peericifc:
                
                    v = ICMD.system.get_version(ifc=peericifc)
                    if v.product.is_bigip and v < 'bigip 11.0':
                        raise NotImplemented('Not working for < 11.0')
                    
                    self.do_prep_cmi(peericifc, peer, ipv6)

                LOG.info('Adding non-CA device %s to trust...', peer)
                ca_api.Management.Trust.add_non_authority_device(address=peer.address,
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
                ip = IP(self.options.floatingip)
                if ip.prefixlen() == 32:
                    raise ValueError("Did you forget the /16 prefix?")
                ip_str = str(ip).split('/', 1)[0]
                
#                from SOAPpy import SOAPBuilder
                ca_api.Networking.SelfIPV2.create(self_ips=['int_floating'],
                                                  vlan_names=['internal'],
                                                  addresses=[ip_str],
                                                  netmasks=[str(ip.netmask())],
                                                  traffic_groups=[DEFAULT_TG],
                                                  floating_states=['STATE_ENABLED']
                                                  )
            
            # BUG: BZ364939 (workaround restart tmm on all peers)
            # 01/22: Appears to work sometimes in 11.2 955.0
            self.do_BZ364939()
            self.do_initial_sync(caicifc)
                    

def main():
    import optparse
    import sys

    usage = """%prog [options] <CA address>[:<CA username>[:<CA password>]] [peer1] [~][peer2]..."""
    """<peer address>[:<peer username>[:<peer password>]] [<peer address>...]"""
    """[-g dg1[:dgtype]] [-g ...]"""

    formatter = optparse.TitledHelpFormatter(indent_increment=2, 
                                             max_help_position=60)
    p = optparse.OptionParser(usage=usage, formatter=formatter,
                            version="F5 Software Installer v%s" % __version__
        )
    p.add_option("-v", "--verbose", action="store_true",
                 help="Debug messages")
    
    p.add_option("-u", "--username", metavar="USERNAME", default='admin',
                 type="string", help="Default username. (default: admin)")
    p.add_option("-p", "--password", metavar="PASSWORD", default='f5site02',
                 type="string", help="Default password. (default: f5site02)")
    p.add_option("-g", "--dg", metavar="DEVICEGROUP", type="string", 
                 action="append",
                 help="Device Group(s) and type. (default: %s)" % DEFAULT_DG)
    p.add_option("-r", "--reset", action="store_true",
                 help="Reset trust on all devices.")
    p.add_option("-6", "--ipv6", action="store_true", default=False,
                 help="Use only IPv6 self IPs as ConfigSync IPs.")
    p.add_option("-f", "--floatingip", metavar="IP/PREFIX", type="string", 
                 help="FLoating self IP for the default TG.")

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
    
    cs = Failover(options=options, authorities=cas, peers=peers, 
                  groups=options.dg or [DEFAULT_DG])
    cs.run()


if __name__ == '__main__':
    main()
