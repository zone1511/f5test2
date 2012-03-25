from ..SwimdClient import SwimdClient
from ..MessageParser import Dictionary, Array, String

class ASMSigInstallAPI(SwimdClient):

    def asmSigInstallCreateFromImage(self, imageUid):
        req = Dictionary()
        req.put('imageUid', String(imageUid))
        return self.sendMsg('asmSigInstallCreateFromImage', req)

    def asmSigInstallSetDevices(self, jobUid, deviceUids):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        req.put('deviceUids', Array(deviceUids))
        self.sendMsg('asmSigInstallSetDevices', req)

    def asmSigInstallSetOptions(self, jobUid, continueOnError):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        req.put('continueOnError', String(continueOnError))
        self.sendMsg('asmSigInstallSetOptions', req)

    def asmSigInstallStart(self, jobUid, taskName):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        req.put('taskName', String(taskName))
        self.sendMsg('asmSigInstallStart', req)

    def asmSigInstallCancelJob(self, jobUid):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        self.sendMsg('asmSigInstallCancelJob', req)

    def asmSigInstallDeleteJob(self, jobUid):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        self.sendMsg('asmSigInstallDeleteJob', req)

    def asmSigImageDelete(self, imageUids):
        req = Dictionary()
        req.put('imageUids', Array(imageUids))
        self.sendMsg('asmSigImageDelete', req)

