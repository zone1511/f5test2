import shlex
from . import subprocess
from ...base import Interface
import logging

LOG = logging.getLogger(__name__)


class CalledProcessError(subprocess.SubprocessError): 
    """This exception is raised when a process run by check_call() or
    check_output() returns a non-zero exit status.
    The exit status will be stored in the returncode attribute;
    check_output() will also store the output in the output attribute.
    """
    def __init__(self, returncode, cmd, output=None):
        self.returncode = returncode
        self.cmd = cmd
        self.output = output
    def __str__(self):
        return u"Command '%s' returned non-zero exit status %d" % (self.cmd, self.returncode)


class ShellInterface(Interface):
    
    def __init__(self, timeout=180, shell=False, *args, **kwargs):
        super(ShellInterface, self).__init__()
        self.timeout = timeout
        self.shell = shell

    def open(self): #@ReservedAssignment
        if self.api:
            return self.api
        self.api = ApiStub(self.timeout, self.shell)
        return self.api


class ApiStub(object):
    
    def __init__(self, timeout=None, shell=False):
        self.timeout = timeout
        self.shell = shell
    
    def run(self, command, fork=False, env=None, shell=None, stream=None):
        if shell is None:
            shell = self.shell
        
        if shell:
            args = command
        else:
            args = shlex.split(command)
        
        if stream is None:
            stream = subprocess.PIPE
        
        LOG.debug('run: %s', command)
        
        if fork:
            return subprocess.Popen(args,
                                    #stderr=LoggingProxy(LOG, logging.ERROR),
                                    #stdout=LoggingProxy(LOG, logging.INFO))
                                    shell=shell,
                                    stderr=stream,
                                    stdout=stream,
                                    env=env)
                             
        try:
            return subprocess.check_output(args,  
                                           timeout=self.timeout,
                                           shell=shell,
                                           stderr=subprocess.STDOUT,
                                           env=env)
        except subprocess.CalledProcessError, e:
            LOG.error(e.output)
            raise
        #return subprocess.check_output(['/bin/sh', '-c', command],  
        #                               timeout=self.timeout,
        #                               stderr=subprocess.STDOUT)
