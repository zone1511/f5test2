from ..AdminClient import AdminClient
from ..MessageParser import Dictionary, String

class PerfmonDBMaintenanceAPI(AdminClient):

    def setMonitoringDbBackupSchedule(self, remoteUser, remoteHostname,
                    remotePath, interval,
                    hour = None, minute = None, ampm = None,
                    dayOfWeek = None, dayOfMonth = None):
        req = Dictionary()
        req.put('interval', String(interval))
        if hour:
            req.put('hour', String(hour))
        if minute:
            req.put('minute', String(minute))
        if ampm:
            req.put('ampm', String(ampm))
        if dayOfWeek:
            req.put('dayOfWeek', String(dayOfWeek))
        if dayOfMonth:
            req.put('dayOfMonth', String(dayOfMonth))
        req.put('remoteUser', String(remoteUser))
        req.put('remoteHostname', String(remoteHostname))
        req.put('remotePath', String(remotePath))
        self.sendMsg('setMonitoringDbBackupSchedule', req)

    def removeMonitoringDbBackupSchedule(self):
        req = Dictionary()
        self.sendMsg('removeMonitoringDbBackupSchedule', req)

