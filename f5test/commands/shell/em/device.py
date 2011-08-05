'''
Created on Apr 25, 2011

@author: jono
'''
from ..sql import Query
#from ...base import WaitableCommand
from ....utils.version import Version


class DeviceNotFound(Exception):
    pass

class TaskNotFound(Exception):
    pass


get_device_info = None
class GetDeviceInfo(Query):

    def __init__(self, mgmtip=None, *args, **kwargs):
        self.mgmtip = mgmtip
        fields = ['uid', 'access_address', 'host_name', 'platform',
                  'active_slot', 'chassis_serial', 'perfmon_state',
                  'monitoring_bytes_per_second',
                  'monitoring_counters_per_second', 'discovery_status',
                  'product_name', 'version', 'build_number',
                  'supports_asm', 'disk_partition_scheme']
        if mgmtip:
            query = "SELECT %s FROM device WHERE access_address = '%s'" % \
                        (','.join(fields), mgmtip)
        else:
            query = "SELECT %s FROM device" % ','.join(fields)

        super(GetDeviceInfo, self).__init__(query=query, *args, **kwargs)

    def setup(self):
        if self.mgmtip:
            try:
                return super(GetDeviceInfo, self).setup()[0]
            except IndexError:
                raise DeviceNotFound("%s" % self.mgmtip)
        else:
            return super(GetDeviceInfo, self).setup()


filter_device_info = None
class FilterDeviceInfo(Query):

    def __init__(self, filter=None, onlyavailable=False, *args, **kwargs):
        assert filter is None or callable(filter), "Filter must be callable or None"
        self.filter = filter
        fields = ['uid', 'access_address', 'host_name', 'platform',
                  'active_slot', 'chassis_serial', 'perfmon_state',
                  'monitoring_bytes_per_second',
                  'monitoring_counters_per_second', 'discovery_status',
                  'product_name', 'version', 'build_number',
                  'supports_asm', 'disk_partition_scheme', 'current_job_uid']
        
        if onlyavailable:
#            query = """SELECT %s FROM device d 
#                                 LEFT JOIN device_2_job dj ON (d.uid = dj.device_uid) 
#                       WHERE dj.job_uid IS NULL""" % ','.join(fields)
            query = """SELECT %s FROM device  
                       WHERE current_job_uid IS NULL""" % ','.join(fields)
        else:
            query = "SELECT %s FROM device" % ','.join(fields)

        super(FilterDeviceInfo, self).__init__(query=query, *args, **kwargs)

    def setup(self):
        return filter(self.filter, super(FilterDeviceInfo, self).setup())


get_device_version = None
class GetDeviceVersion(GetDeviceInfo):

    def setup(self):
        try:
            ret = super(GetDeviceInfo, self).setup()[0]
        except IndexError:
            raise DeviceNotFound("%s" % self.mgmtip)
        return Version("%(product_name)s %(version)s %(build_number)s" % ret)


get_device_state = None
class GetDeviceState(Query):

    def __init__(self, mgmtip=None, uids=None, *args, **kwargs):
        self.mgmtip = mgmtip
        fields = ['d.uid', 'access_address', 'refresh_failed_at', 
                  'refresh_state', 'status', 'substatus_message']
        
        if isinstance(mgmtip, basestring):
            where = "WHERE access_address = '%s'" % mgmtip
        elif isinstance(mgmtip, (tuple, list)):
            where = "WHERE access_address IN (%s)" % ','.join(("'%s'" % str(x) for x in mgmtip))
        elif isinstance(uids, (tuple, list)):
            where = "WHERE uid IN (%s)" % ','.join(("%s" % str(x) for x in uids))
        else:
            where = ''
        
        query = """SELECT %s FROM device d
                       LEFT JOIN device_2_substatus d2s ON (d.uid = d2s.device_uid)
                       LEFT JOIN device_substatus ds ON (d2s.substatus_uid = ds.uid)
                       %s
                """ % (','.join(fields), where)

        super(GetDeviceState, self).__init__(query=query, *args, **kwargs)

    def setup(self):
        try:
            return super(GetDeviceState, self).setup()
        except IndexError:
            raise DeviceNotFound("%s" % self.mgmtip)


