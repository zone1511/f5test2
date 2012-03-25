'''
Created on May 26, 2011

@author: jono
'''
from .base import IcontrolCommand
from ...interfaces.icontrol.driver import IControlFault 
from ..base import CommandError
from ...base import Options
from IPy import IP
import copy

import logging
LOG = logging.getLogger(__name__) 


get_nodes = None
class GetNodes(IcontrolCommand):
    """Returns the Node list and their object statuses in a dictionary.
    
    Example:
    {'/Common/10.10.0.54': {'availability_status': 'AVAILABILITY_STATUS_GREEN', 
                            'enabled_status': 'ENABLED_STATUS_ENABLED', 
                            'status_description': 'Node address is available'}}
    """
    
    def setup(self):
        ic = self.api
        v = self.ifc.version
        
        if v.product.is_bigip and v < 'bigip 11.0':
            try:
                if v.product.is_bigip and v > 'bigip 9.3.1':
                    ic.Management.Partition.set_active_partition(active_partition='[All]')
                nodes = ic.LocalLB.NodeAddress.get_list()
                statuses = ic.LocalLB.NodeAddress.get_object_status(node_addresses=nodes)
            finally:
                if v.product.is_bigip and v > 'bigip 9.3.1':
                    ic.Management.Partition.set_active_partition(active_partition='Common')
        elif v.product.is_bigip and v >= 'bigip 11.0':
            #self.ifc.set_session()
            try:
                ic.System.Session.set_active_folder(folder='/')
                ic.System.Session.set_recursive_query_state(state='STATE_ENABLED')
                nodes = ic.LocalLB.NodeAddressV2.get_list()
                statuses = ic.LocalLB.NodeAddressV2.get_object_status(nodes=nodes)
            finally:
                ic.System.Session.set_active_folder(folder='/Common')
        else:
            raise CommandError('Unsupported version: %s' % v)
        
        return dict(zip(nodes, statuses))


get_pools = None
class GetPools(IcontrolCommand):
    """Returns the Pool list and their object statuses in a dictionary.

    Example:
    {'/Common/LTM10Pool-029': {'availability_status': 'AVAILABILITY_STATUS_GREEN', 
                               'enabled_status': 'ENABLED_STATUS_ENABLED', 
                               'status_description': 'The pool is available'}}
    """
    
    def setup(self):
        ic = self.api
        v = self.ifc.version
        
        if v.product.is_bigip and v < 'bigip 11.0':
            try:
                if v.product.is_bigip and v > 'bigip 9.3.1':
                    ic.Management.Partition.set_active_partition(active_partition='[All]')
                pools = ic.LocalLB.Pool.get_list()
                statuses = ic.LocalLB.Pool.get_object_status(pool_names=pools)
            finally:
                if v.product.is_bigip and v > 'bigip 9.3.1':
                    ic.Management.Partition.set_active_partition(active_partition='Common')
        elif v.product.is_bigip and v >= 'bigip 11.0':
            try:
                ic.System.Session.set_active_folder(folder='/')
                ic.System.Session.set_recursive_query_state(state='STATE_ENABLED')
                pools = ic.LocalLB.Pool.get_list()
                statuses = ic.LocalLB.Pool.get_object_status(pool_names=pools)
            finally:
                ic.System.Session.set_active_folder(folder='/Common')
        else:
            raise CommandError('Unsupported version: %s' % v)
        
        return dict(zip(pools, statuses))


