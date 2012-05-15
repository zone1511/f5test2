#!/usr/bin/env python
from f5test.macros.base import Macro, MacroError
from f5test.base import Options
from f5test.interfaces.config import ConfigInterface
from f5test.interfaces.icontrol import IcontrolInterface, EMInterface
from f5test.interfaces.ssh import SSHInterface
from f5test.defaults import ADMIN_PASSWORD, ADMIN_USERNAME, ROOT_PASSWORD, \
                            ROOT_USERNAME
import f5test.commands.icontrol as ICMD
import f5test.commands.shell as SCMD
import f5test.commands.icontrol.em as EMAPI
import f5test.commands.shell.em as EMSQL
from f5test.utils import cm, Version, net
from f5test.utils.parsers.audit import get_inactive_volume
import logging
import os.path
import time
#import socket

LOG = logging.getLogger(__name__)
SHARED_IMAGES = '/shared/images'
SHARED_TMP = '/shared/tmp'
__version__ = '0.1'
__all__ = ['VersionNotSupported', 'InstallSoftware', 'EMInstallSoftware']

class VersionNotSupported(Exception):
    pass

class InstallFailed(Exception):
    pass


class InstallSoftware(Macro):

    def __init__(self, options, address=None, *args, **kwargs):
        self.options = Options(options)
        if self.options.device:
            device = ConfigInterface().get_device(options.device)
            self.address = device.get_address()
            self.options.admin_username = device.get_admin_creds().username
            self.options.admin_password = device.get_admin_creds().password
            self.options.root_username = device.get_root_creds().username
            self.options.root_password = device.get_root_creds().password
            self.options.ssl_port = device.ports.get('https', 443)
            self.options.ssh_port = device.ports.get('ssh', 22)
        else:
            self.address = address

        self.options.setdefault('admin_username', ADMIN_USERNAME)
        self.options.setdefault('admin_password', ADMIN_PASSWORD)
        self.options.setdefault('root_username', ROOT_USERNAME)
        self.options.setdefault('root_password', ROOT_PASSWORD)
        self.options.setdefault('build_path', cm.ROOT_PATH)
        self.has_essential_config = None

        LOG.info('Doing: %s', self.address)
        super(InstallSoftware, self).__init__(*args, **kwargs)

    def by_em_api(self, filename, hfiso=None):
        devices = []
        devices.append(Options(address=self.address, 
                               username=self.options.admin_username, 
                               password=self.options.admin_password))
        options = Options(device=self.options.em_device,
                          address=self.options.em_address,
                          admin_username=self.options.em_admin_username,
                          admin_password=self.options.em_admin_password,
                          root_username=self.options.em_root_username,
                          root_password=self.options.em_root_password,
                          essential_config=self.options.essential_config,
                          image=filename, hfimage=hfiso)
        macro = EMInstallSoftware(devices, options)
        self.has_essential_config = macro.has_essential_config
        return macro.run()

