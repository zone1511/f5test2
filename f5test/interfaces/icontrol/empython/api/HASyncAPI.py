from ..AdminClient import AdminClient
from ..MessageParser import Dictionary, Array, String

class HASyncAPI(AdminClient):

    def haSyncSetSchedule(self, interval, hour, minute, ampm, dayOfWeek, dayOfMonth):
        req = Dictionary()
        req.put('interval', String(interval))
        req.put('hour', String(hour))
        req.put('minute', String(minute))
        req.put('ampm', String(ampm))
        req.put('dayOfWeek', String(dayOfWeek))
        req.put('dayOfMonth', String(dayOfMonth))
        self.sendMsg('haSyncSetSchedule', req)

    def haSyncRemoveSchedule(self):
        req = Dictionary()
        self.sendMsg('haSyncRemoveSchedule', req)

    def haSyncPerformSync(self, syncType):
        req = Dictionary()
        req.put('syncType', String(syncType))
        return self.sendMsg('haSyncPerformSync', req)

