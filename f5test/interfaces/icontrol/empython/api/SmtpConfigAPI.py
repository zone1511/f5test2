'''
Created on Apr 5, 2012

@author: jono
'''
from ..AdminClient import AdminClient
from ..MessageParser import Dictionary, String

class SmtpConfigAPI(AdminClient):

    def smtpConfigGetNames(self):
        req = Dictionary()
        return self.sendMsg('smtpConfigGetNames', req)

    def smtpConfigSetName(self, name):
        req = Dictionary()
        req.put('name', String(name))
        self.sendMsg('smtpConfigSetName', req)