#    def by_em_ui(self):
#        return
#
#    def by_bigpipe(self):
#        return

    def _initialize_big3d(self, sshifc=None):
        LOG.info('Initializing big3d...')
        if sshifc is None:
            sshifc = SSHInterface(address=self.address,
                                  username=self.options.root_username,
                                  password=self.options.root_password,
                                  port=self.options.ssh_port)
        with sshifc:
            ssh = sshifc.api
            ssh.run('bigstart stop big3d;'
                    'rm -f /shared/bin/big3d;'
                    'test -f /usr/sbin/big3d.default && cp -f /usr/sbin/big3d.default /usr/sbin/big3d;'
                    'bigstart start big3d')

    def _initialize_em(self):
        LOG.info('Initializing EM...')
        sshifc = SSHInterface(address=self.address, port=self.options.ssh_port)
        with sshifc:
            ssh = sshifc.api
            ssh.run('bigstart stop;'
                    '/etc/em/f5em_db_setup.sh;'
                    'rm -f /shared/em/mysql_shared_db/f5em_extern/*;'
                    '/etc/em/f5em_extern_db_setup.sh;'
                    'bigstart start')
            SCMD.ssh.FileExists('/etc/em/.initial_boot', ifc=sshifc).run_wait(lambda x:x is False,
                                                 progress_cb=lambda x:'EM still not initialized...',
                                                 timeout=180)

    def _wait_after_reboot(self, essential):
        if essential:
            ssh = SSHInterface(address=self.address, port=self.options.ssh_port)
        else:
            ssh = SSHInterface(address=self.address,
                               username=self.options.root_username,
                               password=self.options.root_password,
                               port=self.options.ssh_port)

        try:
            SCMD.ssh.GetPrompt(ifc=ssh).run_wait(lambda x:x not in ('INOPERATIVE', '!'),
                                                 timeout=900)
            SCMD.ssh.FileExists('/var/run/mcpd.pid', ifc=ssh).run_wait(lambda x:x,
                                                 progress_cb=lambda x:'mcpd not up...',
                                                 timeout=120)
            SCMD.ssh.FileExists('/var/run/mprov.pid', ifc=ssh).run_wait(lambda x:x is False,
                                                 progress_cb=lambda x:'mprov still running...',
                                                 timeout=120)
            SCMD.ssh.FileExists('/var/run/grub.conf.lock', ifc=ssh).run_wait(lambda x:x is False,
                                                 progress_cb=lambda x:'grub.lock still running...',
                                                 timeout=60)
            version = SCMD.ssh.get_version(ifc=ssh)
        finally:
            ssh.close()
        return version

    def by_image2disk(self, filename, hfiso=None):
        iso_version = cm.version_from_metadata(filename)
        
        if hfiso:
            hfiso_version = cm.version_from_metadata(hfiso)
            reboot = False
        else:
            hfiso_version = None
            reboot = True

        LOG.debug('iso: %s', iso_version)

        base = os.path.basename(filename)
        essential = self.options.essential_config
        timeout = self.options.timeout
        
        if self.options.format_partitions or self.options.format_volumes:
            reboot = True
            timeout = max(1200, timeout)
        else:
            timeout = max(600, timeout)
        
        with SSHInterface(address=self.address,
                          username=self.options.root_username,
                          password=self.options.root_password,
                          timeout=timeout, port=self.options.ssh_port) as sshifc:
            ssh = sshifc.api
            version = SCMD.ssh.get_version(ifc=sshifc)
            LOG.info('running on %s', version)
            
            if not essential and iso_version < version or \
               iso_version.product != version.product:
                LOG.warning('Enforcing --esential-config')
                essential = True
            
            #XXX: Image checksum is not verified!!
            if (not base in ssh.run('ls ' + SHARED_IMAGES).stdout.split()):
                LOG.info('Deleting all images...')
                ssh.run('rm -f %s/*' % SHARED_IMAGES)
                
                LOG.info('Importing iso %s', filename)
                SCMD.ssh.scp_put(ifc=sshifc, source=filename, nokex=False)
            
            filename = os.path.join(SHARED_IMAGES, base)
            
            if self.options.format_volumes:
                fmt = 'lvm'
            elif self.options.format_partitions:
                fmt = 'partitions'
            else:
                fmt = None
            
            def log_progress(stdout, stderr):
                output = ''
                if stdout:
                    output += stdout
                if stderr:
                    output += '\n'
                    output += stderr
                
                # An in-house grep.
                for line in output.splitlines():
                    line = line.strip()
                    if line and not line.startswith('info: '):
                        LOG.debug(line)

            audit = SCMD.ssh.audit_software(version=version, ifc=sshifc)
            volume = get_inactive_volume(audit)
            LOG.info('Installing %s on %s...', iso_version, volume)
            SCMD.ssh.install_software(version=version, ifc=sshifc, 
                                      repository=filename, format=fmt, 
                                      essential=essential, volume=volume, 
                                      progress_cb=log_progress,
                                      reboot=reboot,
                                      repo_version=iso_version)
            
            