get_pool_members = None
class GetPoolMembers(IcontrolCommand):
    """Returns the Pool Member list.

    Example:
    {'/LTM10Partition3/LTM10Pool-004@/LTM10Partition3/10.10.0.53:80': 
                        {'availability_status': 'AVAILABILITY_STATUS_GREEN', 
                        'enabled_status': 'ENABLED_STATUS_ENABLED', 
                        'status_description': 'Pool member is available'}}
    """
    
    def setup(self):
        ic = self.api
        v = self.ifc.version
        
        if v.product.is_bigip and v < 'bigip 11.0':
            try:
                if v.product.is_bigip and v > 'bigip 9.3.1':
                    ic.Management.Partition.set_active_partition(active_partition='[All]')
                pools = ic.LocalLB.Pool.get_list()
                pool_members = ic.LocalLB.Pool.get_member(pool_names=pools)
                statuses = ic.LocalLB.PoolMember.get_object_status(pool_names=pools)
                
                # On 11.0+ statuses are key-based
                statuses = dict([("%s@%s:%s" % (x[0], y['member']['address'], 
                                                      y['member']['port']), 
                                  y['object_status']) 
                                for x in zip(pools, statuses)
                                for y in x[1]])
            finally:
                if v.product.is_bigip and v > 'bigip 9.3.1':
                    ic.Management.Partition.set_active_partition(active_partition='Common')
        elif v.product.is_bigip and v >= 'bigip 11.0':
            try:
                ic.System.Session.set_active_folder(folder='/')
                ic.System.Session.set_recursive_query_state(state='STATE_ENABLED')
                pools = ic.LocalLB.Pool.get_list()
                pool_members = ic.LocalLB.Pool.get_member_v2(pool_names=pools)
                statuses_11x = ic.LocalLB.Pool.get_member_object_status(pool_names=pools,
                                                                        members=pool_members)
                # On 11.0+ statuses are index-based
                statuses = {}
                i = 0
                for pair in zip(pools, pool_members):
                    j = 0
                    for pool_member in pair[1]:
                        name = "%s@%s:%s" % (pair[0], pool_member['address'], 
                                             pool_member['port'])
                        statuses[name] = statuses_11x[i][j]
                        j += 1
                    i += 1
            finally:
                ic.System.Session.set_active_folder(folder='/Common')
        else:
            raise CommandError('Unsupported version: %s' % v)
        
        return statuses


get_virtual_servers = None
class GetVirtualServers(IcontrolCommand):
    """Returns the Virtual Server list and their object statuses in a dictionary.

    Example:
    {'/LTM10Partition3/LTM10VIP-058': 
                        {'availability_status': 'AVAILABILITY_STATUS_GREEN', 
                        'enabled_status': 'ENABLED_STATUS_ENABLED', 
                        'status_description': 'The virtual server is available'}
    """
    
    def setup(self):
        ic = self.api
        v = self.ifc.version
        
        if v.product.is_bigip and v < 'bigip 11.0':
            try:
                if v.product.is_bigip and v > 'bigip 9.3.1':
                    ic.Management.Partition.set_active_partition(active_partition='[All]')
                vips = ic.LocalLB.VirtualServer.get_list()
                statuses = ic.LocalLB.VirtualServer.get_object_status(virtual_servers=vips)
            finally:
                if v.product.is_bigip and v > 'bigip 9.3.1':
                    ic.Management.Partition.set_active_partition(active_partition='Common')
        elif v.product.is_bigip and v >= 'bigip 11.0':
            try:
                ic.System.Session.set_active_folder(folder='/')
                ic.System.Session.set_recursive_query_state(state='STATE_ENABLED')
                vips = ic.LocalLB.VirtualServer.get_list()
                statuses = ic.LocalLB.VirtualServer.get_object_status(virtual_servers=vips)
            finally:
                ic.System.Session.set_active_folder(folder='/Common')
        else:
            raise CommandError('Unsupported version: %s' % v)
        
        return dict(zip(vips, statuses))


