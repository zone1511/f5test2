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
import logging
#import time
import uuid


DEFAULT_DG = '/Common/dg'
LOG = logging.getLogger(__name__)
__version__ = '0.1'


class Failover(Macro):

    def __init__(self, options, authorities=None, peers=None):
        self.options = Options(options.__dict__)
        #self.addresses = addresses
        self.authorities_spec = authorities
        self.peers_spec = peers
        self.cas = []
        self.peers = []

        super(Failover, self).__init__()

    def set_devices(self):
        default_username = self.options.username
        default_password = self.options.password
        self.cas = []
        self.peers = []
        
        def parse_spec(specs, alias=None):
            bits = specs.split(':')
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
            
            device.alias = alias or device.address
            return device

        count = 0
        for specs in self.authorities_spec:
            count += 1
            if isinstance(specs, basestring):
                device = parse_spec(specs, 'ca-%d' % count)
            else:
                device = specs
            self.cas.append(device)

        count = 0
        for specs in self.peers_spec:
            count += 1
            if isinstance(specs, basestring):
                device = parse_spec(specs, 'peer-%d' % count)
            else:
                device = specs
            self.peers.append(device)

    def do_reset_all(self):
        devices = self.cas + self.peers

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
                if DEFAULT_DG in dgs:
                    LOG.info('Removing %s from %s...', DEFAULT_DG, device)
                    ic.Management.DeviceGroup.remove_all_devices(device_groups=[DEFAULT_DG])
                    ic.Management.DeviceGroup.delete_device_group(device_groups=[DEFAULT_DG])

    def do_prep_cmi(self, icifc, device):
        ic = icifc.api
        selfips = ic.Networking.SelfIPV2.get_list()
        vlans = ic.Networking.SelfIPV2.get_vlan(self_ips=selfips)
        vlan_ip_map = dict(zip(vlans, selfips))
        internal_selfip = vlan_ip_map['/Common/internal']

        if not self.options.get('update'):
            LOG.info('Resetting trust on %s...', device)
            ic.Management.Trust.reset_all(device_object_name=device.alias,
                                          keep_current_authority='false',
                                          authority_cert='',
                                          authority_key='')
        
        LOG.info('Setting config sync address on %s to %s...', device, internal_selfip)
        internal_address = ic.Networking.SelfIPV2.get_address(self_ips=[internal_selfip])[0]
        ic.Management.Device.set_configsync_address(devices=[device.alias],
                                      addresses=[internal_address])

        LOG.info('Setting multicast failover on %s...', device)
        ic.Management.Device.set_multicast_address(devices=[device.alias],
                                                   addresses=[dict(interface_name='eth0',
                                                                  address=dict(address='224.0.0.245',
                                                                               port=62960)
                                                                  )]
                                                   )

        LOG.info('Setting primary mirror address on %s to %s...', device, internal_selfip)
        ic.Management.Device.set_primary_mirror_address(devices=[device.alias],
                                                        addresses=[internal_address])
    
    def setup(self):
            
        self.set_devices()
        cas = self.cas
        peers = self.peers
        
        if not cas:
            LOG.warning('No CAs specified, NOOP!')
            return
        
        if self.options.reset:
            return self.do_reset_all()
        
        ca_cred = cas[0].credentials[0]
        with IcontrolInterface(address=cas[0].address, username=ca_cred.username,
                               password=ca_cred.password) as caicifc:
            ca_api = caicifc.api
            #print ic.System.ConfigSync.get_version()
            v = ICMD.system.get_version(ifc=caicifc, _no_cache=True)
            if v.product.is_bigip and v < 'bigip 11.0':
                raise NotImplementedError('Not working for < 11.0: %s' % caicifc.address)
        
            dgs = ca_api.Management.DeviceGroup.get_list()
            if DEFAULT_DG in dgs:
                if not self.options.get('update'):
                    LOG.info('Removing all devices from %s on %s...', DEFAULT_DG, cas[0])
                    ca_api.Management.DeviceGroup.remove_all_devices(device_groups=[DEFAULT_DG])
            else:
                LOG.info('Creating %s on %s...', DEFAULT_DG, cas[0])
                ca_api.Management.DeviceGroup.create(device_groups=['dg'],
                                                     types=['DGT_SYNC_ONLY'])

            self.do_prep_cmi(caicifc, cas[0])

            for peer in cas[1:]:
                cred = peer.credentials[0]
                with IcontrolInterface(address=peer.address, username=cred.username,
                                       password=cred.password) as peericifc:
                
                    v = ICMD.system.get_version(ifc=peericifc)
                    if v.product.is_bigip and v < 'bigip 11.0':
                        raise NotImplemented('Not working for < 11.0')
                    
                    self.do_prep_cmi(peericifc, peer)

                LOG.info('Adding CA device %s to trust...', peer)
                ca_api.Management.Trust.add_authority_device(address=peer.address,
                                                             username=cred.username,
                                                             password=cred.password,
                                                             device_object_name=peer.alias,
                                                             browser_cert_serial_number='',
                                                             browser_cert_signature='',
                                                             browser_cert_sha1_fingerprint='',
                                                             browser_cert_md5_fingerprint='')

            # BUG: BZ365144 (workaround bigstart restart on peers)
            for peer in peers:
                cred = peer.credentials[0]
                with IcontrolInterface(address=peer.address, username=cred.username,
                                       password=cred.password) as peericifc:
                
                    v = ICMD.system.get_version(ifc=peericifc)
                    if v.product.is_bigip and v < 'bigip 11.0':
                        raise NotImplemented('Not working for < 11.0')
                    
                    self.do_prep_cmi(peericifc, peer)

                LOG.info('Adding non-CA device %s to trust...', peer)
                ca_api.Management.Trust.add_non_authority_device(address=peer.address,
                                                             username=cred.username,
                                                             password=cred.password,
                                                             device_object_name=peer.alias,
                                                             browser_cert_serial_number='',
                                                             browser_cert_signature='',
                                                             browser_cert_sha1_fingerprint='',
                                                             browser_cert_md5_fingerprint='')
            
            # NOTE: somehow old devices are getting added automatically.
            #       Prevent from adding duplicates here. 
            my_peers = ["/Common/%s" % x.alias for x in cas + peers]
            existing = ca_api.Management.DeviceGroup.get_device(device_groups=[DEFAULT_DG])
            remaining = set(my_peers) - set(existing[0])
            extra = set(existing[0]) - set(my_peers)
            
            if remaining:
                LOG.info('Adding devices %s to %s...', list(remaining), DEFAULT_DG)
                ca_api.Management.DeviceGroup.add_device(device_groups=[DEFAULT_DG],
                                                         devices=[list(remaining)])
            if extra:
                LOG.info('Removing devices %s from %s...', list(extra), DEFAULT_DG)
                ca_api.Management.DeviceGroup.remove_device(device_groups=[DEFAULT_DG],
                                                            devices=[list(extra)])
                    

def main():
    import optparse
    import sys

    usage = """%prog [options] <CA address>[:<CA username>[:<CA password>]] [peer1] [~][peer2]..."""
    """<peer address>[:<peer username>[:<peer password>]] [<peer address>...]"""

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
    p.add_option("-r", "--reset", action="store_true",
                 help="Reset trust on all devices.")
    p.add_option("-U", "--update", action="store_true",
                 help="Update DG.")
    
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

    cs = Failover(options=options, authorities=cas, peers=peers)
    cs.run()


if __name__ == '__main__':
    main()