#            LOG.info('Rebooting...')
#            SCMD.ssh.reboot(ifc=sshifc)

        if reboot:
            # Grab a new iControl handle that uses the default admin credentials.
            self._wait_after_reboot(essential)

        if hfiso:
            if essential:
                ssh = SSHInterface(address=self.address, timeout=timeout,
                                   port=self.options.ssh_port)
            else:
                ssh = SSHInterface(address=self.address, timeout=timeout,
                                   username=self.options.root_username,
                                   password=self.options.root_password,
                                   port=self.options.ssh_port)

            with ssh:
                version = SCMD.ssh.get_version(ifc=ssh)
                LOG.info('running on %s', version)
                if reboot:
                    audit = SCMD.ssh.audit_software(version=version, ifc=ssh)
                    volume = get_inactive_volume(audit)
                    LOG.info('Installing image on %s...', volume)
                    SCMD.ssh.install_software(version=version, ifc=ssh, 
                                              repository=filename, reboot=False,
                                              essential=essential, volume=volume, 
                                              progress_cb=log_progress,
                                              repo_version=iso_version)
                hfbase = os.path.basename(hfiso)
                if (not hfbase in ssh.run('ls ' + SHARED_IMAGES).stdout.split()):
                    LOG.info('Importing hotfix %s', hfiso)
                    SCMD.ssh.scp_put(ifc=ssh, source=hfiso, nokex=not reboot)
                hfiso = os.path.join(SHARED_IMAGES, hfbase)

                LOG.info('Installing hotfix on %s...', volume)
                SCMD.ssh.install_software(version=version, ifc=ssh, 
                                          repository=hfiso, is_hf=True, 
                                          essential=essential, volume=volume,
                                          progress_cb=log_progress,
                                          repo_version=hfiso_version,
                                          reboot=False)
                if essential:
                    self._initialize_big3d(ssh)
                LOG.info('Rebooting...')
                SCMD.ssh.switchboot(ifc=ssh, volume=volume)
                SCMD.ssh.reboot(ifc=ssh)

        # Grab a new iControl handle that uses the default admin credentials.
        current_version = self._wait_after_reboot(essential)
        expected_version = hfiso_version or iso_version

        if expected_version != current_version:
            raise InstallFailed('Version expected: %s but found %s' % 
                                (expected_version, current_version))
        
        if essential and current_version.product.is_em:
            self._initialize_em()
        
        self.has_essential_config = essential

