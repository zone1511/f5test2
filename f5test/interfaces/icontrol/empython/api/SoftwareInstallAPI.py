from ..SwimdClient import SwimdClient
from ..MessageParser import Dictionary, Array, String

class SoftwareInstallAPI(SwimdClient):

    def softwareInstallGetDeviceList(self, imageUid, hotfixUid):
        req = Dictionary()
        req.put('imageUid', String(imageUid))
        req.put('hotfixUid', String(hotfixUid))
        return self.sendMsg('softwareInstallGetDeviceList', req)

    def softwareInstallCreate(self, imageUid, hotfixUid, devices, includePrivateKeys, continueOnError, taskName):
        req = Dictionary()
        req.put('imageUid', String(imageUid))
        req.put('hotfixUid', String(hotfixUid))
        req.put('devices', Array(devices))
        req.put('includePrivateKeys', String(includePrivateKeys))
        req.put('continueOnError', String(continueOnError))
        req.put('taskName', String(taskName))
        return self.sendMsg('softwareInstallCreate', req)

    def softwareInstallCancelJob(self, jobUid):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        self.sendMsg('softwareInstallCancelJob', req)

