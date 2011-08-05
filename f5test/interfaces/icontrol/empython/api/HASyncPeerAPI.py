from ..AdminClient import AdminClient
from ..MessageParser import Dictionary, Array, String

class HASyncPeerAPI(AdminClient):

    def haSyncPeerPullConfig(self):
        req = Dictionary()
        self.sendMsg('haSyncPeerPullConfig', req)

    def haSyncPeerPushConfig(self):
        req = Dictionary()
        self.sendMsg('haSyncPeerPushConfig', req)

    def haSyncPeerStatus(self, status):
        req = Dictionary()
        req.put('status', String(status))
        self.sendMsg('haSyncPeerStatus', req)

    def haSyncPeerFinished(self, status):
        req = Dictionary()
        req.put('status', String(status))
        self.sendMsg('haSyncPeerFinished', req)

