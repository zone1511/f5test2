'''
Created on Feb 9, 2012

@author: jono
'''
from __future__ import absolute_import
from f5test.macros.confgen import ConfigGenerator
from f5test.macros.keyswap import KeySwap
from f5test.macros.ha import FailoverMacro
from f5test.interfaces.testopia import TestopiaInterface
from f5test.interfaces.config import (expand_devices, ConfigInterface,
                                      KEYSET_COMMON, KEYSET_LOCK,
    KEYSET_DEFAULT)
from f5test.interfaces.ssh import SSHInterface
from f5test.interfaces.icontrol import IcontrolInterface
from f5test.interfaces.subprocess import ShellInterface
from f5test.interfaces.testcase import ContextHelper
from f5test.macros.base import Macro, Stage
from f5test.macros.install import InstallSoftware, EMInstallSoftware
import f5test.commands.icontrol as ICMD
import f5test.commands.shell as SCMD
import f5test.commands.icontrol.em as EMAPI
import f5test.commands.shell.em as EMSQL
from nose.config import _bool
import inspect
import os
import time

from f5test.macros.base import MacroThread, StageError
from f5test.base import Options
from Queue import Queue
import traceback
import logging

LOG = logging.getLogger(__name__)
DEFAULT_PRIORITY = 100
DEFAULT_TIMEOUT = 600
DEFAULT_DISCOVERY_DELAY = 30
ENABLE_KEY = '_enabled'


def carry_flag(d, flag=None):
    """
    Given the dict:
    key1:
        _enabled: 1
        subkey1:
            key: val
        subkey2:
            key: val

    The resulting dict after running carry_flag() on it will be:
    key1:
        _enabled: 1
        subkey1:
            _enabled: 1
            key: val
        subkey2:
            _enabled: 1
            key: val
    """
    if flag != None:
        d.setdefault(ENABLE_KEY, flag)
    else:
        flag = d.get(ENABLE_KEY)

    for v in d.itervalues():
        if isinstance(v, dict):
            carry_flag(v, flag)


def process_stages(stages, section, context):
    if not stages:
        LOG.debug('No stages found.')
        return

    # Replicate the "_enabled" flag.
    carry_flag(stages)

    # Build the stage map with *ALL* defined stage classes in this file.
    stages_map = {}
    for value in globals().values():
        if inspect.isclass(value) and issubclass(value, Stage) and value != Stage:
            stages_map[value.name] = value

    # Focus only on our stages section
    for key in section.split('.'):
        stages = stages.get(key, Options())

    # Sort stages by priority attribute and stage name.
    stages = sorted(stages.iteritems(), key=lambda x: (isinstance(x[1], dict) and
                                                      x[1].get('priority',
                                                               DEFAULT_PRIORITY),
                                                      x[0]))

    config = ConfigInterface().config
    # Group stages of the same type. The we spin up one thread per stage in a
    # group and wait for threads within a group to finish.
    sg_dict = {}
    sg_list = []
    for name, specs in stages:
        if not specs or name.startswith('_'):
            continue

        specs = Options(specs)
        key = specs.get('group', "{0}-{1}".format(name, specs.type))

        group = sg_dict.get(key)
        if not group:
            sg_dict[key] = []
            sg_list.append(sg_dict[key])
        sg_dict[key].append((name, specs))

    LOG.debug("sg_list: %s", sg_list)
    for stages in sg_list:
        q = Queue()
        pool = []
        for stage in stages:
            description, specs = stage
            if not specs or not _bool(specs.get(ENABLE_KEY)):
                continue

            LOG.info("Processing stage: %s", description)
            # items() reverts <Options> to a simple <dict>
            specs = Options(specs)
            if not stages_map.get(specs.type):
                LOG.warning("Stage '%s' (%s) not defined.", description, specs.type)
                continue

            stage_class = stages_map[specs.type]
            parameters = specs.get('parameters', Options())
            parameters._context = context

            for device in expand_devices(specs):
                stage = stage_class(device, parameters)
                name = '%s :: %s' % (description, device.alias) if device else description
                t = MacroThread(stage, q, name=name, config=config)
                t.start()
                pool.append(t)
                if not stage_class.parallelizable:
                    t.join()

        LOG.debug('Waiting for threads...')
        for t in pool:
            t.join()

        if not q.empty():
            stages = []
            while not q.empty():
                ret = q.get(block=False)
                thread, exc_info = ret.popitem()
                stages.append(thread.getName())
                LOG.error('Exception while "%s"', thread.getName())
                for line in traceback.format_exception(*exc_info):
                    LOG.error(line.strip())

            raise StageError('Check logs for exceptions in %s' % ' '.join(stages))


