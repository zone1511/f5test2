from ..AdminClient import AdminClient
from ..MessageParser import Dictionary, Array, String

class ASMSigUpdateAPI(AdminClient):

    def asmSigUpdateCreate(self, isScheduled):
        req = Dictionary()
        req.put('isScheduled', String(isScheduled))
        return self.sendMsg('asmSigUpdateCreate', req)

    def asmSigUpdateFetchImages(self, jobUid, signatureUids):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        req.put('signatureUids', Array(signatureUids))
        self.sendMsg('asmSigUpdateFetchImages', req)

    def asmSigUpdateSetSchedule(self, interval, hour, minute, ampm, dayOfWeek, dayOfMonth, autoDownload):
        req = Dictionary()
        req.put('interval', String(interval))
        req.put('hour', String(hour))
        req.put('minute', String(minute))
        req.put('ampm', String(ampm))
        req.put('dayOfWeek', String(dayOfWeek))
        req.put('dayOfMonth', String(dayOfMonth))
        req.put('autoDownload', String(autoDownload))
        self.sendMsg('asmSigUpdateSetSchedule', req)

    def asmSigUpdateRemoveSchedule(self):
        req = Dictionary()
        self.sendMsg('asmSigUpdateRemoveSchedule', req)

    def asmSigUpdateCancelJob(self, jobUid):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        self.sendMsg('asmSigUpdateCancelJob', req)

    def asmSigUpdateDeleteJob(self, jobUid):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        self.sendMsg('asmSigUpdateDeleteJob', req)