#    def by_tmsh(self):
#        return

    def by_icontrol(self, filename, hfiso=None):
        iso_version = cm.version_from_metadata(filename)
        timeout = max(self.options.timeout, 600)
        if hfiso:
            hfiso_version = cm.version_from_metadata(hfiso)
        else:
            hfiso_version = None

        LOG.debug('iso: %s', iso_version)

        icifc = IcontrolInterface(address=self.address,
                                  username=self.options.admin_username,
                                  password=self.options.admin_password,
                                  port=self.options.ssl_port)
        ic = icifc.open()
        running_volume = ICMD.software.get_active_volume(ifc=icifc)
        assert running_volume != self.options.volume, \
                                    "Can't install on the active volume"

        version = ICMD.system.get_version(ifc=icifc)
        base = os.path.basename(filename)

        LOG.debug('running: %s', version)
        essential = self.options.essential_config
        if not essential and iso_version < version:
            LOG.warning('Enforcing --esential-config')
            essential = True
        
        LOG.info('Setting the global DB vars...')
        ic.Management.DBVariable.modify(variables=[
            {'name': 'LiveInstall.MoveConfig',
            'value': essential and 'disable' or 'enable'},
            {'name': 'LiveInstall.SaveConfig',
            'value': essential and 'disable' or 'enable'}
        ])
        #=======================================================================
        # Copy the ISO over to the device in /shared/images if it's not already
        # in the software repository. 
        #=======================================================================
        images = ICMD.software.get_software_image(ifc=icifc)
        haz_it = filter(lambda x: x['verified'] and
                               x['product'] == iso_version.product.to_tmos() and
                               x['version'] == iso_version.version and
                               x['build'] == iso_version.build
                    , images)

        volume = self.options.volume or ICMD.software.get_inactive_volume(ifc=icifc)
        LOG.info('Preparing volume %s...', volume)
        ICMD.software.clear_volume(volume=volume, ifc=icifc)

        def is_available(items):
            all_count = len(items)
            return len(filter(lambda x: x['verified'] is True, 
                           items)) == all_count
        
        is_clustered = ic.System.Cluster.is_clustered_environment()
        if is_clustered:
            timeout = 1200
        
        LOG.info('Timeout: %d', timeout)
        if not haz_it:
            LOG.info('Deleting all images...')
            ICMD.software.delete_software_image(ifc=icifc)
            
            LOG.info('Importing base iso %s', base)
            SCMD.ssh.scp_put(address=self.address,
                            username=self.options.root_username,
                            password=self.options.root_password,
                            port=self.options.ssh_port,
                            source=filename, nokex=False, timeout=timeout)

            LOG.info('Wait for image to be imported %s', base)
            ICMD.software.GetSoftwareImage(filename=base, ifc=icifc) \
                         .run_wait(is_available, timeout=timeout)
        
        if hfiso:
            images = ICMD.software.get_software_image(ifc=icifc, is_hf=True)
            haz_it = filter(lambda x: x['verified'] and
                                   x['product'] == hfiso_version.product.to_tmos() and
                                   x['version'] == hfiso_version.version and
                                   x['build'] == hfiso_version.build
                        , images)

            if not haz_it:
                hfbase = os.path.basename(hfiso)
                LOG.info('Importing hotfix iso %s', hfiso)
                SCMD.ssh.scp_put(address=self.address,
                                 username=self.options.root_username,
                                 password=self.options.root_password,
                                 port=self.options.ssh_port,
                                 source=hfiso, nokex=True)
    
                LOG.info('Wait for image to be imported %s', hfbase)
                ICMD.software.GetSoftwareImage(filename=hfbase, ifc=icifc, is_hf=True) \
                             .run_wait(is_available)

        def is_still_removing(items):
            return len(filter(lambda x: x['status'].startswith('removing'), 
                              items)) == 0

        def is_still_installing(items):
            return len(filter(lambda x: x['status'].startswith('installing') or \
                                        x['status'].startswith('waiting') or \
                                        x['status'] in ('audited', 'auditing',
                                                        'upgrade needed'), 
                              items)) == 0

        volumes = ICMD.software.get_software_status(ifc=icifc)
        assert is_still_installing(volumes), "An install is already in " \
                                        "progress on another slot: %s" % volumes
        
        ICMD.software.GetSoftwareStatus(volume=volume, ifc=icifc) \
                     .run_wait(is_still_removing,
                               # CAVEAT: tracks progress only for the first blade
                               progress_cb=lambda x:x[0]['status'],
                               timeout=timeout)

        LOG.info('Installing %s...', iso_version)
        
        ICMD.software.install_software(hfiso_version or iso_version, 
                                       volume=volume, ifc=icifc)
        
        ret = ICMD.software.GetSoftwareStatus(volume=volume, ifc=icifc) \
                     .run_wait(is_still_installing,
                               # CAVEAT: tracks progress only for the first blade
                               progress_cb=lambda x:x[0]['status'],
                               timeout=timeout,
                               stabilize=5)

        LOG.info('Resetting the global DB vars...')
        ic.Management.DBVariable.modify(variables=[
            {'name': 'LiveInstall.MoveConfig',
            'value': essential and 'enable' or 'disable'},
            {'name': 'LiveInstall.SaveConfig',
            'value': essential and 'enable' or 'disable'}
        ])

        if len(filter(lambda x: x['status'] == 'complete', ret)) != len(ret):
            raise InstallFailed('Install did not succeed: %s' % ret)

        # Will use SSH!
        if essential:
            self._initialize_big3d()

        LOG.info('Setting the active boot location %s.', volume)
        if is_clustered:
            #===================================================================
            # Apparently on chassis systems the device is rebooted automatically
            # upon setting the active location, just like `b software desired
            # HD1.N active enable`.
            #===================================================================
            uptime = ic.System.SystemInfo.get_uptime()
            ic.System.SoftwareManagement.set_cluster_boot_location(location=volume)
            time.sleep(60)
        else:
            ic.System.SoftwareManagement.set_boot_location(location=volume)
            LOG.info('Rebooting...')
            uptime = ICMD.system.reboot(ifc=icifc)
        
        # Grab a new iControl handle that uses the default admin credentials.
        if essential:
            icifc.close()
            icifc = IcontrolInterface(address=self.address,
                                      port=self.options.ssl_port)
            icifc.open()

        if uptime:
            ICMD.system.HasRebooted(uptime, ifc=icifc).run_wait(timeout=timeout)
            LOG.info('Device is rebooting...')

        LOG.info('Wait for box to be ready...')
        ICMD.system.IsServiceUp('MCPD', ifc=icifc).run_wait(timeout=timeout,
                message="Target doesn't seem to be willing to come back up "
                        "after %d seconds." % timeout)
        ICMD.system.IsServiceUp('TMM', ifc=icifc).run_wait(message="Target "
                  "doesn't seem to be willing to come back up after 3 minutes.")
        
