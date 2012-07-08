from ..DeviceClient import DeviceClient
from ..MessageParser import Dictionary, String

class SwapDeviceAPI(DeviceClient):

    def swapDeviceCreateChecklist(self, deviceUid):
        req = Dictionary()
        req.put('deviceUid', String(deviceUid))
        self.sendMsg('swapDeviceCreateChecklist', req)

    def swapDeviceSetChecklistValue(self, deviceUid, name, value):
        req = Dictionary()
        req.put('deviceUid', String(deviceUid))
        req.put('name', String(name))
        req.put('value', String(value))
        self.sendMsg('swapDeviceSetChecklistValue', req)

    def swapDeviceSetCurrentButton(self, deviceUid, button):
        req = Dictionary()
        req.put('deviceUid', String(deviceUid))
        req.put('button', String(button))
        self.sendMsg('swapDeviceSetCurrentButton', req)

    def swapDeviceSetHostname(self, deviceUid, hostName):
        req = Dictionary()
        req.put('deviceUid', String(deviceUid))
        req.put('hostName', String(hostName))
        self.sendMsg('swapDeviceSetHostname', req)

    def swapDeviceSetRegkey(self, deviceUid, regkey):
        req = Dictionary()
        req.put('deviceUid', String(deviceUid))
        req.put('regkey', String(regkey))
        self.sendMsg('swapDeviceSetRegkey', req)

    def swapDeviceDeleteChecklist(self, deviceUid):
        req = Dictionary()
        req.put('deviceUid', String(deviceUid))
        self.sendMsg('swapDeviceDeleteChecklist', req)

