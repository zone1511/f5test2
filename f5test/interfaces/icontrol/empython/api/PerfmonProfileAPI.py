from ..StatsClient import StatsClient
from ..MessageParser import Dictionary, Array, String

class PerfmonProfileAPI(StatsClient):

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

    def monitorProfileAssociateDeviceObject(self, deviceUid, profileUid = None, profileType = None, useDefault = None, objectName = None):
        req = Dictionary()
        req.put('deviceUid', String(deviceUid))
        if profileUid:
            req.put('profileUid', String(profileUid))
        if profileType:
            req.put('profileType', String(profileType))
        if useDefault:
            req.put('useDefault', String(useDefault))
        if objectName:
            req.put('objectName', String(objectName))
        self.sendMsg('monitorProfileAssociateDeviceObject', req)

    def monitorProfileSetDefault(self, profileUid):
        req = Dictionary()
        req.put('profileUid', String(profileUid))
        self.sendMsg('monitorProfileSetDefault', req)