create_ltm_app = None
class CreateLtmApp(IcontrolCommand):
    """Create a Virtual Server and all its dependencies.

    @param definition: Virtual Server definition
    @type definition: Options instance
    @param options: Optional pool members, monitors, profiles, etc.
    @type options: Options instance
    """
    def __init__(self, definition, options=None, *args, **kwargs):
        super(CreateLtmApp, self).__init__(*args, **kwargs)
        self.definition = definition
        self.definition.setdefault('name', 'vs_1')
        self.definition.setdefault('address', '10.11.10.1')
        self.definition.setdefault('port', 80)
        self.definition.setdefault('protocol', 'PROTOCOL_TCP')
        self.options = options or Options()
        self.rollback = Options()

        if options.folder:
            self.folder_prefix = "%s/" % options.folder
        else:
            self.folder_prefix = ''

    def prep(self):
        super(CreateLtmApp, self).prep()
        v = abs(self.ifc.version)
        self.is_solstice = v >= 'bigip 11.0'
        
        # Folders not supported on < 11.0
        if not self.is_solstice:
            self.folder_prefix = ''

    def revert(self):
        ic = self.api
        if self.rollback.virtual:
            virtual_server = self.rollback.virtual
            ic.LocalLB.VirtualServer.delete_virtual_server(virtual_servers=[virtual_server])
        
        if self.rollback.pool:
            pool_name = self.rollback.pool
            ic.LocalLB.Pool.delete_pool(pool_names=[pool_name])

        if self.rollback.nodes:
            nodes = self.rollback.nodes
            try:
                if self.is_solstice:
                    ic.LocalLB.NodeAddressV2.delete_node_address(nodes=nodes)
                else:
                    ic.LocalLB.NodeAddress.delete_node_address(node_addresses=nodes)
            except IControlFault:
                LOG.warning('Some nodes could not be deleted')
        
        # Cleanup Folder
        if self.rollback.folder:
            ic.Management.Folder.delete_folder(folders=[self.rollback.folder])

        super(CreateLtmApp, self).revert()

    def do_enable_monitor(self, enable, nodes):
        ic = self.api
        addresses = [Options(address_type='ATYPE_EXPLICIT_ADDRESS', 
                             ipaddress=x) for x in nodes]
        
        monitor_rule = Options()
        monitor_rule.quorum = 0
        if enable:
            monitor_rule.monitor_templates = ['icmp']
            monitor_rule.type = 'MONITOR_RULE_TYPE_SINGLE'
        else:
            monitor_rule.monitor_templates = ''
            monitor_rule.type = 'MONITOR_RULE_TYPE_NONE'
            
        if self.is_solstice:
            monitor_rules = [monitor_rule] * len(nodes)
            ic.LocalLB.NodeAddressV2.set_monitor_rule(nodes=nodes,
                                                      monitor_rules=monitor_rules)
        else:
            if enable:
                monitor_associations = [Options(node_address=x,
                                                monitor_rule=monitor_rule) 
                                        for x in addresses]
                ic.LocalLB.NodeAddress.set_monitor_association(monitor_associations=monitor_associations)
            else:
                monitor_associations = [Options(node_address=x,
                                                removal_rule='REMOVE_ALL_MONITOR_ASSOCIATION') 
                                        for x in addresses]
                ic.LocalLB.NodeAddress.remove_monitor_association(monitor_associations=monitor_associations)

    def do_create_pool(self, pool_name, members):
        ic = self.api
        if self.is_solstice:
            ic.LocalLB.Pool.create_v2(pool_names=[pool_name],
                                      lb_methods=['LB_METHOD_ROUND_ROBIN'],
                                      members=[members])
        else:
            ic.LocalLB.Pool.create(pool_names=[pool_name],
                                   lb_methods=['LB_METHOD_ROUND_ROBIN'],
                                   members=[members])

    def cleanup(self):
        ic = self.api
        if self.rollback.initial_folder:
            initial_folder = self.rollback.initial_folder
            if initial_folder != '/Common':
                ic.System.Session.set_active_folder(folder=initial_folder)

    def setup(self):
        ic = self.api
        o = self.options
        
        if self.is_solstice and self.options.folder:
            current_folder = ic.System.Session.get_active_folder()
            self.rollback.initial_folder = current_folder
            
            ic.System.Session.set_active_folder(folder='/')
            ic.System.Session.set_recursive_query_state(state='STATE_ENABLED')
            folders = ic.Management.Folder.get_list()
            ic.System.Session.set_active_folder(folder='/Common')
            if self.options.folder not in folders:
                LOG.debug('Creating Folder...')
                ic.Management.Folder.create(folders=[self.options.folder])
                self.rollback.folder = self.options.folder

        if o.pool_members:
            members = []
            for pool_member in o.pool_members:
                ip, port = pool_member
                definition = Options()
                if self.is_solstice:
                    definition.address = "%s%s" % (self.folder_prefix, ip)
                else:
                    definition.address = ip
                definition.port = int(port)
                members.append(definition)
            pool_name = "%s%s_pool" % (self.folder_prefix, self.definition.name)
            self.do_create_pool(pool_name, members)
            self.rollback.pool = pool_name

            resource = Options()
            resource.type = 'RESOURCE_TYPE_POOL'
            resource.default_pool_name = pool_name

            state = o.nodes_forced_down and 'STATE_DISABLED' or 'STATE_ENABLED'
            nodes = [x.address for x in members]
            if self.is_solstice:
                ic.LocalLB.NodeAddressV2.set_monitor_state(nodes=nodes, 
                                                           states=[state]*len(members))
            else:
                ic.LocalLB.NodeAddress.set_monitor_state(node_addresses=nodes, 
                                                         states=[state]*len(members))
            self.rollback.nodes = nodes
            
            
            if o.monitor_enabled is True:
                LOG.debug('Enabling icmp monitor on nodes...')
                self.do_enable_monitor(enable=True, nodes=nodes)
            elif o.monitor_enabled is False:
                LOG.debug('Removing any monitors from nodes...')
                self.do_enable_monitor(enable=False, nodes=nodes)
            else:
                LOG.debug('Leaving default node monitor.')

        else:
            resource = Options()
            resource.type = 'RESOURCE_TYPE_POOL'
            resource.default_pool_name = ''
        
        profiles = []
        for profile_name in o.profiles or []:
            http_profile = Options()
            http_profile.profile_context = 'PROFILE_CONTEXT_TYPE_ALL'
            http_profile.profile_name = profile_name

        ip_vs = IP(self.definition.address.split('%',1)[0]) # Take care of Route Domains
        if ip_vs.version() == 6:
            wildmask = 'ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff'
        else:
            wildmask = '255.255.255.255'
        
        definition = copy.copy(self.definition)
        definition.name = "%s%s" % (self.folder_prefix, self.definition.name)
        ic.LocalLB.VirtualServer.create(definitions=[definition],
                                        wildmasks=[wildmask],
                                        resources=[resource],
                                        profiles=[profiles])
        self.rollback.virtual = definition