get_reachable_devices = None
class GetReachableDevices(Query):

    def __init__(self, *args, **kwargs):
        fields = ['d.uid', 'access_address', 'refresh_failed_at', 
                  'refresh_state', 'status', 'substatus_message']
        query = """SELECT %s FROM device d
                       LEFT JOIN device_2_substatus d2s ON (d.uid = d2s.device_uid)
                       LEFT JOIN device_substatus ds ON (d2s.substatus_uid = ds.uid)
                   WHERE refresh_failed_at is NULL""" % \
                    (','.join(fields))

        super(GetReachableDevices, self).__init__(query=query, *args, **kwargs)

    def setup(self):
        return super(GetReachableDevices, self).setup()


get_device_slots = None
class GetDeviceSlots(Query):

    def __init__(self, mgmtip, *args, **kwargs):
        fields = ['product', 'slot_key', 'slot_num', 'visible_name',
                  'ds.version', 'ds.build', 'ds.is_cf', 'ds.reg_key', 'ds.uid']
        query = """SELECT %s FROM device_slot ds 
                             JOIN device d ON (ds.device_id = d.uid)
                             WHERE d.access_address = '%s'""" % \
                    (','.join(fields), mgmtip)

        super(GetDeviceSlots, self).__init__(query=query, *args, **kwargs)


get_device_active_slot = None
class GetDeviceActiveSlot(Query):

    def __init__(self, mgmtip, *args, **kwargs):
        self.mgmtip = mgmtip
        fields = ['product', 'slot_key', 'slot_num', 'visible_name',
                  'ds.version', 'ds.build', 'ds.is_cf', 'ds.reg_key', 'ds.uid']
        query = """SELECT %s FROM device_slot ds 
                             JOIN device d ON (ds.device_id = d.uid AND 
                                               ds.slot_num = d.active_slot)
                             WHERE d.access_address = '%s'""" % \
                    (','.join(fields), mgmtip)

        super(GetDeviceActiveSlot, self).__init__(query=query, *args, **kwargs)

    def setup(self):
        try:
            return super(GetDeviceActiveSlot, self).setup()[0]
        except IndexError:
            raise DeviceNotFound("%s" % self.mgmtip)


get_task = None
class GetTask(Query):

    def __init__(self, task_id, *args, **kwargs):
        self.task_id = int(task_id)
        super(GetTask, self).__init__(query=task_id, *args, **kwargs)

    def prep(self):
        fields = ['uid', 'task_name', 'create_time', 'start_time', 'finish_time',
                  'error_code', 'error_message', 'user_name', 'detail_table',
                  'status']
        self.query = """SELECT %s FROM job_header WHERE uid = '%d'""" % \
                    (','.join(fields), self.task_id)

        super(GetTask, self).prep()


get_discovery_task = None
class GetDiscoveryTask(GetTask):

    def setup(self):
        fields = ['jh.uid', 'task_name', 'create_time', 'start_time', 'finish_time',
                  'error_code', 'error_message', 'user_name', 'detail_table',
                  'status', 'progress_percent']
        self.query = """SELECT %s FROM job_header jh
                                  JOIN discovery_job dj ON (dj.uid = jh.uid)
                                  WHERE jh.uid = '%d'""" % \
                    (','.join(fields), self.task_id)

        try:
            task = super(GetDiscoveryTask, self).setup()[0]
        except IndexError:
            raise TaskNotFound("%s" % self.task_id)

        # 'device-busy'
        self.query = """SELECT COUNT(*) AS count FROM discovery_results 
                        WHERE uid = %s AND discovery_status IN 
                            ('auth-failed', 'comm-failed', 'unsupported', 
                             'unsupported-product-version','db-save-failed',
                             'exceeds-license', 'device-busy')""" % \
                    task['uid']

        error_count = super(GetDiscoveryTask, self).setup()[0]['count']
        task['error_count'] = int(error_count)

        fields = ['uid', 'access_address', 'system_id', 'product_name', 
                  'version', 'build_number', 'discovery_status',
                  'discovery_status_message']
        self.query = """SELECT %s FROM discovery_results
                                  WHERE uid = %d""" % \
                    (','.join(fields), self.task_id)

        details = super(GetDiscoveryTask, self).setup()
        task.details = details
        task.progress_percent = int(task.progress_percent)
        return task


