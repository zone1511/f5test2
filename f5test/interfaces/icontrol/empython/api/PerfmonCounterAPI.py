from ..StatsClient import StatsClient
from ..MessageParser import Dictionary, String

class PerfmonCounterAPI(StatsClient):

    def getStatsDescription(self):
        req = Dictionary()
        return self.sendMsg('getStatsDescription', req)

    def statsConnectionAdd(self, deviceAddress):
        req = Dictionary()
        req.put('deviceAddress', String(deviceAddress))
        self.sendMsg('statsConnectionAdd', req)

    def statsConnectionRemove(self, deviceAddress):
        req = Dictionary()
        req.put('deviceAddress', String(deviceAddress))
        self.sendMsg('statsConnectionRemove', req)

    def setMonitoringEnabled(self, enabled):
        req = Dictionary()
        req.put('enabled', String(enabled))
        self.sendMsg('setMonitoringEnabled', req)

    def setDeviceMonitoringEnabled(self, deviceUid, enabled):
        req = Dictionary()
        req.put('deviceUid', String(deviceUid))
        req.put('enabled', String(enabled))
        self.sendMsg('setDeviceMonitoringEnabled', req)

