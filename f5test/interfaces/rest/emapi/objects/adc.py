'''
Created on sept 15, 2014

/mgmt/cm/adc workers

@author: a.dobre@f5.com
'''
from .....utils.wait import wait
from .base import Reference, ReferenceList, Task, DEFAULT_TIMEOUT
from ...base import BaseApiObject


class AdcDiscoveryWorker(Task):
    URI = '/mgmt/cm/adc/provider/discovery'

    def __init__(self, *args, **kwargs):
        super(AdcDiscoveryWorker, self).__init__(*args, **kwargs)
        self.setdefault('enabled', True)


class Config(BaseApiObject):
    URI = '/mgmt/cm/adc/config'

    def __init__(self, *args, **kwargs):
        super(Config, self).__init__(*args, **kwargs)
        self.setdefault('configPathScope', 'full')
        self.setdefault('deviceReferenceUri', '')


class RefreshCurrentConfig(Task):
    URI = '/mgmt/cm/shared/config/refresh-current-config'

    def __init__(self, *args, **kwargs):
        super(RefreshCurrentConfig, self).__init__(*args, **kwargs)
        self.setdefault('configPaths', [])
        self.setdefault('deviceReference', Reference())

class Conflict(Task):
    URI = '/mgmt/shared/gossip-conflicts'

    def __init__(self, *args, **kwargs):
        super(Conflict, self).__init__(*args, **kwargs)
