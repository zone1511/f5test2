'''
Created on April 17, 2014

@author: jwong
'''
from ..base import SSHCommand
from ..ssh import key_exchange
from ....interfaces.ssh import SSHInterface
import logging

LOG = logging.getLogger(__name__)


touch_bigip = None
class TouchBigip(SSHCommand):  # @IgnorePep8
    """Run 'touch /etc/bigstart/scripts/scim' against a device.
       Needed for BIG-IQ 4.2.0 upgrading bigip 11.4.1 635.0 and 637.0
    """
    COMMAND = 'touch /etc/bigstart/scripts/scim'

    def __init__(self, target, timeout=30, *args, **kwargs):
        super(TouchBigip, self).__init__(timeout=timeout, *args, **kwargs)
        self.target = target

    def setup(self):
        with SSHInterface(device=self.target) as sshifc:
            LOG.info('Running touch...')
            key_exchange(self.target, ifc=self.ifc)
            sshifc.api.run(TouchBigip.COMMAND)
