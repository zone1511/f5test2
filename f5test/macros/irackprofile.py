#!/usr/bin/env python
'''
Created on May 26, 2011

@author: jono
'''
from f5test.macros.base import Macro
from f5test.base import Options, AttrDict
from f5test.interfaces.rest.irack import IrackInterface
import logging

IRACK_HOSTNAME = 'irack.mgmt.pdsea.f5net.com'
IRACK_HOSTNAME_DEBUG = '127.0.0.1:8081'
LOG = logging.getLogger(__name__)
DEFAULT_RANGE = '172.27.58.0/24'
__version__ = '0.1'


def id_from_uri(uri):
    return int(uri.split('/')[-2])

class IrackProfile(Macro):

    def __init__(self, options, address=None):
        self.options = Options(options.__dict__)
        self.address = address

        super(IrackProfile, self).__init__()

    def setup(self):
        if self.options.verbose:
            hostname = IRACK_HOSTNAME_DEBUG
        else:
            hostname = IRACK_HOSTNAME
        with IrackInterface(address=hostname,
                            timeout=self.options.timeout,
                            username=self.options.username,
                            password=self.options.apikey, ssl=False) as irack:
            
            done = False
            nextitem = None
            dump = dict(static={})
            static = dump['static'] = {}
            
            if self.address:
                params = dict(address_set__address__in=self.address)
            else:
                params = dict(address_set__address__range=DEFAULT_RANGE)
            
            while not done:
                if nextitem:
                    ret = irack.api.from_uri(nextitem).filter()
                else:
                    ret = irack.api.staticbag.filter(asset__type=1, **params)
                nextitem = ret.data.meta.next
                if nextitem is None:
                    done = True
                
                for bag in map(AttrDict, ret.data.objects):
                    bagid = bag.id
                    
                    print '=' * 80
                    ret = irack.api.staticaddress.filter(bag=bagid, type=0, access=True)
                    assert ret.data.meta.total_count == 1, ret
                    mgmtip = ret.data.objects[0]['address']
                    asset_id = id_from_uri(bag.asset)
                    print 'Asset ID:', asset_id
                    ret = irack.api.f5asset.get_by_id(asset_id)
                    print 'Available:', not ret.data.v_is_reserved
                    
                    ret = irack.api.asset.get_by_id(asset_id)
                    print 'IP:', mgmtip
                    mgmtip_node = static[mgmtip] = AttrDict()
        
                    print '-' * 80
                    ret = irack.api.staticaddress.filter(bag=bagid, type=1)
                    selfip_node = mgmtip_node.selfip = AttrDict()
                    for o in map(AttrDict, ret.data.objects):
                        vlan = o.vlan.split('/')[-1]
                        print 'Vlan:', vlan
                        print 'Address:', o.address
                        print 'Netmask:', o.netmask
                        selfip_node[vlan] = AttrDict(address=o.address, 
                                                     netmask=o.netmask)
        
                    print '-' * 80
                    ret = irack.api.staticsystem.filter(bag=bagid)
                    assert ret.data.meta.total_count == 1
                    hostname = ret.data.objects[0]['hostname']
                    print 'Hostname:', hostname
                    mgmtip_node.hostname = hostname
                    
                    print '-' * 80
                    ret = irack.api.staticlicense.filter(bag=bagid)
                    licenses_node = mgmtip_node.licenses = AttrDict()
                    licenses_node.reg_key = []
                    for o in map(AttrDict, ret.data.objects):
                        print 'License desc:', o.description
                        print 'Regkey:', o.reg_key
                        #licenses_node['description'] = o['description']
                        licenses_node.reg_key.append(o.reg_key)
        
                    #print '-' * 80
                    print
            #print yaml.safe_dump(dump, default_flow_style=False)

def main():
    import optparse
    import sys

    usage = """%prog [options] <address> ..."""

    formatter = optparse.TitledHelpFormatter(indent_increment=2, 
                                             max_help_position=60)
    p = optparse.OptionParser(usage=usage, formatter=formatter,
                            version="F5 Software Installer v%s" % __version__
        )
    p.add_option("-v", "--verbose", action="store_true",
                 help="Debug messages")
    
    p.add_option("-u", "--username", metavar="USERNAME",
                 type="string", help="Your iRack username.")
    p.add_option("-p", "--apikey", metavar="APIKEY",
                 type="string", help="Your iRack API key.")
    
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
    
    cs = IrackProfile(options=options, address=args)
    cs.run()


if __name__ == '__main__':
    main()
