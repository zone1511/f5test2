'''
Created on March 6, 2015
@author: jwong

'''
from ...base import BaseApiObject
from .....base import AttrDict

DEFAULT_DP_PATH = '/build/platform/cisco-apic/daily/current/F5DevicePackage.zip'


class aaaLogin(BaseApiObject):
    URI = '/api/aaaLogin'

    def __init__(self, *args, **kwargs):
        super(aaaLogin, self).__init__(*args, **kwargs)
        self.setdefault('aaaUser', AttrDict())
        self.aaaUser.setdefault('@name', 'admin')
        self.aaaUser.setdefault('@pwd', str())


class DevicePackage(BaseApiObject):
    UPLOAD_URI = '/ppi/node/mo'
    DELETE_URI = '/api/node/mo/uni/infra'
    URI = '/api/node/class/vnsMDev'

    def __init__(self, *args, **kwargs):
        super(DevicePackage, self).__init__(*args, **kwargs)
