'''
Created on May 22, 2014
@author: mathur

'''
from .base import DEFAULT_TIMEOUT
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
