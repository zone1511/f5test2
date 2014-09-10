'''
Created on Feb 21, 2014

@author: jono
'''
from .base import Stage, StageError
from ...macros.base import Macro
from ...base import enum
import logging
from ...interfaces.aws import AwsInterface
from ...commands.aws.ec2.common import wait_to_start_instances_by_id, \
                                       wait_to_stop_instances_by_id

LOG = logging.getLogger(__name__)
OPERATION = enum('start', 'stop')


class Ec2Stage(Stage, Macro):
    """
    Start stop EC2 instances.
    """
    name = 'deploy-ec2'

    def __init__(self, device, specs=None, *args, **kwargs):
        self.device = device
        self.specs = specs
        self._context = specs.get('_context')
        super(Ec2Stage, self).__init__(*args, **kwargs)

    def setup(self):
        super(Ec2Stage, self).setup()
        s = self.specs
        LOG.info('EC2 deploy for: %s', self.device)
        if s.operation == OPERATION.start:
            LOG.info('Starting instances %s', s.instances)
            # Connecting to AWS EC2 API. # MANDATORY
            LOG.info("Connecting to AWS EC2 API...")
            with AwsInterface(region=self.device.specs.region,
                              key_id=self.device.get_creds().username,
                              access_key=self.device.get_creds().password) as awsifc:
                wait_to_start_instances_by_id(s.instances, timeout=720, ifc=awsifc)
            # give time to stabalize. To DO in future: this should check for restjavad
            import time
            time.sleep(300)
        elif s.operation == OPERATION.stop:
            LOG.info('Stopping instances %s', s.instances)
            # Connecting to AWS EC2 API. # MANDATORY
            LOG.info("Connecting to AWS EC2 API...")
            with AwsInterface(region=self.device.specs.region,
                              key_id=self.device.get_creds().username,
                              access_key=self.device.get_creds().password) as awsifc:
                wait_to_stop_instances_by_id(s.instances, timeout=600, ifc=awsifc)
        else:
            raise StageError('Unknown operation "%s" for %s stage' %
                             (s.operation, self.name))