class TweaksStage(Stage, Macro):
    """
    Mainly this stage is open for any type of debugging flags/setups needed to
    be set after a clean software install. This includes:

    - Enable iControl debug logging (icontrol);
    - Force logrotate (logrotate);
    - Enable iControl Proxy.

    These settings will be on for all tests and will not be unset (unless a
    teardown stage is implemented).
    """
    name = 'tweaks'

    def __init__(self, device, specs=None, *args, **kwargs):
        self.device = device
        self.specs = specs
        self._context = specs.get('_context')
        super(TweaksStage, self).__init__(*args, **kwargs)

    def setup(self):
        super(TweaksStage, self).setup()
        LOG.info('Tweaks stage for: %s', self.device)
        # mcp: Enable MCPD debug logging
        if self.specs.mcp and _bool(self.specs.mcp):
            with SSHInterface(device=self.device) as sshifc:
                sshifc.api.run('setdb log.mcpd.level debug')

        # icontrol: Enable icontrol debug logging
        if self.specs.icontrol and _bool(self.specs.icontrol):
            with SSHInterface(device=self.device) as sshifc:
                sshifc.api.run('setdb icontrol.loglevel debug')
                sshifc.api.run('bigstart restart httpd')

        # logrotate: Force logrotate all logs
        if self.specs.logrotate and _bool(self.specs.logrotate):
            with SSHInterface(device=self.device) as sshifc:
                sshifc.api.run('/usr/sbin/logrotate /etc/logrotate.conf -f')

        # scp: Copy files to/from
        if self.specs.scp:
            params = self.specs.scp

            source = params.source if isinstance(params.source, basestring) \
                                   else ' '.join(params.source)

            with SSHInterface(device=self.device) as sshifc:
                if params.method.lower() == 'get':
                    SCMD.ssh.scp_get(ifc=sshifc, source=source,
                         destination=params.destination, nokex=True)
                elif params.method.lower() == 'put':
                    SCMD.ssh.scp_put(ifc=sshifc, source=source,
                         destination=params.destination, nokex=True)
                else:
                    raise ValueError("Unknown scp method: %s" % params.method)

        # shell: Execute shell commands
        if self.specs.shell:
            commands = [self.specs.shell] if isinstance(self.specs.shell,
                                                        basestring) \
                                          else self.specs.shell
            with SSHInterface(device=self.device) as sshifc:
                for command in commands:
                    ret = sshifc.api.run(command)
                    LOG.debug(ret)


class CoresStage(Stage, Macro):
    """
    A teardown stage which looks for core files and downloads them from device.
    """
    name = 'cores'

    def __init__(self, device, specs=None, *args, **kwargs):
        self.device = device
        cfgifc = ConfigInterface()
        self.session = cfgifc.get_session()
        super(CoresStage, self).__init__(*args, **kwargs)

    def run(self):
        LOG.debug('Looking for cores on device %s', self.device)
        email_container = ContextHelper('__main__').set_container('email')

        with SSHInterface(device=self.device) as sshifc:
            if SCMD.ssh.cores_exist(ifc=sshifc):
                LOG.debug('Cores found on device %s', self.device)
                email_container.cores = {}
                cores_dir = os.path.join(self.session.path, 'cores',
                                         self.device.get_address())
                cores_dir = os.path.expanduser(cores_dir)
                cores_dir = os.path.expandvars(cores_dir)
                if not os.path.exists(cores_dir):
                    os.makedirs(cores_dir)

                SCMD.ssh.scp_get(ifc=sshifc, source='/var/core/*',
                                 destination=cores_dir, nokex=True)
                sshifc.api.run('rm -f /var/core/*')

                # Add read permissions to group and others.
                with ShellInterface(shell=True) as shell:
                    shell.api.run('chmod -R go+r %s' % cores_dir)
                email_container.cores[self.device.get_alias()] = True


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


class PrintDevicesInfo(Macro):
    """
    Gather some basic information about all devices included in the current run.
    """

    def run(self, config):
        cfgifc = ConfigInterface()
        devices = cfgifc.get_all_devices()

        LOG.info('=' * 80)
        LOG.info('EM test suite environment:')
        LOG.info('-' * 80)
        tags = []
        i = 1
        for device in devices:
            platform = ICMD.system.get_platform(device=device)
            version = ICMD.system.get_version(device=device)
            LOG.info("%s: %s - %s - %s" % (device.alias, device.address,
                                           platform, version))
            tags.append("device.%d.build=%s" % (i, version.build))
            tags.append("device.%d.platform=%s" % (i, platform))
            tags.append("device.%d.version=%s" % (i, version.version))
            tags.append("device.%d.product=%s" % (i, version.product.product))
            tags.append("device.%d.alias=%s" % (i, device.alias))
            tags.append("device.%d.address=%s" % (i, device.address))
            i += 1

        LOG.info('=' * 80)

        if config.testopia and config.testopia._testrun:
            LOG.debug('Tagging testrun with devices specs...')
            c = config.testopia
            t = TestopiaInterface().open()
            t.TestRun.add_tag(c._testrun, tags)


