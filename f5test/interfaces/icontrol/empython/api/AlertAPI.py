from ..AlertClient import AlertClient
from ..MessageParser import Dictionary, Array, String

class AlertAPI(AlertClient):

    def signalAlertEvent(self):
        req = Dictionary()
        self.sendMsg('signalAlertEvent', req)

    def saveAlertInstance(self, instance):
        req = Dictionary()
        req.put('instance', Dictionary(instance))
        return self.sendMsg('saveAlertInstance', req)

    def updateDeviceAlerts(self, deviceUid, disabledAlertInstanceUids, enabledAlertInstanceUids):
        req = Dictionary()
        req.put('deviceUid', String(deviceUid))
        req.put('disabledAlertInstanceUids', Array(disabledAlertInstanceUids))
        req.put('enabledAlertInstanceUids', Array(enabledAlertInstanceUids))
        return self.sendMsg('updateDeviceAlerts', req)

    def deleteAlertInstance(self, uids):
        req = Dictionary()
        req.put('uids', Array(uids))
        self.sendMsg('deleteAlertInstance', req)

    def deleteAlertHistory(self, uids):
        req = Dictionary()
        req.put('uids', Array(uids))
        self.sendMsg('deleteAlertHistory', req)

    def setAlertConfig(self, defaultEmail = None, syslogServerAddress = None, maxHistoryEntries = None):
        req = Dictionary()
        if defaultEmail:
            req.put('defaultEmail', String(defaultEmail))
        if syslogServerAddress:
            req.put('syslogServerAddress', String(syslogServerAddress))
        if maxHistoryEntries:
            req.put('maxHistoryEntries', String(maxHistoryEntries))
        self.sendMsg('setAlertConfig', req)

    def updateDeviceGroupAlerts(self, deviceGroupUid, disabledAlertInstanceUids, enabledAlertInstanceUids):
        req = Dictionary()
        req.put('deviceGroupUid', String(deviceGroupUid))
        req.put('disabledAlertInstanceUids', Array(disabledAlertInstanceUids))
        req.put('enabledAlertInstanceUids', Array(enabledAlertInstanceUids))
        return self.sendMsg('updateDeviceGroupAlerts', req)

