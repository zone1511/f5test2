'''
Created on Jun 9, 2011

@author: jono
'''
from ..sql import Query


get_metrics_count = None
class GetMetricsCount(Query):
    """Returns the metrics count calculated live.
    
    @rtype: int
    """
    def __init__(self, *args, **kwargs):
        super(GetMetricsCount, self).__init__(query=None, *args, **kwargs)

    def setup(self):
        self.query = "CALL set_perfmon_metrics(0)"
        super(GetMetricsCount, self).setup()
        
        self.query = "CALL get_metrics_count()"
        ret = super(GetMetricsCount, self).setup()[0]

        if ret.collection_rate == '---':
            return 0
        else:
            return int(ret.collection_rate)

get_device_objects = None
class GetDeviceObjects(Query):
    """Returns the network objects count associated with a device.
    
    @param address:  The management address of the device.
    @param type: Stat type (e.g. node, pool, pool_member, vip)
    @return: A table with the following columns: host_name, address, stat_type, instance_name.
    @rtype: list
    """
    def __init__(self, address, type='node', username='admin', *args, **kwargs):
        # Queries were captured with mysql log slow queries.
        # Edit /var/lib/mysql/my.cnf:
        # [mysqld]
        # log-slow-queries = /tmp/slow.log
        # long_query_time = 0
        if type in ('node', 'pool', 'vip'):
            query = r"""
            select count(distinct deviceconf0_.device_config_item_uid) as count 
from device_config_%s deviceconf0_ 
inner join device_config_item deviceconf0_1_ on deviceconf0_.device_config_item_uid=deviceconf0_1_.uid 
inner join partition partition1_ on deviceconf0_1_.partition_uid=partition1_.partition_uid 
inner join device device2_ on deviceconf0_1_.device_uid=device2_.uid 
inner join user_2_device deviceuser3_ on device2_.uid=deviceuser3_.device_uid 
inner join device_config_current_statistics deviceconf4_ on deviceconf0_.device_config_item_uid=deviceconf4_.device_config_item_uid 
inner join device_config_current_statistics_v deviceconf5_ on deviceconf4_.uid=deviceconf5_.device_config_current_statistics_uid 

where deviceuser3_.login_name='%s' 
and (deviceuser3_.access_partition_uid is null 
    or deviceuser3_.access_partition_uid=partition1_.partition_uid 
    or partition1_.name='Common') 
and mgmt_address = '%s'""" % (type, username, address)
        elif type == 'pool_member':
            query = r"""
            select count(distinct deviceconf0_.device_config_item_uid) as count 
from device_config_pool_member deviceconf0_ 
inner join device_config_item deviceconf0_1_ on deviceconf0_.device_config_item_uid=deviceconf0_1_.uid 
inner join device_config_pool deviceconf1_ on deviceconf0_.device_config_pool_uid=deviceconf1_.device_config_item_uid 
inner join device_config_item deviceconf1_1_ on deviceconf1_.device_config_item_uid=deviceconf1_1_.uid 
inner join partition partition2_ on deviceconf0_1_.partition_uid=partition2_.partition_uid 
inner join device device3_ on deviceconf0_1_.device_uid=device3_.uid 
inner join user_2_device deviceuser4_ on device3_.uid=deviceuser4_.device_uid 
inner join device_config_current_statistics deviceconf5_ on deviceconf0_.device_config_item_uid=deviceconf5_.device_config_item_uid 
inner join device_config_current_statistics_v deviceconf6_ on deviceconf5_.uid=deviceconf6_.device_config_current_statistics_uid 

where deviceuser4_.login_name='%s' 
and (deviceuser4_.access_partition_uid is null 
    or deviceuser4_.access_partition_uid=partition2_.partition_uid 
    or partition2_.name='Common')
and mgmt_address = '%s'""" % (username, address)
        else:
            raise NotImplementedError('Unknown type: %s' % type)

        super(GetDeviceObjects, self).__init__(query=query, *args, **kwargs)

    def setup(self):
        return int(super(GetDeviceObjects, self).setup()[0]['count'])

monitoring_enabled = None
class MonitoringEnabled(Query):
    """Returns the collection state (on or off).
    
    @return: Collection state.
    @rtype: bool
    """
    def __init__(self, *args, **kwargs):
        query = "SELECT value FROM `em_str_daemon_setting` WHERE " \
                "name='em.monitoring.monitoring_enabled';"
        super(MonitoringEnabled, self).__init__(query=query, *args, **kwargs)

    def setup(self):
        return super(MonitoringEnabled, self).setup()[0]['value'] == 'true'