#        ICMD.system.FileExists('/var/run/bigstart.tmm', 
#                               ifc=icifc).run_wait(lambda x:x is False,
#                                  progress_cb=lambda x:'bigstart still running...',
#                                  timeout=300)

        ICMD.management.GetDbvar('Configsync.LocalConfigTime', 
                             ifc=icifc).run_wait(lambda x:int(x) > 0,
                                  progress_cb=lambda x:'waiting configsync...',
                                  timeout=60)
        #ICMD.management.GetDbvar('License.operational', 
        #                     ifc=icifc).run_wait(lambda x:x == 'true',
        #                          progress_cb=lambda x:'waiting license...',
        #                          timeout=60)
        ICMD.system.FileExists('/var/run/mprov.pid', 
                               ifc=icifc).run_wait(lambda x:x is False,
                                  progress_cb=lambda x:'mprov still running...',
                                  timeout=300)
        ICMD.system.FileExists('/var/run/grub.conf.lock', 
                               ifc=icifc).run_wait(lambda x:x is False,
                              progress_cb=lambda x:'grub.lock still present...',
                              timeout=60)

        current_version = ICMD.system.get_version(ifc=icifc, build=True)
        expected_version = hfiso_version or iso_version
        try:
            if expected_version != current_version:
                raise InstallFailed('Version expected: %s but found %s' % 
                                    (expected_version, current_version))
        finally:
            icifc.close()

        if essential and current_version.product.is_em:
            self._initialize_em()
        
        self.has_essential_config = essential
        
#    def by_ui(self):
#        return

    def prep(self):
        LOG.debug('prepping for install')

    def setup(self):
        if self.options.image:
            title = 'Installing custom base image on %s' % self.address
        else:
            title = 'Installing %s %s on %s' % (self.options.product, 
                                                self.options.pversion, 
                                                self.address)
        LOG.info(title)
        identifier = self.options.pversion
        build = self.options.pbuild

        if identifier:
            ver = identifier = str(identifier)
            if build:
                build = str(build)
                ver = "%s %s" % (identifier, build)
    
            if cm.is_version_string(ver):
                wanted_version = Version(ver, product=self.options.product)
            else:
                wanted_version = ver
    
            LOG.debug('wanted: %s', wanted_version)

        if self.options.image:
            filename = self.options.image
        else:
            base_build = None if self.options.phf else build
            filename = cm.isofile(identifier=identifier, build=base_build, 
                                  product=self.options.product,
                                  root=self.options.build_path)

        iso_version = cm.version_from_metadata(filename)

        if self.options.phf:
            if self.options.hfimage:
                hfiso = self.options.hfimage
            else:
                hfiso = cm.isofile(identifier=identifier, build=build, 
                                   hotfix=self.options.phf,
                                   product=self.options.product,
                                   root=self.options.build_path)
        else:
            hfiso = None

        if self.options.format_partitions or self.options.format_volumes:
            with SSHInterface(address=self.address,
                              username=self.options.root_username,
                              password=self.options.root_password,
                              port=self.options.ssh_port) as sshifc:
                version = SCMD.ssh.get_version(ifc=sshifc)
        else:
            with IcontrolInterface(address=self.address,
                                   username=self.options.admin_username,
                                   password=self.options.admin_password,
                                   port=self.options.ssl_port) as icifc:
                version = ICMD.system.get_version(ifc=icifc)

        if (iso_version.product.is_bigip and iso_version >= 'bigip 10.0.0' or
            iso_version.product.is_em and iso_version >= 'em 2.0.0'):
            if self.options.format_partitions or self.options.format_volumes or \
               (version.product.is_bigip and version < 'bigip 10.0.0' or \
                version.product.is_em and version < 'em 2.0.0'):
                ret = self.by_image2disk(filename, hfiso)
            else:
                ret = self.by_icontrol(filename, hfiso)
        elif (iso_version.product.is_bigip and iso_version < 'bigip 9.6.0' or
              iso_version.product.is_em and iso_version < 'em 2.0.0'):
            assert self.options.em_address, "--em-address is needed for legacy installations."
            ret = self.by_em_api(filename, hfiso)
        else:
            raise VersionNotSupported('%s is not supported' % wanted_version)

        LOG.debug('done')
        return ret


