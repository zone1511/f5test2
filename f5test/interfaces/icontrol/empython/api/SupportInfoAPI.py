from ..DeviceClient import DeviceClient
from ..MessageParser import Dictionary, Array, String

class SupportInfoAPI(DeviceClient):

    def supportInfoCreate(self, caseNumber):
        req = Dictionary()
        req.put('caseNumber', String(caseNumber))
        return self.sendMsg('supportInfoCreate', req)

    def supportInfoSetAdditionalInfo(self, jobUid, additionalInfo):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        req.put('additionalInfo', String(additionalInfo))
        self.sendMsg('supportInfoSetAdditionalInfo', req)

    def supportInfoSetOptions(self, jobUid, qkviewArgs):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        req.put('qkviewArgs', String(qkviewArgs))
        self.sendMsg('supportInfoSetOptions', req)

    def supportInfoAddDevices(self, jobUid, deviceUids):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        req.put('deviceUids', Array(deviceUids))
        self.sendMsg('supportInfoAddDevices', req)

    def supportInfoDeleteDevices(self, jobUid, deviceUids):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        req.put('deviceUids', Array(deviceUids))
        self.sendMsg('supportInfoDeleteDevices', req)

    def supportInfoGatherInfo(self, jobUid):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        self.sendMsg('supportInfoGatherInfo', req)

    def supportInfoCancelGatherInfo(self, jobUid):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        self.sendMsg('supportInfoCancelGatherInfo', req)

    def supportInfoAddAttachment(self, jobUid, tmpFilePath, actualFileName):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        req.put('tmpFilePath', String(tmpFilePath))
        req.put('actualFileName', String(actualFileName))
        self.sendMsg('supportInfoAddAttachment', req)

    def supportInfoDeleteAttachments(self, jobUid, filePaths):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        req.put('filePaths', Array(filePaths))
        self.sendMsg('supportInfoDeleteAttachments', req)

    def supportInfoCreateArchive(self, jobUid):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        self.sendMsg('supportInfoCreateArchive', req)

    def supportInfoSetDestination(self, jobUid, targetType, targetDir, ftpServer, ftpServerPort, ftpLogin, ftpPassword):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        req.put('targetType', String(targetType))
        req.put('targetDir', String(targetDir))
        req.put('ftpServer', String(ftpServer))
        req.put('ftpServerPort', String(ftpServerPort))
        req.put('ftpLogin', String(ftpLogin))
        req.put('ftpPassword', String(ftpPassword))
        self.sendMsg('supportInfoSetDestination', req)

    def supportInfoGetArchiveFilePath(self, jobUid):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        return self.sendMsg('supportInfoGetArchiveFilePath', req)

    def supportInfoSendInfo(self, jobUid):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        self.sendMsg('supportInfoSendInfo', req)

    def supportInfoFinishJob(self, jobUid):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        self.sendMsg('supportInfoFinishJob', req)

    def supportInfoDeleteJob(self, jobUid):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        self.sendMsg('supportInfoDeleteJob', req)

