'''
Created on Dec 6, 2011

@author: jono
'''
from .base import IcontrolCommand
from ..base import CommandError
from .locallb import create_ltm_app, delete_ltm_app
from ...base import Options
from netaddr import IPAddress
import re

import logging
LOG = logging.getLogger(__name__) 


is_gtm_available = None
class IsGtmAvailable(IcontrolCommand):
    """Returns the true if GTMD is started or false if not.
    
    @rtype: bool
    """

    def setup(self):
        ic = self.api
        ret = ic.System.Services.get_service_status(services=['SERVICE_GTMD'])
        return ret[0]['status'] == 'SERVICE_STATUS_UP'

get_pools = None
class GetPools(IcontrolCommand):
    """Returns the Pool list and their object statuses in a dictionary.
    
    Example:
    {'/Common/subf1.1/test.net_pool': 
                    {'availability_status': 'AVAILABILITY_STATUS_GREEN', 
                    'enabled_status': 'ENABLED_STATUS_ENABLED', 
                    'status_description': 'Available'}}
    """
    
    def setup(self):
        ic = self.api
        v = self.ifc.version
        
        if v.product.is_bigip and v < 'bigip 11.0':
            try:
                if v.product.is_bigip and v > 'bigip 9.3.1':
                    ic.Management.Partition.set_active_partition(active_partition='[All]')
                pools = ic.GlobalLB.Pool.get_list()
                statuses = ic.GlobalLB.Pool.get_object_status(pool_names=pools)
            finally:
                if v.product.is_bigip and v > 'bigip 9.3.1':
                    ic.Management.Partition.set_active_partition(active_partition='Common')
        elif v.product.is_bigip and v >= 'bigip 11.0':
            #self.ifc.set_session()
            try:
                ic.System.Session.set_active_folder(folder='/')
                ic.System.Session.set_recursive_query_state(state='STATE_ENABLED')
                pools = ic.GlobalLB.Pool.get_list()
                statuses = ic.GlobalLB.Pool.get_object_status(pool_names=pools)
            finally:
                ic.System.Session.set_active_folder(folder='/Common')
        else:
            raise CommandError('Unsupported version: %s' % v)
        
        return dict(zip(pools, statuses))