class EMInstallSoftware(Macro):
    """Use an EM to install software.
    
    install_options = dict(uid, slot_uid, install_location, boot_location, 
                           format, reboot, essential)
    device = dict(address='1.1.1.1', username='admin', password='admin', 
                  install_options)
    options = dict(iso, hfiso, include_pk, continue_on_error, task_name)
    
    @param devices: [device1, device2, ...]
    @type devices: array
    @param options: EM address, credentials and other installation options.
    @param options: AttrDict
    """
    def __init__(self, devices, options, *args, **kwargs):
        self.devices = devices
        self.options = Options(options)
        self.options.setdefault('build_path', cm.ROOT_PATH)
        self.has_essential_config = None

        super(EMInstallSoftware, self).__init__(*args, **kwargs)

    def by_api(self):
        o = self.options
        timeout = max(o.timeout, 600)

        identifier = self.options.pversion
        build = self.options.pbuild
        
        if identifier:
            identifier = str(identifier)
            if build:
                build = str(build)
            
        if self.options.image:
            filename = self.options.image
        else:
            filename = cm.isofile(identifier=identifier, build=build, 
                                  product=self.options.product,
                                  root=self.options.build_path)

        if self.options.phf:
            if self.options.hfimage:
                hfiso = self.options.hfimage
            else:
                hfiso = cm.isofile(identifier=identifier, build=build, 
                                   hotfix=self.options.phf,
                                   product=self.options.product,
                                   root=self.options.build_path)
        else:
            hfiso = None

        iso_version = cm.version_from_metadata(filename)
        if (iso_version.product.is_bigip and iso_version >= 'bigip 10.0.0' or
            iso_version.product.is_em and iso_version >= 'em 2.0.0'):
            raise VersionNotSupported('Only legacy images supported through EMInstaller.')

        emifc = EMInterface(device=o.device, address=o.address, 
                         username=o.admin_username, password=o.admin_password)
        emifc.open()
        
        with SSHInterface(device=o.device, address=o.address, 
                          username=o.root_username, password=o.root_password,
                          port=self.options.ssh_port) as ssh:
