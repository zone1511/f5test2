from ..DeviceClient import DeviceClient
from ..MessageParser import Dictionary, Array, String

class Big3dInstallAPI(DeviceClient):

    def big3dInstallCreate(self, taskName, deviceUids, includePrivateKeys, continueOnError):
        req = Dictionary()
        req.put('taskName', String(taskName))
        req.put('deviceUids', Array(deviceUids))
        req.put('includePrivateKeys', String(includePrivateKeys))
        req.put('continueOnError', String(continueOnError))
        return self.sendMsg('big3dInstallCreate', req)

    def big3dInstallCancelJob(self, jobUid):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        self.sendMsg('big3dInstallCancelJob', req)

