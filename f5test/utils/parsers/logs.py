'''
Created on Jan 4, 2012

@author: jono
'''
import logging
#from ...commands.shell import ssh as SCMD
LOG = logging.getLogger(__name__)

class LogTester(object):
    
    def __init__(self, filename, testcb, ifc):
        self.filename = filename
        self.testcb = testcb
        self.ifc = ifc
    
    def __enter__(self):
        #print SCMD.generic('id')
        ssh = self.ifc.api
        self._pre_stats = ssh.stat(self.filename)

    def __exit__(self, type, value, traceback): #@ReservedAssignment
        ssh = self.ifc.api
        self._post_stats = ssh.stat(self.filename)
        
        size_before = self._pre_stats.st_size
        size_after = self._post_stats.st_size
        delta = size_after - size_before
        LOG.debug('delta: %d', delta)

        ret = ssh.run('tail --bytes={0} {1}'.format(delta, self.filename))
        self.testcb(ret.stdout, self._post_stats)
