from ..DeviceClient import DeviceClient
from ..MessageParser import Dictionary, String

class DeviceMaintenanceModeAPI(DeviceClient):

    def deviceSetMaintenanceMode(self, deviceUid, mode, reason):
        req = Dictionary()
        req.put('deviceUid', String(deviceUid))
        req.put('mode', String(mode))
        req.put('reason', String(reason))
        self.sendMsg('deviceSetMaintenanceMode', req)

