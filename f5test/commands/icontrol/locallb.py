'''
Created on May 26, 2011

@author: jono
'''
from .base import IcontrolCommand
from ..base import CommandError

import logging
LOG = logging.getLogger(__name__) 


get_nodes = None
class GetNodes(IcontrolCommand):
    """Returns the Node list.
    """
    
    def setup(self):
        ic = self.api
        v = self.ifc.version
        
        if v.product.is_bigip and v < 'bigip 11.0':
            try:
                if v.product.is_bigip and v > 'bigip 9.3.1':
                    ic.Management.Partition.set_active_partition(active_partition='[All]')
                nodes = ic.LocalLB.NodeAddress.get_list()
            finally:
                if v.product.is_bigip and v > 'bigip 9.3.1':
                    ic.Management.Partition.set_active_partition(active_partition='Common')
            return nodes
        elif v.product.is_bigip and v >= 'bigip 11.0':
            #self.ifc.set_session()
            try:
                ic.System.Session.set_active_folder(folder='/')
                ic.System.Session.set_recursive_query_state(state='STATE_ENABLED')
                nodes = ic.LocalLB.NodeAddressV2.get_list()
            finally:
                ic.System.Session.set_active_folder(folder='/Common')
            return nodes
        else:
            raise CommandError('Unsupported version: %s' % v)