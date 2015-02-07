'''
Created on Jan 7th, 2015

@author: a.dobre@f5.com
'''
import logging
from . import ExtendedPlugin, PLUGIN_NAME
from ...interfaces.config import expand_devices
from ...commands.aws.ec2.common import (wait_to_start_instances_by_id,
                                        wait_to_stop_instances_by_id)
import f5test.defaults as F5D

LOG = logging.getLogger(__name__)


class Ec2Stages(ExtendedPlugin):
    """
    Starts and Stops EC2 duts.
    """
    enabled = False
    name = 'ec2_stages'

    def options(self, parser, env):
        """Register commandline options."""
        parser.add_option('--with-ec2_stages', action='store_true',
                          default=False,
                          help="Enable Start/Stop of Ec2 Duts. (default: no)")
        parser.add_option('--no-dut-stop', action='store_true',
                          dest='no_dutstop', default=False,
                          help="Disable Stopping the DUTs.")

    def configure(self, options, noseconfig):
        super(Ec2Stages, self).configure(options, noseconfig)

        from ...interfaces.testcase import ContextHelper
        from ...interfaces.config import ConfigInterface

        self.data = ContextHelper().set_container(PLUGIN_NAME)
        self.cfgifc = ConfigInterface()

        self.enabled = noseconfig.options.with_ec2_stages or self.enabled
        self.ec2s = {}

        if self.enabled:
            instances = options.instances
            for ec2 in self.cfgifc.get_all_devices(kind=F5D.KIND_CLOUD_EC2):
                instances = set(ec2.specs.instances).intersection(set(instances))
                if instances:
                    self.ec2s[ec2] = [x.specs.instanceid for x in expand_devices(instances)]

    def begin(self):
        """start duts
        """

        LOG.info('EC2 Start Duts Nose Stage...')

        for ec2, instances in self.ec2s.items():
            LOG.info('Starting instances: {0}'.format(instances))
            LOG.info("Connecting to AWS EC2 API for [{0}]..."
                     .format(ec2))
            wait_to_start_instances_by_id(instances, timeout=720, device=ec2)

    def finalize(self, result):
        """stop duts
        """

        if not self.data.nose_config.options.no_dutstop:
            LOG.info('EC2 Stop Duts Nose Stage...')
            for ec2, instances in self.ec2s.items():
                LOG.info('Stopping instances {0}'.format(instances))
                LOG.info("Connecting to AWS EC2 API for [{0}]..."
                         .format(ec2))
                wait_to_stop_instances_by_id(instances, timeout=600, device=ec2)