get_pool_members = None
class GetPoolMembers(IcontrolCommand):
    """Returns the Pool Member list.

    Example:
    {'/Common/subf1.1/test.net_pool@/Common/test.net_server:test_net_vs': 
                {'availability_status': 'AVAILABILITY_STATUS_GREEN', 
                'enabled_status': 'ENABLED_STATUS_ENABLED', 
                'status_description': ''}}
    """
    
    def setup(self):
        ic = self.api
        v = self.ifc.version
        
        if v.product.is_bigip and v < 'bigip 11.0':
            try:
                if v.product.is_bigip and v > 'bigip 9.3.1':
                    ic.Management.Partition.set_active_partition(active_partition='[All]')
                pools = ic.GlobalLB.Pool.get_list()
                pool_members = ic.GlobalLB.Pool.get_member(pool_names=pools)
                
                pool_members_fix = []
                for pool in pool_members:
                    member_fix = []
                    for member in pool:
                        member_fix.append(member['member'])
                    pool_members_fix.append(member_fix)
                
                statuses = ic.GlobalLB.PoolMember.get_object_status(pool_names=pools,
                                                                    members=pool_members_fix)
                # On 9.x statuses are key-based
                statuses = dict([("%s@%s:%s" % (x[0], y['member']['address'], 
                                                      y['member']['port']), 
                                  y['status']) 
                                for x in zip(pools, statuses)
                                for y in x[1]])
            finally:
                if v.product.is_bigip and v > 'bigip 9.3.1':
                    ic.Management.Partition.set_active_partition(active_partition='Common')
        elif v.product.is_bigip and v >= 'bigip 11.0':
            try:
                ic.System.Session.set_active_folder(folder='/')
                ic.System.Session.set_recursive_query_state(state='STATE_ENABLED')
                pools = ic.GlobalLB.Pool.get_list()
                pool_members = ic.GlobalLB.Pool.get_member_v2(pool_names=pools)
                statuses_11x = ic.GlobalLB.Pool.get_member_object_status(pool_names=pools,
                                                                         members=pool_members)
                # On 11.0+ statuses are index-based
                statuses = {}
                i = 0
                for pair in zip(pools, pool_members):
                    j = 0
                    for pool_member in pair[1]:
                        name = "%s@%s:%s" % (pair[0], pool_member['server'], 
                                             pool_member['name'])
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
    {'/Common/test.net_server:gaga': 
                {'availability_status': 'AVAILABILITY_STATUS_RED', 
                'enabled_status': 'ENABLED_STATUS_ENABLED', 
                'status_description': ' Monitor /Common/bigip from gtmd : no reply from big3d: timed out'}}
    """
    
    def setup(self):
        ic = self.api
        v = self.ifc.version
        
        if v.product.is_bigip and v < 'bigip 11.0':
            try:
                if v.product.is_bigip and v > 'bigip 9.3.1':
                    ic.Management.Partition.set_active_partition(active_partition='[All]')
                vips = ic.GlobalLB.VirtualServer.get_list()
                statuses = ic.GlobalLB.VirtualServer.get_object_status(virtual_servers=vips)
                virtuals = ["%s@%s:%d" % (x['name'], x['address'], x['port']) 
                            for x in vips]
            finally:
                if v.product.is_bigip and v > 'bigip 9.3.1':
                    ic.Management.Partition.set_active_partition(active_partition='Common')
        elif v.product.is_bigip and v >= 'bigip 11.0':
            try:
                ic.System.Session.set_active_folder(folder='/')
                ic.System.Session.set_recursive_query_state(state='STATE_ENABLED')
                vips = ic.GlobalLB.VirtualServerV2.get_list()
                statuses = ic.GlobalLB.VirtualServerV2.get_object_status(virtual_servers=vips)
                virtuals = ["%s:%s" % (x['server'], x['name']) 
                            for x in vips]
            finally:
                ic.System.Session.set_active_folder(folder='/Common')
        else:
            raise CommandError('Unsupported version: %s' % v)
        
        return dict(zip(virtuals, statuses))


get_wideips = None
class GetWideips(IcontrolCommand):
    """Returns the WideIP list and their object statuses in a dictionary.
    
    Example:
    {'/Common/subf1.1/test.net': 
                    {'availability_status': 'AVAILABILITY_STATUS_GREEN', 
                    'enabled_status': 'ENABLED_STATUS_ENABLED', 
                    'status_description': 'Available'}}
    """
    
    def setup(self):
        ic = self.api
        v = self.ifc.version
        
        if v.product.is_bigip and v < 'bigip 11.0':
            try:
                if v.product.is_bigip and v > 'bigip 9.3.1':
                    ic.Management.Partition.set_active_partition(active_partition='[All]')
                wips = ic.GlobalLB.WideIP.get_list()
                statuses = ic.GlobalLB.WideIP.get_object_status(wide_ips=wips)
            finally:
                if v.product.is_bigip and v > 'bigip 9.3.1':
                    ic.Management.Partition.set_active_partition(active_partition='Common')
        elif v.product.is_bigip and v >= 'bigip 11.0':
            #self.ifc.set_session()
            try:
                ic.System.Session.set_active_folder(folder='/')
                ic.System.Session.set_recursive_query_state(state='STATE_ENABLED')
                wips = ic.GlobalLB.WideIP.get_list()
                statuses = ic.GlobalLB.WideIP.get_object_status(wide_ips=wips)
            finally:
                ic.System.Session.set_active_folder(folder='/Common')
        else:
            raise CommandError('Unsupported version: %s' % v)
        
        return dict(zip(wips, statuses))


create_gtm_app = None
class CreateGtmApp(IcontrolCommand):
    """Create a Wide IP and all its dependencies.

    @param name: Wide IP name
    @type name: str
    @param options: Optional pool members, monitors, profiles, etc.
    @type options: Options instance
    """
    def __init__(self, name, options=None, *args, **kwargs):
        super(CreateGtmApp, self).__init__(*args, **kwargs)
        self.name = name
        self.options = options or Options()
        
        if options.folder:
            self.folder_prefix = "%s/" % options.folder
        else:
            self.folder_prefix = ''
        
        self.options.setdefault('ltm_definition', Options())
        self.options.setdefault('ltm_options', Options())
        self.rollback = Options()

    def prep(self):
        super(CreateGtmApp, self).prep()
        v = abs(self.ifc.version)
        self.is_solstice = v >= 'bigip 11.0'
        self.is_931 = v == 'bigip 9.3.1'

        # Folders not supported on < 11.0
        if not self.is_solstice:
            self.folder_prefix = ''

    def revert(self):
        ic = self.api
        # Cleanup GTM Listener
        if self.rollback.listener:
            gtm_vs = [self.rollback.listener]
            ic.LocalLB.VirtualServer.delete_virtual_server(virtual_servers=gtm_vs)
            
        # Cleanup Wide IP
        if self.rollback.wide_ip:
            wide_ip = self.rollback.wide_ip
            ic.GlobalLB.WideIP.delete_wideip(wide_ips=[wide_ip])
        
        # Cleanup Pool    
        if self.rollback.pool:
            pool_name = self.rollback.pool
            ic.GlobalLB.Pool.delete_pool(pool_names=[pool_name])
        
        # Cleanup Virtual Servers    
        if self.rollback.virtual_servers:
            virtual_servers = self.rollback.virtual_servers
            if self.is_solstice:
                ic.GlobalLB.VirtualServerV2.delete_virtual_server(virtual_servers=virtual_servers)
            else:
                ic.GlobalLB.VirtualServer.delete_virtual_server(virtual_servers=virtual_servers)

        # Cleanup Servers    
        if self.rollback.server:
            server = self.rollback.server
            ic.GlobalLB.Server.delete_server(servers=[server])

        # Cleanup Data Centers    
        if self.rollback.data_center:
            data_center = self.rollback.data_center
            ic.GlobalLB.DataCenter.delete_data_center(data_centers=[data_center])

        # Cleanup LTM App    
        if self.rollback.ltm_app:
            vs_name = self.rollback.ltm_app.name
            delete_ltm_app(vs_name, folder=self.options.folder, ifc=self.ifc)

        # Cleanup Folder
        if self.rollback.folder:
            ic.Management.Folder.delete_folder(folders=[self.rollback.folder])

        super(CreateGtmApp, self).revert()

    def do_get_selfip(self, vlan='/Common/internal'):
        ic = self.ifc.api
        if self.is_solstice:
            selfips = ic.Networking.SelfIPV2.get_list()
            vlans = ic.Networking.SelfIPV2.get_vlan(self_ips=selfips)
            vlan_ip_map = dict(zip(vlans, selfips))
            vlan_selfip = vlan_ip_map[vlan]
            return ic.Networking.SelfIPV2.get_address(self_ips=[vlan_selfip])[0]
        else:
            vlan = vlan.split('/')[-1]
            selfips = ic.Networking.SelfIP.get_list()
            vlans = ic.Networking.SelfIP.get_vlan(self_ips=selfips)
            vlan_ip_map = dict(zip(vlans, selfips))
            vlan_selfip = vlan_ip_map.get(vlan)
            if not vlan_selfip:
                raise CommandError('No self IP found for VLAN: %s' % vlan)
            return vlan_selfip

    def do_create_ltmapp(self):
        definition = self.options.ltm_definition
        # Override the LTM App name, otherwise it has to be passed as a param to
        # the delete method.
        definition.name = '%s_vs' % self.name
        o = self.options.ltm_options
        o.setdefault('folder', self.options.folder)
        create_ltm_app(definition, options=o, ifc=self.ifc)
        return definition

    def do_add_listener(self, address):
        ic = self.ifc.api
        vs = Options()
        vs.name = '%svs_%s_53_gtm' % (self.folder_prefix, 
                                      re.sub(r'[^\w/]', r'_', self.name))
        vs.address = address
        vs.port = 53
        vs.protocol = 'PROTOCOL_UDP'
        
        udp_profile = Options()
        udp_profile.profile_context = 'PROFILE_CONTEXT_TYPE_ALL'
        udp_profile.profile_name = 'dns'
        gtm_profile = Options()
        gtm_profile.profile_context = 'PROFILE_CONTEXT_TYPE_ALL'
        gtm_profile.profile_name = 'udp_gtm_dns'
        
        resource = Options()
        resource.type = 'RESOURCE_TYPE_POOL'
        resource.default_pool_name = ''
        
        ip_vs = IPAddress(vs.address.split('%',1)[0]) # Take care of Route Domains
        if ip_vs.version == 6:
            wildmask = 'ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff'
        else:
            wildmask = '255.255.255.255'

        ic.LocalLB.VirtualServer.create(definitions=[vs],
                                        wildmasks=[wildmask],
                                        resources=[resource],
                                        profiles=[[udp_profile, gtm_profile]])
        
        ic.LocalLB.VirtualServer.set_translate_address_state(virtual_servers=[vs.name],
                                                             states=['STATE_DISABLED'])
        ic.LocalLB.VirtualServer.set_translate_port_state(virtual_servers=[vs.name],
                                                          states=['STATE_DISABLED'])
        LOG.debug('Added listener: %s', vs.name)

    def cleanup(self):
        ic = self.api
        if self.rollback.initial_folder:
            initial_folder = self.rollback.initial_folder
            if initial_folder != '/Common':
                ic.System.Session.set_active_folder(folder=initial_folder)

    def setup(self):
        ic = self.ifc.api

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

        LOG.debug('Creating DataCenter...')
        dc = Options()
        dc.name = '%s_dc' % self.name
        dc.location = 'somewhere'
        dc.contact = 'someone'
        ic.GlobalLB.DataCenter.create(data_centers=[dc])
        self.rollback.data_center = dc.name
        
        LOG.debug('Creating Server...')
        server_name = '%s_server' % self.name
        ip = Options()
        ip.device = '%s_device' % self.name
        
        if self.options.server_address:
            ip.addresses_on_device = [self.options.server_address]
            servertype = 'SERVER_TYPE_GENERIC_HOST'
        else:
            ip.addresses_on_device = [self.do_get_selfip()]
            servertype = 'SERVER_TYPE_BIGIP_STANDALONE'
        
        if self.is_solstice:
            ic.GlobalLB.Server.create_v2(servers=[server_name],
                                         ips=[[ip]],
                                         types=[servertype],
                                         data_centers=[dc.name])
        else:
            server = Options()
            server.server = server_name
            server.addresses = []
            saddr = Options()
            saddr.unit_id = 0
            saddr.addresses_on_unit = []
            saddr.addresses_on_unit.append(ip.addresses_on_device[0])
            server.addresses.append(saddr)
            ic.GlobalLB.Server.create(servers=[server],
                                      types=[servertype],
                                      data_centers=[dc.name])
        self.rollback.server = server_name
        
        ic.GlobalLB.Server.set_auto_configuration_state(servers=[server_name],
                                                        states=['AUTOCONFIG_DISABLED'])
        
        LOG.debug('Adding Virtual Server...')
        vs = self.do_create_ltmapp()
        self.rollback.ltm_app = vs

        def strip(string):
            return re.sub(r'[^\w/]', r'_', string)
        
        ltm_vs = [vs]
        if self.is_solstice:
            virtual_servers = [Options(name=strip(x.name), server=server_name) 
                               for x in ltm_vs]
            addresses = [Options(address=x.address, port=x.port) 
                         for x in ltm_vs]
            ic.GlobalLB.VirtualServerV2.create(virtual_servers=virtual_servers,
                                               addresses=addresses)
        else:
            virtual_servers = [Options(name=strip(x.name), address=x.address, 
                                       port=x.port)
                               for x in ltm_vs]
            ic.GlobalLB.VirtualServer.create(virtual_servers=virtual_servers,
                                             servers=[server_name])
        self.rollback.virtual_servers = virtual_servers

        LOG.debug('Creating Pool...')
        pool_name = '%s%s_pool' % (self.folder_prefix, self.name)
        lb_method = 'LB_METHOD_ROUND_ROBIN'
        members = ltm_vs
        orders = range(0, len(members))
        
        if self.is_solstice:
            #re.sub(r'[^\w/]', r'_', x.name)
            members_11x = [Options(name=strip(x.name), server=server_name) 
                           for x in members]
            ip_port_vs = ic.GlobalLB.VirtualServerV2.get_address(virtual_servers=members_11x)
            http_members = [t[0] for t in zip(members_11x, ip_port_vs)]
            ic.GlobalLB.Pool.create_v2(pool_names=[pool_name],
                                       lb_methods=[lb_method],
                                       members=[http_members],
                                       orders=[orders])
        else:
            members_10x = [dict(member=dict(address=t[0]['address'], 
                                            port=t[0]['port']), 
                                order=t[1]) 
                           for t in zip(members, orders)]
            ic.GlobalLB.Pool.create(pool_names=[pool_name],
                                    lb_methods=[lb_method],
                                    members=[members_10x])
        self.rollback.pool = pool_name

        LOG.debug('Creating WideIP...')
        wip_name = "%s%s" % (self.folder_prefix, self.name)
        lb_method = 'LB_METHOD_ROUND_ROBIN'
        pool = Options()
        pool.pool_name = pool_name
        pool.order = 1
        pool.ratio = 1
        ic.GlobalLB.WideIP.create(wide_ips=[wip_name],
                                  lb_methods=[lb_method],
                                  wideip_pools=[[pool]],
                                  wideip_rules=[[]])
        self.rollback.wide_ip = wip_name
        self.options.setdefault('listener', 
                                self.do_get_selfip('/Common/external'))
        self.do_add_listener(self.options.listener)
        self.rollback.listener = self.options.listener


delete_gtm_app = None
class DeleteGtmApp(IcontrolCommand):
    """Delete a Wide IP and all its dependencies.

    @param name: Wide IP name
    @type name: str
    """
    def __init__(self, name, folder=None, *args, **kwargs):
        super(DeleteGtmApp, self).__init__(*args, **kwargs)
        self.name = name
        self.folder = folder

        if folder:
            self.folder_prefix = "%s/" % folder
        else:
            self.folder_prefix = ''

    def prep(self):
        super(DeleteGtmApp, self).prep()
        v = abs(self.ifc.version)
        self.is_solstice = v >= 'bigip 11.0'
        
        # Folders not supported on < 11.0
        if not self.is_solstice:
            self.folder_prefix = ''

    def do_get_selfip(self, vlan='/Common/internal'):
        ic = self.ifc.api
        if self.is_solstice:
            selfips = ic.Networking.SelfIPV2.get_list()
            vlans = ic.Networking.SelfIPV2.get_vlan(self_ips=selfips)
            vlan_ip_map = dict(zip(vlans, selfips))
            vlan_selfip = vlan_ip_map[vlan]
            return ic.Networking.SelfIPV2.get_address(self_ips=[vlan_selfip])[0]
        else:
            vlan = vlan.split('/')[-1]
            selfips = ic.Networking.SelfIP.get_list()
            vlans = ic.Networking.SelfIP.get_vlan(self_ips=selfips)
            vlan_ip_map = dict(zip(vlans, selfips))
            vlan_selfip = vlan_ip_map[vlan]
            return vlan_selfip

    def setup(self):
        ic = self.ifc.api
        gtm_vs = ['%svs_%s_53_gtm' % (self.folder_prefix, 
                                      re.sub(r'[^\w/]', r'_', self.name))]

        LOG.debug('Deleting Wide IP...')
        wide_ip = "%s%s" % (self.folder_prefix, self.name)
        pool = ic.GlobalLB.WideIP.get_wideip_pool(wide_ips=[wide_ip])[0]
        ic.GlobalLB.WideIP.delete_wideip(wide_ips=[wide_ip])
        pool_names = [x['pool_name'] for x in pool]
        members = ic.GlobalLB.Pool.get_member(pool_names=pool_names)[0]
        
        LOG.debug('Deleting Pool...')
        ic.GlobalLB.Pool.delete_pool(pool_names=pool_names)
        
        # TODO: Use VirtualServerV2 interface for 11.0+
        virtual_servers = ic.GlobalLB.VirtualServer.get_list()
        virtual_servers = [Options(name=x[0]['name'], 
                                   address=x[1]['member']['address'], 
                                   port=x[1]['member']['port']) 
                           for x in zip(virtual_servers, members)]
        servers = ic.GlobalLB.VirtualServer.get_server(virtual_servers=virtual_servers)
        
        LOG.debug('Deleting Virtual Servers...')
        ic.GlobalLB.VirtualServer.delete_virtual_server(virtual_servers=virtual_servers)
        data_centers = ic.GlobalLB.Server.get_data_center(servers=servers)
        
        LOG.debug('Deleting Servers...')
        ic.GlobalLB.Server.delete_server(servers=servers)
        
        LOG.debug('Deleting Data Center...')
        ic.GlobalLB.DataCenter.delete_data_center(data_centers=data_centers)
        
        LOG.debug('Deleting Listener...')
        ic.LocalLB.VirtualServer.delete_virtual_server(virtual_servers=gtm_vs)
        
        LOG.debug('Deleting LTM app...')
        delete_ltm_app('%s_vs' % self.name, folder=self.folder, ifc=self.ifc)
