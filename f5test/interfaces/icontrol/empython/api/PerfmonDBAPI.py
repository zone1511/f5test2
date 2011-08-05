from ..StatsClient import StatsClient
from ..MessageParser import Dictionary, Array, String

class PerfmonDBAPI(StatsClient):

    def getMonitoringTotalSpaceAvailable(self):
        req = Dictionary()
        return self.sendMsg('getMonitoringTotalSpaceAvailable', req)

    def getMonitoringSpaceInUse(self):
        req = Dictionary()
        return self.sendMsg('getMonitoringSpaceInUse', req)

    def getMonitoringEstimatedNumDaysCurrent(self):
        req = Dictionary()
        return self.sendMsg('getMonitoringEstimatedNumDaysCurrent', req)

    def getMonitoringEstimatedNumDaysWithAllocatedSpace(self, allocatedSpace):
        req = Dictionary()
        req.put('allocatedSpace', String(allocatedSpace))
        return self.sendMsg('getMonitoringEstimatedNumDaysWithAllocatedSpace', req)

    def setMonitoringDbAllocatedSpace(self, allocatedSpace):
        req = Dictionary()
        req.put('allocatedSpace', String(allocatedSpace))
        self.sendMsg('setMonitoringDbAllocatedSpace', req)

    def setMonitoringDbRemoteAccessInfo(self, allow, password):
        req = Dictionary()
        req.put('allow', String(allow))
        req.put('password', String(password))
        self.sendMsg('setMonitoringDbRemoteAccessInfo', req)

    def setMonitoringDbHaSyncEnabled(self, enabled):
        req = Dictionary()
        req.put('enabled', String(enabled))
        self.sendMsg('setMonitoringDbHaSyncEnabled', req)

