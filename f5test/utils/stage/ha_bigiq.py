'''
Created on Feb 10, 2015

@author: jwong
'''
from ...interfaces.config import ConfigInterface
from ...interfaces.ssh import SSHInterface
from ...macros.ha_bigiq import HABigiqMacro
from .base import Stage
from ...base import Options
from f5test.commands.rest.device import DEFAULT_ALLBIGIQS_GROUP
import logging

LOG = logging.getLogger(__name__)


class HABigiqStage(Stage, HABigiqMacro):
    """
    Cofigure BIG-IQ Active-Active HA two or more BIGIQ 4.3.0+ devices.
    """
    name = 'ha_bigiq'

    def __init__(self, device, specs=None, *args, **kwargs):
        configifc = ConfigInterface()
        self.devices = configifc.get_device_groups()[DEFAULT_ALLBIGIQS_GROUP]
        default = next(x for x in self.devices if x.is_default())
        peers = [x for x in self.devices if x != default]

        options = Options(reset=specs.get("reset"),
                          timeout=specs.get("timeout"),
                          ha_passive=specs.get("ha_passive"))
        self._context = specs.get('_context')

        super(HABigiqStage, self).__init__(options, default=default,
                                           peers=peers)

    def revert(self):
        super(HABigiqStage, self).revert()
        if self._context:
            LOG.debug('In HAStage.revert()')
            for device in self.devices:
                self._context.get_interface(SSHInterface, device=device)
