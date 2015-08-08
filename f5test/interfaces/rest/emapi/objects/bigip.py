'''
Created on May 22, 2014
@author: mathur

'''
from .base import DEFAULT_TIMEOUT, Reference, ReferenceList
from ...base import BaseApiObject
from .....utils.wait import wait


class SyncStatus(BaseApiObject):
    URI = '/mgmt/tm/cm/sync-status'
    SYNC_STATE = 'In Sync'
    STANDALONE_STATE = 'Standalone'

    def __init__(self, *args, **kwargs):
        super(SyncStatus, self).__init__(*args, **kwargs)

    @staticmethod
    def wait(icifc, timeout=DEFAULT_TIMEOUT):

        def all_done(ret):
            return ret['entries']['https://localhost/mgmt/tm/cm/sync-status/0']['nestedStats']['entries']['status']['description'] == SyncStatus.STANDALONE_STATE

        ret = wait(lambda: icifc.get(SyncStatus.URI), timeout=timeout, interval=1, condition=all_done,
                   progress_cb=lambda ret: 'Status: {0}'.format((ret['entries']['https://localhost/mgmt/tm/cm/sync-status/0']['nestedStats']['entries']['status']['description'])))

        return ret

    @staticmethod
    def wait_sync(icifc, timeout=DEFAULT_TIMEOUT):

        def all_done(ret):
            return ret['entries']['https://localhost/mgmt/tm/cm/sync-status/0']['nestedStats']['entries']['status']['description'] == SyncStatus.SYNC_STATE

        ret = wait(lambda: icifc.get(SyncStatus.URI), timeout=timeout, interval=1, condition=all_done,
                   progress_cb=lambda ret: 'Status: {0}'.format((ret['entries']['https://localhost/mgmt/tm/cm/sync-status/0']['nestedStats']['entries']['status']['description'])))

        return ret


class Device(BaseApiObject):
    URI = '/mgmt/tm/cm/device'
    ITEM_URI = '/mgmt/tm/cm/device/%s'
    VALID_STATES = ['active', 'standby']

    def __init__(self, *args, **kwargs):
        super(Device, self).__init__(*args, **kwargs)

    @staticmethod
    def wait(rest, timeout=DEFAULT_TIMEOUT):

        def all_done(ret):
            states = [x.failoverState for x in ret['items']
                      if x.failoverState in Device.VALID_STATES]
            return len(states) == len(ret['items'])

        ret = wait(lambda: rest.get(Device.URI), timeout=timeout, interval=1,
                   condition=all_done,
                   progress_cb=lambda ret: 'States: {0}'.format([x.failoverState
                                                                 for x in ret['items']]))

        return ret


class iAppTemplate(BaseApiObject):
    URI = '/mgmt/shared/iapp/blocks'

    def __init__(self, *args, **kwargs):
        super(iAppTemplate, self).__init__(*args, **kwargs)
        self.setdefault('state', 'TEMPLATE')
        self.setdefault('name', 'Default Template Name')
        self.setdefault('audit', dict(intervalSeconds=0, policy='NOTIFY_ONLY'))
        self.setdefault('configurationProcessorReference', Reference())
        self.setdefault('statsProcessorReferences', ReferenceList())
        self.setdefault('inputProperties', list())


class FailoverState(BaseApiObject):
    URI = '/mgmt/tm/shared/bigip-failover-state'

    def __init__(self, *args, **kwargs):
        super(FailoverState, self).__init__(*args, **kwargs)


class DeviceGroup(BaseApiObject):
    URI = '/mgmt/tm/cm/device-group'

    def __init__(self, *args, **kwargs):
        super(DeviceGroup, self).__init__(*args, **kwargs)


class VirtualServer(BaseApiObject):
    URI = '/mgmt/tm/ltm/virtual'

    def __init__(self, *args, **kwargs):
        super(VirtualServer, self).__init__(*args, **kwargs)


class Node(BaseApiObject):
    URI = '/mgmt/tm/ltm/node'

    def __init__(self, *args, **kwargs):
        super(Node, self).__init__(*args, **kwargs)


class IApp(BaseApiObject):
    URI = '/mgmt/tm/cloud/services/iapp'

    def __init__(self, *args, **kwargs):
        super(IApp, self).__init__(*args, **kwargs)