#            version = SCMD.ssh.get_version(ifc=ssh)
#            LOG.info('running on %s', version)
#            if (version.product.is_bigip and version >= 'bigip 10.0.0' or
#                version.product.is_em and version >= 'em 2.0.0'):
#                raise VersionNotSupported('Downgrading to legacy software is not supported.')
            
            status = SCMD.ssh.get_prompt(ifc=ssh)
            if status in ['LICENSE EXPIRED', 'REACTIVATE LICENSE']:
                SCMD.ssh.relicense(ifc=ssh)
            elif status in ['LICENSE INOPERATIVE', 'NO LICENSE']:
                raise MacroError('Device at %s needs to be licensed.' % ssh)
                
            reachable_devices = [x['access_address'] for x in 
                                    EMSQL.device.get_reachable_devices(ifc=ssh)]
            for x in self.devices:
                x.address = net.resolv(x.address)
            
            to_discover = [x for x in self.devices 
                              if x.address not in reachable_devices]
            
            if to_discover:
                uid = EMAPI.device.discover(to_discover, ifc=emifc)
                task = EMSQL.device.GetDiscoveryTask(uid, ifc=ssh) \
                            .run_wait(lambda x: x['status'] != 'started',
                                      timeout=timeout,
                                      progress_cb=lambda x:'discovery: %d%%' % x.progress_percent)
                assert task['error_count'] == 0, 'Discovery failed: %s' % task
            targets = []
            for device in self.devices:
                mgmtip = device.address
                version = EMSQL.device.get_device_version(mgmtip, ifc=ssh)
                if not o.essential_config and iso_version < version:
                    LOG.warning('Enforcing --esential-config')
                    o.essential_config = True

                device_info = EMSQL.device.get_device_info(mgmtip, ifc=ssh)
                active_slot = EMSQL.device.get_device_active_slot(mgmtip,
                                                                  ifc=ssh)
                #slots = EMSQL.device.get_device_slots(mgmtip=mgmtip,
                #                                      ifc=ssh)
                #filter(lambda x:int(x['is_cf']) and )
                targets.append(dict(device_uid=device_info['uid'], 
                                    slot_uid=active_slot['uid']))

            image_list = EMSQL.software.get_image_list(ifc=ssh)
            if not iso_version in image_list:
                base = os.path.basename(filename)
                destination = '%s.%d' % (os.path.join(SHARED_TMP, base), os.getpid())
                LOG.info('Importing base iso %s', base)
                SCMD.ssh.scp_put(device=o.device, address=o.address,
                                 destination=destination,
                                 username=self.options.root_username,
                                 password=self.options.root_password,
                                 port=self.options.ssh_port,
                                 source=filename, nokex=False)
    
                imuid = EMAPI.software.import_image(destination, ifc=emifc)
            else:
                imuid = image_list[iso_version]
                LOG.info('Image already imported: %d', imuid)
            #EMAPI.software.delete_image(imuid, ifc=emifc)
            
            if hfiso:
                hf_list = EMSQL.software.get_hotfix_list(ifc=ssh)
                hfiso_version = cm.version_from_metadata(hfiso)
                if not hfiso_version in hf_list:
                    hfbase = os.path.basename(hfiso)
                    destination = '%s.%d' % (os.path.join(SHARED_TMP, hfbase), os.getpid())
                    LOG.info('Importing hotfix iso %s', hfbase)
                    SCMD.ssh.scp_put(device=o.device, address=o.address,
                                     destination=destination,
                                     username=self.options.root_username,
                                     password=self.options.root_password,
                                     port=self.options.ssh_port,
                                     source=hfiso, nokex=True)
                    hfuid = EMAPI.software.import_image(destination, ifc=emifc)
                else:
                    hfuid = hf_list[hfiso_version]
            else:
                hfuid = None
            
            EMSQL.software.get_hotfix_list(ifc=ssh)

            all_mgmtips = [x.address for x in self.devices]
            EMSQL.device.CountActiveTasks(all_mgmtips, ifc=ssh) \
                        .run_wait(lambda x: x == 0, timeout=timeout,
                                  progress_cb=lambda x:'waiting for other tasks')

            LOG.info('Installing %s...', iso_version)
            ret = EMAPI.software.install_image(targets, imuid, hfuid, o, ifc=emifc)
            ret = EMSQL.software.GetInstallationTask(ret['uid'], ifc=ssh) \
                          .run_wait(lambda x: x['status'] != 'started',
                                    progress_cb=lambda x:'install: %d%%' % x.progress_percent,
                                    timeout=max(o.timeout, 1800))
        
        LOG.info('Deleting %d device(s)...', len(targets))
        EMAPI.device.delete(uids=[x['device_uid'] for x in targets], ifc=emifc)
        emifc.close()

        messages = []
        for d in ret['details']:
            if int(d['error_code']):
                messages.append("%(display_device_address)s:%(error_message)s" % d)
            if int(d['hf_error_code'] or 0):
                messages.append("%(display_device_address)s:%(hf_error_message)s" % d)
        if messages:
            raise InstallFailed('Install did not succeed: %s' % 
                                ', '.join(messages))

        self.has_essential_config = o.essential_config
        return ret

    def setup(self):
        if not self.devices:
            LOG.info('No devices to install')
            return
        if self.options.image:
            title = 'Installing custom base image on %s through %s' % ( 
                                                           self.devices,
                                                           self.options.device)
        else:
            title = 'Installing %s %s on %s through %s' % (self.options.product, 
                                                           self.options.pversion, 
                                                           self.devices,
                                                           self.options.device)
        LOG.info(title)
        return self.by_api()


