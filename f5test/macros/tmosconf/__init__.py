'''
Created on Apr 9, 2013

@author: jono
'''
import logging
from f5test.macros.tmosconf.placer import ConfigPlacer


if __name__ == '__main__':
    from f5test.base import AttrDict as O
    from f5test.utils.version import Version
    from f5test.macros.tmosconf.base import (SystemConfig, NetworkConfig,
                                             LTMConfig, AFMConfig)
    logging.basicConfig(level=logging.INFO)

    context = O(version=Version('bigip 10.1.0'),
                provision=O(afm='nominal', ltm='nominal'))

    o = O()
    o.partitions = 1
    o.mgmtip = '172.27.95.102/24'
    o.gateway = '172.27.95.254'
    o.nameservers = ['172.27.1.1']
    o.ntpservers = ['ntp.f5net.com']
    o.provision = {}
    o.provision.ltm = 'nominal'
    o.users = {}
    o.users.g = 'guest'
    o.users.a = 'admin'
    o.users.o = 'operator'
    #o.users.ra = O(password='a', role='guest')
    o.smtpserver = 'mail.aaaa.bb'
    tree = SystemConfig(context, **o).run()

    o = O()
    o.tree = tree
    o.vlans = {}
    o.vlans.internal = O(interfaces=['1.1'])
    o.vlans.external = O(interfaces=['1.2'])
    #o.trunks = {}
    #o.trunks.main = O(interfaces=['1/1.1', '2/1.1'], lacp=True)
    o.selfips = {}
    #o.selfips.internal = '10.1.1.1'
    #o.selfips.external = '10.2.1.1'
    o.selfips.internal = O(address='10.1.1.1/24', name='blah')
    NetworkConfig(context, **o).run()

    o = O()
    o.tree = tree
    o.with_monitors = False
    LTMConfig(context, **o).run()

    o = O()
    o.tree = tree
    o.address_lists = 2
    o.port_lists = 2
    o.rules = 2
    o.rules_lists = 2
    o.vlans = 2
    o.self_ips = 2
    o.route_domains = 2
    o.vips = 2
    AFMConfig(context, **o).run()

    # rendering
    s = tree.render()
    s.seek(0)
    print s.read()
