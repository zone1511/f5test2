'''
Created on Jul 25, 2013

@author: jono
'''
from ..base import SSHCommand
from ..ssh import key_exchange
from ....interfaces.ssh import SSHInterface
import logging

LOG = logging.getLogger(__name__)


update_bigip = None
class UpdateBigip(SSHCommand):  # @IgnorePep8
    """Run the update_bigip.sh against a device.
    """
    MARKER_FILE = '/tmp/RESTFramework_Installed_{0.version}_{0.build}'
    COMMAND = 'cd /usr/lib/dco/packages/upd-adc && ./update_bigip.sh -a {0} -p {1} {2}'

    def __init__(self, target, timeout=300, *args, **kwargs):
        super(UpdateBigip, self).__init__(timeout=timeout, *args, **kwargs)
        self.target = target

    def setup(self):
        filename = UpdateBigip.MARKER_FILE.format(self.ifc.version)
        found = False
        with SSHInterface(device=self.target) as sshifc:
            try:
                LOG.debug('Looking for %s on %s', filename, self.target)
                sshifc.api.sftp().stat(filename)
                found = True
                LOG.debug('Found!')
            except IOError:
                pass

        if not found:
            LOG.info('Running update_bigip...')
            key_exchange(self.target, ifc=self.ifc)

            ret = self.api.run(UpdateBigip.COMMAND \
                               .format(self.target.get_admin_creds().username,
                                self.target.get_admin_creds().password,
                                self.target.get_address()))
            LOG.debug(ret)
            with SSHInterface(device=self.target) as sshifc:
                with sshifc.api.sftp().open(filename, 'w'):
                    pass
