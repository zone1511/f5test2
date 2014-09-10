'''
Created on Jul 25, 2013

@author: jono
'''
from ..base import SSHCommand
from ...base import CommandError
from ....interfaces.ssh import SSHInterface
from ....utils.wait import wait, WaitTimedOut
from ....interfaces.rest.emapi.objects import FailoverState
import logging
import json
import smtplib

LOG = logging.getLogger(__name__)

wait_ha_peer = None
class WaitHaPeer(SSHCommand):  # @IgnorePep8
    """Wait until the given devices is no longer in response.
    """
    COMMAND = 'restcurl /shared/identified-devices'

    def __init__(self, peers, timeout=120, session=None, *args, **kwargs):
        super(WaitHaPeer, self).__init__(*args, **kwargs)
        self.peers = peers
        self.timeout = timeout
        self.session = session

    def setup(self):
        ours = [x.get_discover_address() for x in self.peers]
        LOG.info('Waiting until {0} removed from /shared/identified-devices...'.format(self.peers))
        if not ours:
            LOG.info("No peers, do nothing.")
            return

        try:
            wait(lambda: json.loads(self.api.run(WaitHaPeer.COMMAND).stdout),
                 condition=lambda ret: not set(ours).intersection(set([x['address'] for x in ret['items']])),
                 progress_cb=lambda ret: [x['address'] for x in ret['items']],
                 timeout=self.timeout, interval=5)

        except WaitTimedOut:
            server = smtplib.SMTP('mail.f5net.com')
            server.sendmail('john.wong@f5.com', 'john.wong@f5.com',
                            'Subject: HA teardown issue, check %s' % self.session)
            server.quit()

wait_ha = None
class WaitHa(SSHCommand):  # @IgnorePep8
    """Wait until the given devices are out of PENDING state when setting up
       Active/Active HA.
    """
    COMMAND = 'restcurl /shared/gossip'

    def __init__(self, devices, timeout=300, *args, **kwargs):
        super(WaitHa, self).__init__(*args, **kwargs)
        self.devices = devices
        self.timeout = timeout

    def setup(self):
        if len(self.devices) == 1:
            LOG.info('Only 1 BIG-IQ in given in function so assuming HA is NOT setup.')
            return

        for device in self.devices:
            LOG.info('Waiting until {0} is finished PENDING...'.format(device))

            with SSHInterface(device=device) as sshifc:
                ret = wait(lambda: json.loads(sshifc.api.run(WaitHa.COMMAND).stdout),
                           condition=lambda ret: not ret['status'] in FailoverState.PENDING_STATES,
                           progress_cb=lambda ret: "{0}: {1}".format(device, ret['status']),
                           timeout=self.timeout)

                if ret['status'] != 'ACTIVE':
                    msg = json.dumps(ret['status'], sort_keys=True, indent=4, ensure_ascii=False)
                    raise CommandError("{0} failed.\n{1}".format(device, msg))
