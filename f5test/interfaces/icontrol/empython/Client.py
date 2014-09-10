from .MessageParser import String, parseResult, to_python, ParsingError
import time
import logging

LOG = logging.getLogger(__name__)


class Client:
    
    def __init__(self, msgType, icontrol):
        self.msgType = msgType
        self.icontrol = icontrol
        self.retries = 60
        self.retry_interval = 1

    def formatMsg(self, taskName, request):
        request.put('username', String(self.icontrol.username))
        msgLst = ['<?xml version="1.0" ?><request><version>904</version><taskName>', taskName,
            '</taskName><args>', request.to_string(), '</args></request>']
        msgTxt = ''.join(msgLst)
        return msgTxt

    def sendMsg(self, taskName, request):
        packetTxt = self.formatMsg(taskName, request)
        
        for _ in range(self.retries):
            LOG.debug('request: %s', packetTxt)
            ret = self.icontrol.Management.EM.sendRequest(daemon=self.msgType,
                                                           request=packetTxt)
            LOG.debug('response: %s', ret)
            try:
                return to_python(parseResult(ret))
            except ParsingError, e:
                if e.errno == 19:
                    LOG.info('EM returned locked status')
                    time.sleep(self.retry_interval)
                else:
                    raise
