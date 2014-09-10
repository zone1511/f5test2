from .base import SSHCommand, SSHCommandError
import logging

LOG = logging.getLogger(__name__) 


#class BigpipeCommand(SSHCommand):
#    
#    def setup(self):
#        """Bigpipe will not be available in BIGIP 11.0.0+ and EM 3.0.1+
#        
#        Still supporting EM 3.0.0 as it's unclear whether we drop BP support
#        or not.
#        """
#        this_version = get_version(self.ssh)
#        if this_version >= 'bigip 11.0.0' or this_version > 'em 3.0.1':
#            raise CommandNotSupported('only in BIGIP < 11.0.0 and EM <= 3.0.1 not %s' % this_version)

#list_software = None
#class ListSoftware(CachedCommand, BigpipeCommand):
#    
#    def setup(self):
#        super(ListSoftware, self).setup()
#
#        LOG.info('bigpipe software desired list on %s...', self.ssh)
#                
#        if get_version(self.ssh) < 'bigip 10.0.1' or \
#           get_version(self.ssh) < 'em 1.6.0':
#            raise CommandNotSupported('only in BIGIP >= 10.0.1 and EM >= 1.6')
#        
#        ret = self.ssh.run('bigpipe software list')
#        if not ret.status:
#            # XXX: bigpipe list output is not compatible with tmsh parser.
#            #return tmsh_to_dict(ret.stdout)
#            return ret.stdout
#        else:
#            LOG.error(ret)

generic = None
class Generic(SSHCommand):
    """Run a generic one line bigpipe command.
    
    >>> bigpipe.generic('system list')
    system {
       gui setup disable
       hostname "bp6800-122.mgmt.pdsea.f5net.com"
    }

    @param command: the arguments for bigpipe
    @type command: str
    """
    def __init__(self, command, *args, **kwargs):
        
        super(Generic, self).__init__(*args, **kwargs)
        self.command = command

    def setup(self):
        LOG.info('bigpipe %s on %s...', self.command, self.api)
                
        ret = self.api.run('bigpipe %s' % self.command)
        if not ret.status:
            # XXX: bigpipe list output is not compatible with tmsh parser.
            #return tmsh_to_dict(ret.stdout)
            return ret
        else:
            raise SSHCommandError(ret)

