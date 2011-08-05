from ..AdminClient import AdminClient
from ..MessageParser import Dictionary, Array, String

class SystemInfoAPI(AdminClient):

    def systemInfoGetFilesystemStats(self, mountPoint):
        req = Dictionary()
        req.put('mountPoint', String(mountPoint))
        return self.sendMsg('systemInfoGetFilesystemStats', req)

    def systemInfoGetFilesystemDetail(self, filesystemName):
        req = Dictionary()
        req.put('filesystemName', String(filesystemName))
        return self.sendMsg('systemInfoGetFilesystemDetail', req)

    def systemInfoGetLocalHAInfo(self):
        req = Dictionary()
        return self.sendMsg('systemInfoGetLocalHAInfo', req)

