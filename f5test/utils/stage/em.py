'''
Created on Feb 21, 2014

@author: jono
'''
from ...interfaces.config import (ConfigInterface, KEYSET_COMMON, KEYSET_LOCK,
                                  expand_devices)
from ...interfaces.icontrol import IcontrolInterface
from ...interfaces.ssh import SSHInterface
from ...macros.base import Macro
from ...macros.install import EMInstallSoftware
from .base import Stage, StageError
from ...base import Options

import f5test.commands.icontrol as ICMD
import f5test.commands.icontrol.em as EMAPI
import f5test.commands.shell as SCMD
import f5test.commands.shell.em as EMSQL
import logging
import time

DEFAULT_TIMEOUT = 600
DEFAULT_DISCOVERY_DELAY = 30
LOG = logging.getLogger(__name__)

__all__ = ['EMDiscocveryStage', 'EMInstallSoftwareStage']


class EMDiscocveryStage(Stage, Macro):
    """
    The stage where the EM Under Test discovers all target devices.
    """
    name = 'emdiscovery'
    parallelizable = False

    def __init__(self, device, specs, *args, **kwargs):
        self._context = specs.get('_context')
        self.device = device
        self.specs = specs
        self.to_discover = expand_devices(specs, 'devices')

        super(EMDiscocveryStage, self).__init__(*args, **kwargs)

    def setup(self):
        devices = self.to_discover
        assert devices, 'No devices to discover on DUT?'

        # XXX: Not sure why self IPs take a little longer to come up.
        if sum([x.specs._x_tmm_bug or 0 for x in devices
                               if x.get_discover_address() != x.get_address()]):
            delay = self.specs.get('delay', DEFAULT_DISCOVERY_DELAY)
            LOG.info('XXX: Waiting %d seconds for tmm to come up...' % delay)
            time.sleep(delay)
            for x in devices:
                x.specs._x_tmm_bug = False

        # Enable SSH access for this EM.
        with IcontrolInterface(device=self.device) as icifc:
            icifc.api.System.Services.set_ssh_access_v2(access={'state': 'STATE_ENABLED',
                                                                'addresses': 'ALL'})

        with SSHInterface(device=self.device) as ssh:
            reachable_devices = [int(x.is_local_em) and
                                    x.mgmt_address or
                                    x.access_address
                                 for x in
                                    EMSQL.device.get_reachable_devices(ifc=ssh)]

            to_discover = [Options(address=x.get_discover_address(),
                                   username=x.get_admin_creds().username,
                                   password=x.get_admin_creds().password)
                           for x in devices
                           if x.get_discover_address() not in reachable_devices
                              and not x.is_default()]  # 2.3+ autodiscover self

            # Set the autoRefreshEnabled to false to avoid AutoRefresh tasks.
            try:
                EMAPI.device.set_config(device=self.device)
            except Exception, e:
                LOG.warning("set_config() failed: %s", e)

            devices_ips = set([x.get_discover_address() for x in devices])
            to_delete = [x.uid for x in EMSQL.device.filter_device_info(ifc=ssh)
                               if x.access_address not in devices_ips
                               and not int(x.is_local_em)]
            if to_delete:
                LOG.info('Deleting device uids: %s', to_delete)
                uid = EMAPI.device.delete(to_delete, device=self.device)

            if to_discover:
                LOG.info("Discovering %s", to_discover)
                uid = EMAPI.device.discover(to_discover, device=self.device)
                task = EMSQL.device.GetDiscoveryTask(uid, ifc=ssh) \
                            .run_wait(lambda x: x['status'] != 'started',
                                      timeout=666,  # Sometimes it takes more.
                                      progress_cb=lambda x: 'discovery: %d%%' % x.progress_percent)
                summary = ''
                for detail in task.details:
                    if detail.discovery_status != 'ok':
                        summary += "%(access_address)s: " \
                                   "%(discovery_status)s - %(discovery_status_message)s\n" % detail

                assert (task['status'] == 'complete' and
                        task['error_count'] == 0), \
                        'Discovery failed: [{0}] {1}'.format(task.status, summary)

                # Look for impaired devices after discovery.
                for device in to_discover:
                    ret = EMSQL.device.get_device_state(device.address, ifc=ssh)
                    for status in ret:
                        if not status['status'] in ('big3d_below_minimum',
                                                    'big3d_update_required',
                                                    None):
                            raise StageError('Discovery incomplete: %s' % ret)

    def revert(self):
        super(EMDiscocveryStage, self).revert()
        if self._context:
            LOG.debug('In EMDiscocveryStage.revert()')
            self._context.get_interface(SSHInterface, device=self.device)


class EMInstallSoftwareStage(Stage, EMInstallSoftware):
    """
    This stage is used to perform legacy installations through a 3rd party EM.
    Legacy (9.x) installations are not supported natively, that is through
    image2disk or iControl.

    The convention is to use the 'x-em' alias for the 3rd party EM.
    """
    name = 'eminstall'

    def __init__(self, device, specs, *args, **kwargs):
        configifc = ConfigInterface()
        config = configifc.open()
        assert str(specs.version) in ('9.3.1', '9.4.3', '9.4.5', '9.4.6', '9.4.7',
                                      '9.4.8'), "Unsupported legacy version: %s" % specs.version
        options = Options(device=device, product=specs.product,
                          pversion=specs.version, pbuild=specs.build,
                          phf=specs.hotfix, image=specs.get('custom iso'),
                          hfimage=specs.get('custom hf iso'),
                          essential_config=specs.get('essential config'),
                          build_path=config.paths.build,
                          timeout=specs.get('timeout', DEFAULT_TIMEOUT))
        devices = []
        for device_ in expand_devices(specs, 'targets'):
            device = Options(device=device_,
                             address=device_.address,
                             username=device_.get_admin_creds(keyset=KEYSET_LOCK).username,
                             password=device_.get_admin_creds(keyset=KEYSET_LOCK).password)
            devices.append(device)
        super(EMInstallSoftwareStage, self).__init__(devices, options,
                                                     *args, **kwargs)

    def prep(self):
        ret = super(EMInstallSoftwareStage, self).prep()
        for device_attrs in self.devices:
            LOG.debug('Resetting password before: %s...', device_attrs.device)
            assert ICMD.system.set_password(device=device_attrs.device,
                                            keyset=KEYSET_COMMON)
            SCMD.ssh.remove_em(device=device_attrs.device)
        return ret

    def setup(self):
        ret = super(EMInstallSoftwareStage, self).setup()

        for device_attrs in self.devices:
            LOG.debug('Resetting password after: %s...', device_attrs.device)
            assert ICMD.system.set_password(device=device_attrs.device)

        return ret
