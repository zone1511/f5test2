'''
Created on Feb 6, 2015

@author: jono
'''
from __future__ import absolute_import

import logging

from . import ExtendedPlugin


DEFAULT_TIMEOUT = 60
DEFAULT_HOSTNAME = 'irack.mgmt.pdsea.f5net.com'
LOG = logging.getLogger(__name__)


class IrackCheckin(ExtendedPlugin):
    """
    iRack plugin. Enable with ``--with-irack``. This plugin checks in/out
    devices from iRack: http://go/irack

    WARNING: This plugin expects an 'irack' section to be present at the ROOT
    of the test config (this is for backward compatibility).
    """
    enabled = False
    score = 490

    def configure(self, options, noseconfig):
        """ Call the super and then validate and call the relevant parser for
        the configuration file passed in """
        from ...interfaces.config import ConfigInterface

        super(IrackCheckin, self).configure(options, noseconfig)
        self.enabled = noseconfig.options.with_irack
        self.config_ifc = ConfigInterface()
        if self.enabled:
            config = self.config_ifc.open()
            assert config.irack, "iRack checkout requested but no irack section " \
                                 "found in the config."

    def finalize(self, result):
        from ...interfaces.rest.irack import IrackInterface
        LOG.info("Checking in devices to iRack...")

        config = self.config_ifc.open()
        irackcfg = config.irack
        res = irackcfg._reservation

        if not res:
            LOG.warning('No devices to be un-reserved.')
            return

        with IrackInterface(address=irackcfg.get('address', DEFAULT_HOSTNAME),
                            timeout=irackcfg.get('timeout', DEFAULT_TIMEOUT),
                            username=irackcfg.username,
                            password=irackcfg.apikey, ssl=False) as irack:

            try:
                ret = irack.api.from_uri(res).delete()
                LOG.debug("Checkin HTTP status: %s", ret.response.status)
            except:
                LOG.error("Exception occured while deleting reservation")
