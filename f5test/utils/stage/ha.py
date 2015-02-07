'''
Created on Feb 21, 2014

@author: jono
'''
from ...interfaces.config import (ConfigInterface, expand_devices)
from ...interfaces.ssh import SSHInterface
from ...macros.ha import FailoverMacro
from .base import Stage
from ...base import Options

import logging

LOG = logging.getLogger(__name__)


class HAStage(Stage, FailoverMacro):
    """
    Create a CMI Device Group for Failover and Config Sync between two or more
    BIGIP 11.0+ devices or EM 3.0+.
    """
    name = 'ha'

    def __init__(self, device, specs=None, *args, **kwargs):
        configifc = ConfigInterface()
        authorities = [device] + list(expand_devices(specs, 'authorities') or [])
        peers = list(expand_devices(specs, 'peers') or [])
        groups = specs.groups or configifc.get_device_groups(authorities + peers).keys()

        options = Options(specs.options)
        if options.set_active:
            options.set_active = configifc.get_device(options.set_active)
        self._context = specs.get('_context')

        super(HAStage, self).__init__(options, authorities, peers, groups)

    def revert(self):
        super(HAStage, self).revert()
        if self._context:
            LOG.debug('In HAStage.revert()')
            for device in self.cas + self.peers:
                self._context.get_interface(SSHInterface, device=device)