get_big3d_task = None
class GetBig3dTask(GetTask):

    def setup(self):
        fields = ['jh.uid', 'dj.task_name', 'create_time', 'start_time', 'finish_time',
                  'error_code', 'error_message', 'user_name', 'detail_table',
                  'status']
        self.query = """SELECT %s FROM job_header jh
                                  JOIN big3d_install_job dj ON (dj.job_header_uid = jh.uid)
                                  WHERE jh.uid = '%d'""" % \
                    (','.join(fields), self.task_id)

        try:
            task = super(GetBig3dTask, self).setup()[0]
        except IndexError:
            raise TaskNotFound("%s" % self.task_id)

        # 'device-busy'
        self.query = """SELECT COUNT(*) AS count FROM big3d_install_device_job 
                        WHERE big3d_install_job_uid = %s AND error_code != 0""" % \
                    task['uid']

        error_count = super(GetBig3dTask, self).setup()[0]['count']
        task['error_count'] = int(error_count)

        fields = ['uid', 'progress_percent', 'status', 'display_device_name',
                  'display_device_address', 'display_initial_big3d_version',
                  'error_code', 'error_message', 'device_uid']
        self.query = """SELECT %s FROM big3d_install_device_job
                                  WHERE big3d_install_job_uid = %d""" % \
                    (','.join(fields), self.task_id)

        details = super(GetBig3dTask, self).setup()
        task.details = details
        task.progress_percent = sum([100 if int(x['progress_percent']) < -1 else int(x['progress_percent']) 
                                    for x in details]) / len(details)
        
        return task



get_changeset_task = None
class GetChangesetTask(GetTask):

    def setup(self):
        fields = ['jh.uid', 'dscj.task_name', 'create_time', 'start_time', 'finish_time',
                  'error_code', 'error_message', 'user_name', 'detail_table',
                  'status']
        self.query = """SELECT %s FROM job_header jh
                                  JOIN deploy_staged_changeset_job dscj ON (dscj.job_header_uid = jh.uid)
                                  WHERE jh.uid = '%d'""" % \
                    (','.join(fields), self.task_id)

        try:
            task = super(GetChangesetTask, self).setup()[0]
        except IndexError:
            raise TaskNotFound("%s" % self.task_id)

        # 'device-busy'
        self.query = """SELECT COUNT(*) AS count FROM deploy_staged_changeset_changeset_job 
                        WHERE job_header_uid = %s AND error_code != 0""" % \
                    task['uid']

        error_count = super(GetChangesetTask, self).setup()[0]['count']
        task['error_count'] = int(error_count)

        fields = ['uid', 'progress_percent', 'status', 'target_device', 'target_partition',
                  'display_source_name', 'display_source_description',
                  'error_code', 'error_message', 'source_uid']
        self.query = """SELECT %s FROM deploy_staged_changeset_changeset_job 
                                  WHERE job_header_uid = %d""" % \
                    (','.join(fields), self.task_id)

        details = super(GetChangesetTask, self).setup()
        task.details = details
        task.progress_percent = sum([100 if int(x['progress_percent']) < -1 else int(x['progress_percent']) 
                                    for x in details]) / len(details)
        
        return task


count_pending_tasks = None
class CountPendingTasks(Query):

    def __init__(self, mgmtips=None, *args, **kwargs):
        query = """SELECT COUNT(*) AS count FROM device d
                       JOIN device_2_job d2j ON (d.uid = d2j.device_uid)"""
        if mgmtips:
            query += """
                   WHERE d.access_address IN (%s)""" % \
                                    ','.join(("'%s'" % str(x) for x in mgmtips))

        super(CountPendingTasks, self).__init__(query=query, *args, **kwargs)

    def setup(self):
        return int(super(CountPendingTasks, self).setup()[0]['count'])


get_device_archives = None
class GetDeviceArchives(Query):

    def __init__(self, device_uid, pinned=True, *args, **kwargs):
        query = """SELECT * FROM config_archive d WHERE device_uid = %s AND pinned = %d""" % (device_uid, int(pinned))
        
        super(GetDeviceArchives, self).__init__(query=query, *args, **kwargs)


get_diff_filenames = None
class GetDiffFilenames(Query):

    def __init__(self, *args, **kwargs):
        query = """SELECT * FROM diff_file_names"""
        
        super(GetDiffFilenames, self).__init__(query=query, *args, **kwargs)

    def setup(self):
        return [x['file_name'] for x in super(GetDiffFilenames, self).setup()]