delete_ltm_app = None
class DeleteLtmApp(IcontrolCommand):
    """Delete a Virtual Server and all its dependencies.

    @param name: Virtual Server name
    @type name: str
    """
    def __init__(self, name, folder=None, *args, **kwargs):
        super(DeleteLtmApp, self).__init__(*args, **kwargs)
        self.name = name

        if folder:
            self.folder_prefix = "%s/" % folder
        else:
            self.folder_prefix = ''

    def prep(self):
        super(DeleteLtmApp, self).prep()
        v = abs(self.ifc.version)
        self.is_solstice = v >= 'bigip 11.0'
        
        # Folders not supported on < 11.0
        if not self.is_solstice:
            self.folder_prefix = ''

    def setup(self):
        ic = self.api
        virtual_server = "%s%s" % (self.folder_prefix, self.name)
        pool_name = ic.LocalLB.VirtualServer.get_default_pool_name(virtual_servers=[virtual_server])[0]
        
        if self.is_solstice:
            members = ic.LocalLB.Pool.get_member_v2(pool_names=[pool_name])[0]
        else:
            members = ic.LocalLB.Pool.get_member(pool_names=[pool_name])[0]
        
        LOG.debug('Deleting Virtual Server...')
        ic.LocalLB.VirtualServer.delete_virtual_server(virtual_servers=[virtual_server])
        if pool_name:
            LOG.debug('Deleting Pool...')
            ic.LocalLB.Pool.delete_pool(pool_names=[pool_name])

        try:
            LOG.debug('Deleting Nodes...')
            nodes = [x['address'] for x in members]
            if self.is_solstice:
                ic.LocalLB.NodeAddressV2.delete_node_address(nodes=nodes)
            else:
                ic.LocalLB.NodeAddress.delete_node_address(node_addresses=nodes)
        except IControlFault:
            LOG.warning('Some nodes could not be deleted')
