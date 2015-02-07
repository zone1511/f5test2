'''
Created on Feb 21, 2014

@author: jono
'''
from ...interfaces.config import (ConfigInterface, KEYSET_COMMON)
from ...interfaces.ssh import SSHInterface
from ...macros.install import InstallSoftware
from .base import Stage
from ...base import Options

import f5test.commands.icontrol as ICMD
import f5test.commands.shell as SCMD
import logging
import datetime

DEFAULT_TIMEOUT = 600
LOG = logging.getLogger(__name__)


class InstallSoftwareStage(Stage, InstallSoftware):
    """
    Main installation stage. This is designed to work for BIGIP 10.0+ and EM
    2.0+. For BIGIP 9.x installations see EMInstallSoftwareStage.
    """
    name = 'install'

    def __init__(self, device, specs, *args, **kwargs):
        configifc = ConfigInterface()
        config = configifc.open()
        self._context = specs.get('_context')
        self.specs = specs
        self.device = device

        options = Options(device=device, product=specs.product,
                          pversion=specs.version, pbuild=specs.build,
                          phf=specs.hotfix, image=specs.get('custom iso'),
                          hfimage=specs.get('custom hf iso'),
                          format_volumes=specs.get('format volumes'),
                          format_partitions=specs.get('format partitions'),
                          essential_config=specs.get('essential config'),
                          build_path=config.paths.build,
                          timeout=specs.get('timeout', DEFAULT_TIMEOUT))
        super(InstallSoftwareStage, self).__init__(options, *args, **kwargs)

    def prep(self):
        super(InstallSoftwareStage, self).prep()
        if not self.specs.get('no reset password before'):
            LOG.info('Resetting password before install...')
            ICMD.system.SetPassword(device=self.options.device, keyset=KEYSET_COMMON).run_wait(timeout=120)

        if not self.specs.get('no remove em certs'):
            LOG.info('Removing EM certs...')
            SCMD.ssh.remove_em(device=self.options.device)

    def setup(self):
        ret = super(InstallSoftwareStage, self).setup()

        if not self.specs.get('no reset password after'):
            LOG.info('Resetting password after install...')
            ICMD.system.SetPassword(device=self.options.device).run_wait(timeout=60)

        if not self.has_essential_config:
            # This variable exists only on 11.0+. Used for 10.x -> 11.x HA upgrades.
            v = ICMD.system.get_version(device=self.device)
            if v.product.is_bigip and v >= 'bigip 11.0' and v < 'bigip 11.5' or \
               v.product.is_em and v >= 'em 3.0' or \
               v.product.is_bigiq and v < 'bigiq 4.1':
                LOG.info('Waiting on Trust.configupdatedone DB variable...')
                ICMD.management.GetDbvar('Trust.configupdatedone',
                                         device=self.options.device).\
                                         run_wait(lambda x: x == 'true', timeout=300)

            self.options.device.specs.has_tmm_restarted = datetime.datetime.now()

        return ret

    def revert(self):
        super(InstallSoftwareStage, self).revert()
        if self._context:
            LOG.debug('In InstallSoftwareStage.revert()')
            device = self.options.device
            # If the installation has failed before rebooting then no password
            # change is needed.
            #ICMD.system.set_password(device=self.options.device)
            self._context.get_interface(SSHInterface, device=device)
