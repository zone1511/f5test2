from ..DeviceClient import DeviceClient
from ..MessageParser import Dictionary, Array, String

class EnableDisableAPI(DeviceClient):

    def enableDisableCreate(self, taskName, configObjects):
        req = Dictionary()
        req.put('taskName', String(taskName))
        req.put('configObjects', String(configObjects))
        return self.sendMsg('enableDisableCreate', req)

    def enableDisableSaveChanges(self, jobUid, taskName, comment):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        req.put('taskName', String(taskName))
        req.put('comment', String(comment))
        self.sendMsg('enableDisableSaveChanges', req)

    def enableDisableExecuteAction(self, jobUid, action):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        req.put('action', String(action))
        self.sendMsg('enableDisableExecuteAction', req)

    def enableDisableFinish(self, jobUid):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        self.sendMsg('enableDisableFinish', req)

