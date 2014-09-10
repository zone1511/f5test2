'''
Created on Feb 21, 2014

@author: jono
'''
from .base import Stage
from ...base import Options
from ...interfaces.config import (ConfigInterface, KEYSET_COMMON, KEYSET_DEFAULT,
                                  KEYSET_LOCK)
from ...interfaces.icontrol import IcontrolInterface
from ...interfaces.ssh import SSHInterface
from ...macros.base import Macro
from ...macros.keyswap import KeySwap
from ...macros.tmosconf.placer import ConfigPlacer

import f5test.commands.icontrol as ICMD
import f5test.commands.shell as SCMD
import datetime
import logging

DEFAULT_TIMEOUT = 600
LOG = logging.getLogger(__name__)


class ConfigStage(Stage, ConfigPlacer):
    """
    This stage makes sure the devices are configured with the 'stock' settings.
    Its functionally is similar to the f5.configurator CLI utility.
    """
    name = 'config'

    def __init__(self, device, specs, *args, **kwargs):
        configifc = ConfigInterface()
        config = configifc.open()
        password = configifc.get_device(device).get_root_creds().password
        self._context = specs.get('_context')
        common = config.get('platform', Options())

        options = Options(device=device,
                          ssh_port=device.ports.get('ssh'),
                          ssl_port=device.ports.get('https'),
                          license=specs.get('license'),
                          timezone=specs.get('timezone',
                                             common.get('timezone')),
                          timeout=specs.get('timeout'),
                          selfip_internal=specs.get('selfip internal'),
                          selfip_external=specs.get('selfip external'),
                          vlan_internal=specs.get('vlan internal'),
                          vlan_external=specs.get('vlan external'),
                          trunks_lacp=specs.get('trunks lacp'),
                          provision=specs.get('provision'),
                          partitions=specs.get('partitions'),
                          node_count=specs.get('node count'),
                          pool_count=specs.get('pool count'),
                          vip_count=specs.get('vip count'),
                          pool_members=specs.get('pool members'),
                          node_start=specs.get('node start'),
                          vip_start=specs.get('vip start'),
                          no_irack=specs.get('no irack'),
                          hostname=specs.get('hostname'),
                          dns_servers=specs.get('dns servers',
                                                common.get('dns servers')),
                          dns_suffixes=specs.get('dns suffixes',
                                                 common.get('dns suffixes')),
                          ntp_servers=specs.get('ntp servers',
                                                common.get('ntp servers')),
                          password=password)

        if config.irack:
            options.irack_address = config.irack.address
            options.irack_username = config.irack.username
            options.irack_apikey = config.irack.apikey

        super(ConfigStage, self).__init__(options, *args, **kwargs)

    def setup(self):
        ret = super(ConfigStage, self).setup()
        LOG.debug('Locking device %s...', self.options.device)
        ICMD.system.SetPassword(device=self.options.device).run_wait(timeout=60)
        self.options.device.specs._x_tmm_bug = True
        self.options.device.specs.configure_done = datetime.datetime.now()
        self.options.device.specs.is_cluster = SCMD.ssh.is_cluster(device=self.options.device)

        return ret

    def revert(self):
        super(ConfigStage, self).revert()
        if self._context:
            LOG.debug('In ConfigStage.revert()')
            device = self.options.device
            # If the installation has failed before rebooting then no password
            # change is needed.
            #ICMD.system.set_password(device=self.options.device)
            self._context.get_interface(SSHInterface, device=device)


class SetPasswordStage(Stage, Macro):
    """
    A teardown stage that resets the password on configured devices.
    """
    name = 'setpassword'

    def __init__(self, device, specs=None, *args, **kwargs):
        self.device = device
        self.specs = specs
        super(SetPasswordStage, self).__init__(*args, **kwargs)

    def run(self):
        LOG.debug('Unlocking device %s', self.device)
        keysets = Options(default=KEYSET_DEFAULT, common=KEYSET_COMMON, lock=KEYSET_LOCK)
        ICMD.system.set_password(device=self.device,
                                 keyset=keysets.get(self.specs.keyset, KEYSET_COMMON))

        # Save the config after password change otherwise it will be reverted
        # upon reboot.
        with IcontrolInterface(device=self.device) as icifc:
            icifc.api.System.ConfigSync.save_configuration(filename='',
                                                           save_flag="SAVE_HIGH_LEVEL_CONFIG")


class KeySwapStage(Stage, KeySwap):
    """
    This stage makes sure the SSH keys are exchanged between the test runner
    system and the devices.
    """
    name = 'keyswap'

    def __init__(self, device, specs=None, *args, **kwargs):
        options = Options(device=device)
        super(KeySwapStage, self).__init__(options, *args, **kwargs)