def main():
    import optparse
    import sys

    usage = """%prog [options] <address>"""

    formatter = optparse.TitledHelpFormatter(indent_increment=2, 
                                             max_help_position=60)
    p = optparse.OptionParser(usage=usage, formatter=formatter,
                            version="Remote Software Installer v%s" % __version__
        )
    p.add_option("", "--verbose", action="store_true",
                 help="Debug messages")
    
    p.add_option("", "--admin-username", metavar="USERNAME",
                 default=ADMIN_USERNAME, type="string",
                 help="An user with administrator rights (default: %s)"
                 % ADMIN_USERNAME)
    p.add_option("", "--admin-password", metavar="PASSWORD",
                 default=ADMIN_PASSWORD, type="string",
                 help="An user with administrator rights (default: %s)"
                 % ADMIN_PASSWORD)
    p.add_option("", "--root-username", metavar="USERNAME",
                 default=ROOT_USERNAME, type="string",
                 help="An user with root rights (default: %s)"
                 % ROOT_USERNAME)
    p.add_option("", "--root-password", metavar="PASSWORD",
                 default=ROOT_PASSWORD, type="string",
                 help="An user with root rights (default: %s)"
                 % ROOT_PASSWORD)
    
    p.add_option("", "--em-address", metavar="HOST", type="string",
                 help="IP address or hostname of an EM")
    p.add_option("", "--em-admin-username", metavar="USERNAME",
                 default=ADMIN_USERNAME, type="string",
                 help="An user with administrator rights (default: %s)"
                 % ADMIN_USERNAME)
    p.add_option("", "--em-admin-password", metavar="PASSWORD",
                 default=ADMIN_PASSWORD, type="string",
                 help="An user with administrator rights (default: %s)"
                 % ADMIN_PASSWORD)
    p.add_option("", "--em-root-username", metavar="USERNAME",
                 default=ROOT_USERNAME, type="string",
                 help="An user with root rights (default: %s)"
                 % ROOT_USERNAME)
    p.add_option("", "--em-root-password", metavar="PASSWORD",
                 default=ROOT_PASSWORD, type="string",
                 help="An user with root rights (default: %s)"
                 % ROOT_PASSWORD)

    p.add_option("", "--timeout", metavar="TIMEOUT", type="int", default=600,
                 help="Timeout. (default: 600)")
    p.add_option("", "--ssl-port", metavar="INTEGER", type="int", default=443,
                 help="SSL Port. (default: 443)")
    p.add_option("", "--ssh-port", metavar="INTEGER", type="int", default=22,
                 help="SSH Port. (default: 22)")

    p.add_option("", "--image", metavar="FILE", type="string",
                 help="Custom built ISO. (e.g. /tmp/bigip.iso) (optional)")
    p.add_option("", "--hfimage", metavar="FILE", type="string",
                 help="Custom built hotfix. (e.g. /tmp/bigip-HF1.iso) (optional)")
    
    p.add_option("", "--product", metavar="PRODUCT", type="string",
                 help="Desired product. (e.g. bigip)")
    p.add_option("", "--pversion", metavar="VERSION", type="string",
                 help="Desired version. (e.g. 10.2.1)")
    p.add_option("", "--pbuild", metavar="BUILD", type="string",
                 help="Desired build. (e.g. 6481.0) (optional)")
    p.add_option("", "--phf", metavar="HOTFIX", type="string",
                 help="Desired hotfix. (e.g. hf2 or eng) (optional)")
    
    p.add_option("", "--volume", metavar="VOLUME", type="string",
                 help="Force installation to this volume. (e.g. HD1.1) (optional)")
    p.add_option("", "--essential-config", action="store_true", default=False,
                 help="Roll configuration forward. (e.g. HD1.1) (default: yes)")
    p.add_option("", "--format-volumes", action="store_true", default=False,
                 help="Pre-format to lvm. (default: no)")
    p.add_option("", "--format-partitions", action="store_true", default=False,
                 help="Pre-format to partitions. (default: no)")

    options, args = p.parse_args()

    if options.verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO
        logging.getLogger('paramiko.transport').setLevel(logging.ERROR)
        logging.getLogger('f5test').setLevel(logging.ERROR)
        logging.getLogger('f5test.macros').setLevel(logging.INFO)

    LOG.setLevel(level)
    logging.basicConfig(level=level)
    
    if not args:
        p.print_version()
        p.print_help()
        sys.exit(2)
    
    cs = InstallSoftware(options=options.__dict__, address=args[0])
    cs.run()


if __name__ == '__main__':
    main()
