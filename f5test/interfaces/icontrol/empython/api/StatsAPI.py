from ..StatsClient import StatsClient
from ..MessageParser import Dictionary, Array, String

class StatsAPI(StatsClient):

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

    def monitorProfileCreate(self, name, profileType, description, interval):
        req = Dictionary()
        req.put('name', String(name))
        req.put('profileType', String(profileType))
        req.put('description', String(description))
        req.put('interval', String(interval))
        return self.sendMsg('monitorProfileCreate', req)

    def monitorProfileUpdate(self, profileUid, description, interval):
        req = Dictionary()
        req.put('profileUid', String(profileUid))
        req.put('description', String(description))
        req.put('interval', String(interval))
        self.sendMsg('monitorProfileUpdate', req)

    def monitorProfileUpdateCounter(self, profileUid, counterUid, enabled, minThreshold, maxThreshold):
        req = Dictionary()
        req.put('profileUid', String(profileUid))
        req.put('counterUid', String(counterUid))
        req.put('enabled', String(enabled))
        req.put('minThreshold', String(minThreshold))
        req.put('maxThreshold', String(maxThreshold))
        self.sendMsg('monitorProfileUpdateCounter', req)

    def monitorProfileUpdated(self, profileUid):
        req = Dictionary()
        req.put('profileUid', String(profileUid))
        self.sendMsg('monitorProfileUpdated', req)

    def monitorProfileDelete(self, profiles):
        req = Dictionary()
        req.put('profiles', Array(profiles))
        self.sendMsg('monitorProfileDelete', req)

    def monitorProfileAssociateDeviceObject(self, deviceUid, profileUid, objectName = None):
        req = Dictionary()
        req.put('deviceUid', String(deviceUid))
        req.put('profileUid', String(profileUid))
        if objectName:
            req.put('objectName', String(objectName))
        self.sendMsg('monitorProfileAssociateDeviceObject', req)

    def monitorProfileSetDefault(self, profileUid):
        req = Dictionary()
        req.put('profileUid', String(profileUid))
        self.sendMsg('monitorProfileSetDefault', req)

    def setMonitoringDbHaSyncEnabled(self, enabled):
        req = Dictionary()
        req.put('enabled', String(enabled))
        self.sendMsg('setMonitoringDbHaSyncEnabled', req)