class SanityCheck(Macro):
    """
    Do some sanity checks before running any other stages:

    - Check that 'root ca', 'build' and 'logs' paths are defined;
    - Chack that <build>/bigip directory exists;
    - Check that <root ca> directory is writable;
    - Verify that <logs> directory is writable;
    - Make sure <logs> directory has more than 100MB free.
    """

    def run(self):
        configifc = ConfigInterface()
        config = configifc.open()

        if not config.paths:
            LOG.info('Test runner sanity skipped.')
            return

        assert config.paths.build, 'CM Build path is not set in the config'
        assert config.paths.logs, 'Logs path is not set in the config'

        sample = os.path.join(config.paths.build, 'bigip')
        if not os.path.exists(sample):
            raise StageError("%s does not exist" % sample)

        sample = config.paths.get('logs')
        sample = os.path.expanduser(sample)
        sample = os.path.expandvars(sample)
        if not os.access(sample, os.W_OK):
            raise StageError("Logs dir: %s is not writable" % sample)

        stats = os.statvfs(sample)
        if not (stats.f_bsize * stats.f_bavail) / 1024 ** 2 > 100:
            raise StageError("Logs dir: %s has not enough space left" % sample)

        LOG.info('Test runner sanity check passed!')


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
        LOG.info('Resetting password before install...')
        assert ICMD.system.set_password(device=self.options.device,
                                        keyset=KEYSET_COMMON)

        if not self.specs.get('no remove em certs'):
            LOG.info('Removing EM certs...')
            SCMD.ssh.remove_em(device=self.options.device)

    def setup(self):
        ret = super(InstallSoftwareStage, self).setup()

        if not self.specs.get('no reset password after'):
            LOG.info('Resetting password after install...')
            ICMD.system.SetPassword(device=self.options.device).run_wait(timeout=60)

        if not self.has_essential_config:
            # This variable exists only on 11.0+
            v = ICMD.system.get_version(device=self.device)
            if v.product.is_bigip and v >= 'bigip 11.0' or \
               v.product.is_em and v >= 'em 3.0' or \
               v.product.is_bigiq:
                LOG.info('Waiting on Trust.configupdatedone DB variable...')
                ICMD.management.GetDbvar('Trust.configupdatedone',
                                         device=self.options.device).\
                                         run_wait(lambda x: x == 'true', timeout=300)

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


class ConfigGeneratorStage(Stage, ConfigGenerator):
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

        options = Options(device=device,
                          config=specs.get('config file'),
                          peer_device=specs.get('peer'),
                          unitid=specs.get('unitid'),
                          license=specs.get('license'),
                          timezone=specs.get('timezone'),
                          timeout=specs.get('timeout'),
                          selfip_floating=specs.get('floating ip'),
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
                          password=password)

        if config.irack:
            options.irack_address = config.irack.address
            options.irack_username = config.irack.username
            options.irack_apikey = config.irack.apikey

        super(ConfigGeneratorStage, self).__init__(options, *args, **kwargs)

    def setup(self):
        ret = super(ConfigGeneratorStage, self).setup()
        LOG.debug('Locking device %s...', self.options.device)
        ICMD.system.SetPassword(device=self.options.device).run_wait(timeout=60)
        self.options.device.specs._x_tmm_bug = True

        return ret

    def revert(self):
        super(ConfigGeneratorStage, self).revert()
        if self._context:
            LOG.debug('In ConfigGeneratorStage.revert()')
            device = self.options.device
            # If the installation has failed before rebooting then no password
            # change is needed.
            #ICMD.system.set_password(device=self.options.device)
            self._context.get_interface(SSHInterface, device=device)


class KeySwapStage(Stage, KeySwap):
    """
    This stage makes sure the SSH keys are exchanged between the test runner
    system and the devices.
    """
    name = 'keyswap'

    def __init__(self, device, specs=None, *args, **kwargs):
        options = Options(device=device)
        super(KeySwapStage, self).__init__(options, *args, **kwargs)


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
                            LOG.warn(ret)

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


class HAStage(Stage, FailoverMacro):
    """
    Create a CMI Device Group for Failover and Config Sync between two or more
    BIGIP 11.0+ devices or EM 3.0+.
    """
    name = 'ha'

    def __init__(self, device, specs=None, *args, **kwargs):
        authorities = [device] + list(expand_devices(specs, 'authorities'))
        peers = list(expand_devices(specs, 'peers'))
        groups = specs.groups or []

        configifc = ConfigInterface()
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
