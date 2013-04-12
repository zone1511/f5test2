"""All commands that run over the SSH interface."""

from .base import SSHCommand, CommandNotSupported, SSHCommandError
from ..base import CachedCommand, WaitableCommand, CommandError
from ...base import Options
from ...interfaces.subprocess import ShellInterface
from ...utils.parsers.version_file import colon_pairs_dict, equals_pairs_dict
from ...utils.parsers.audit import audit_parse
from ...utils.version import Version
import logging
import time
import os
import re

LOG = logging.getLogger(__name__)
KV_COLONS = 0
KV_EQUALS = 1


class LicenseParsingError(SSHCommandError):
    """Usually thrown when the bigip.license file can't be read."""
    pass


generic = None
class Generic(WaitableCommand, SSHCommand): #@IgnorePep8
    """Run a generic shell command.

    >>> ssh.generic('id')
    uid=0(root) gid=0(root) groups=0(root)

    @param command: the shell command
    @type command: str

    @rtype: SSHResult
    """
    def __init__(self, command, *args, **kwargs):
        super(Generic, self).__init__(*args, **kwargs)
        self.command = command

    def setup(self):
        ret = self.api.run(self.command)

        if not ret.status:
            return ret
        else:
            raise SSHCommandError(ret)


scp_put = None
class ScpPut(SSHCommand): #@IgnorePep8
    """Copy a file through SSH using the SCP utility. To avoid the "Password:"
    prompt for new boxes, it exchanges ssh keys first.

    @param source: source file
    @type source: str
    @param destination: destination file (or directory)
    @type destination: str
    @param nokex: don't do key exchange
    @type nokex: bool
    """
    upload = True

    def __init__(self, source, destination="/shared/images/", nokex=False,
                 timeout=300, *args, **kwargs):
        super(ScpPut, self).__init__(*args, **kwargs)

        self.source = source
        self.destination = destination
        self.nokex = nokex
        self.timeout = timeout

    def setup(self):
        """SCP a file from local system to one device."""
        if not self.nokex:
            self.api.exchange_key()

        shell = ShellInterface(timeout=self.timeout, shell=True).open()

        LOG.info('Copying file %s to %s...', self.source, self.ifc)
        scpargs = ['-p',  # Preserves modification times, access times, and modes from the original file.
                   '-o StrictHostKeyChecking=no',  # Don't look in  ~/.ssh/known_hosts.
                   '-o UserKnownHostsFile=/dev/null',  # Throw away the new identity
                   '-c arcfour256',  # High performance cipher.
                   '-P %d' % self.ifc.port]
        destdir = os.path.dirname(self.destination)
        self.api.run('mkdir -p %s' % destdir)
        if self.upload:
            shell.run('scp %s %s %s@%s:%s' %
                                    (' '.join(scpargs),
                                     self.source, self.ifc.username,
                                     self.ifc.address, self.destination))
        else:
            shell.run('scp %s %s@%s:%s %s' %
                                    (' '.join(scpargs),
                                     self.ifc.username, self.ifc.address,
                                     self.source, self.destination))

        LOG.info('Done.')


scp_get = None
class ScpGet(ScpPut): #@IgnorePep8
    upload = False


parse_keyvalue_file = None
class ParseKeyvalueFile(SSHCommand): #@IgnorePep8
    """Parses a file and return a dictionary. The file structure sould look like:
    Key1: Value1
    Key2: Value2

    @rtype: dict
    """
    def __init__(self, file, mode=KV_COLONS, *args, **kwargs):  # @ReservedAssignment
        super(ParseKeyvalueFile, self).__init__(*args, **kwargs)

        self.file = file
        self.mode = mode

    def __repr__(self):
        parent = super(ParseKeyvalueFile, self).__repr__()
        opt = {}
        opt['file'] = self.file
        opt['mode'] = self.mode
        return parent + "(file=%(file)s, mode=%(mode)d)" % opt

    def setup(self):
        ret = self.api.run('cat %s' % self.file)

        if ret.status == 0:
            if self.mode == KV_EQUALS:
                return equals_pairs_dict(ret.stdout)
            elif self.mode == KV_COLONS:
                return colon_pairs_dict(ret.stdout)
            else:
                raise ValueError(self.mode)
        else:
            LOG.error(ret)
            raise SSHCommandError(ret)


get_version = None
class GetVersion(SSHCommand): #@IgnorePep8
    """Parses the /VERSION file and returns a version object.
    For: bigip 9.3.1+, em 1.6.0+

    @rtype: Version
    """

    def setup(self):
        """SCP a file from local system to one device."""
        ret = parse_keyvalue_file('/VERSION', mode=KV_COLONS, ifc=self.ifc)
        return Version("%(product)s %(version)s %(build)s" % ret)


get_platform = None
class GetPlatform(CachedCommand, SSHCommand): #@IgnorePep8
    """Parses the /PLATFORM file and return a dictionary.
    For: bigip 9.3.1+, em 1.6.0+

    @rtype: dict
    """
    def setup(self):
        return parse_keyvalue_file('/PLATFORM', mode=KV_EQUALS, ifc=self.ifc)


license = None  # @ReservedAssignment
class License(SSHCommand): #@IgnorePep8
    """Calls SOAPLicenseClient to license a box with a given basekey.
    For: bigip 9.4.0+, em 1.6.0+

    @param basekey: the base key (e.g. A809-389396-302350-330107-5006032)
    @type basekey: str
    @param addkey: any addon key(s) (e.g. G745858-8953827)
    @type addkey: array or str

    @rtype: bool
    """
    def __init__(self, basekey, addkey=None, *args, **kwargs):
        super(License, self).__init__(*args, **kwargs)

        self.basekey = basekey
        self.addkey = addkey

    def setup(self):
        if get_version(ifc=self.ifc) < 'bigip 9.4.0' or \
           get_version(ifc=self.ifc) < 'em 1.6.0':
            raise CommandNotSupported('only in BIGIP>=9.4.0 and EM>=1.6')

        LOG.info('Licensing: %s', self.ifc)
        if self.addkey:
            addkey_str = "--addkey %s"

            if isinstance(self.addkey, basestring):
                addkey_str %= self.addkey
            else:
                addkey_str %= ' '.join(self.addkey)

        ret = self.api.run('SOAPLicenseClient --verbose --basekey %s %s' % \
                           (self.basekey, addkey_str))

        if not ret.status:
            LOG.info('Licensing: Done.')
            return True
        else:
            LOG.error(ret)
            raise SSHCommandError(ret)


relicense = None
class Relicense(SSHCommand): #@IgnorePep8
    """Calls SOAPLicenseClient against the key grepped off bigip.license.
    For: bigip 9.4.0+, em 1.6.0+

    @rtype: bool
    """
    def setup(self):
        if get_version(ifc=self.ifc) < 'bigip 9.4.0' or \
           get_version(ifc=self.ifc) < 'em 1.6.0':
            raise CommandNotSupported('only in BIGIP>=9.4.0 and EM>=1.6')

        LOG.info('relicensing: %s', self.ifc)
        ret = self.api.run('SOAPLicenseClient --basekey `grep '
                           '"Registration Key" /config/bigip.license|'
                           'cut -d: -f2`')
        if not ret.status:
            LOG.info('relicensing: Done.')
            return True
        else:
            LOG.error(ret)
            raise SSHCommandError(ret)


parse_license = None
class ParseLicense(CachedCommand, SSHCommand): #@IgnorePep8
    """Parse the bigip.license file into a dictionary.

    @param tokens_only: filter out all non license flags
    @type tokens_only: bool
    """

    def __init__(self, tokens_only=False, *args, **kwargs):
        super(ParseLicense, self).__init__(*args, **kwargs)

        self.tokens_only = tokens_only

    def __repr__(self):
        parent = super(ParseLicense, self).__repr__()
        opt = {}
        opt['tokens_only'] = self.tokens_only
        return parent + "(tokens_only=%(tokens_only)s)" % opt

    def setup(self):
        ret = self.api.run("grep -v '^\s*#' /config/bigip.license")

        if ret.status:
            LOG.error(ret)
            raise LicenseParsingError(ret)

        license_dict = {}
        for row in ret.stdout.split('\n'):
            if row.strip():
                bits = row.split(':')
                license_dict[bits[0].strip()] = bits[1].strip()

        if self.tokens_only:
            meta_keys = ('Auth vers', 'Usage', 'Vendor', 'active module',
                         'optional module', 'Registration Key', 'Platform ID',
                         'Service check date', 'Service Status', 'Dossier',
                         'Authorization', 'inactive module', 'Evaluation end',
                         'Evaluation start', 'Licensed version', 'Appliance SN',
                         'License end', 'License start', 'Licensed date')
            unwanted = set(license_dict) & set(meta_keys)
            for unwanted_key in unwanted:
                del license_dict[unwanted_key]

        return license_dict


get_prompt = None
class GetPrompt(WaitableCommand, SSHCommand): #@IgnorePep8
    """Returns the bash prompt string.

    Examples:
    [root@bp6800-123:Active] config #
    returns: 'Active'
    [root@viprioncmi:/S2-green-P:Active] config #
    returns: 'Active'

    @rtype: str
    """
    def setup(self):
        ret = self.api.run('source /etc/bashrc; if [ -x /bin/ps1 ]; '
                           'then /bin/ps1; elif [ -f /var/prompt/ps1 ]; '
                           'then getPromptStatus; else echo "!"; fi')

        if ret.status:
            LOG.error(ret)
            raise SSHCommandError(ret)

        # Viprions have the cluster info
        status = ret.stdout.strip().split(':')[-1]
        return status


reboot = None
class Reboot(SSHCommand): #@IgnorePep8
    """Runs the `reboot` command.

    @param post_sleep: number of seconds to sleep after reboot
    @type interface: int
    """
    def __init__(self, post_sleep=60, *args, **kwargs):
        super(Reboot, self).__init__(*args, **kwargs)
        self.post_sleep = post_sleep

    def setup(self):
        uptime_before = None
        try:
            ret = self.api.run('cat /proc/uptime')
            uptime_before = float(ret.stdout.split(' ')[0])
        except:
            LOG.debug('get_uptime() not available (probably a 9.3.1)')
            pass

        ret = self.api.run('reboot')

        if ret.status:
            LOG.error(ret)
            raise SSHCommandError(ret)

        LOG.debug('Reboot post sleep')
        time.sleep(self.post_sleep)
        return uptime_before


switchboot = None
class Switchboot(SSHCommand): #@IgnorePep8
    """Runs the `switchboot -b <slot>` command.

    @param post_sleep: the short-form description of a boot image location
    @type interface: str
    """
    def __init__(self, volume, *args, **kwargs):
        super(Switchboot, self).__init__(*args, **kwargs)
        self.volume = volume

    def setup(self):
        ret = self.api.run('switchboot -b %s' % self.volume)

        if ret.status:
            LOG.error(ret)
            raise SSHCommandError(ret)


install_software = None
class InstallSoftware(SSHCommand): #@IgnorePep8
    """Runs the `image2disk` command.

    @param repository: a product distribution file (an iso image), an HTTP URL,
                     or the absolute path to a local directory
    @type repository: str
    @param volume: the target volume
    @type volume: str
    @param essential: the target volume
    @type essential: str
    @param format: partitions or lvm or None. If lvm is passed and the target is
                already formatted to LVM then it will reformat it
    @type format: str
    @param repo_version: the version of the repository
    @type repo_version: Version
    """
    def __init__(self, repository, volume=None, essential=False, format=None,  # @ReservedAssignment
                 repo_version=None, progress_cb=None, is_hf=False, reboot=True,
                 *args, **kwargs):
        super(InstallSoftware, self).__init__(*args, **kwargs)

        assert callable(progress_cb), "The progress_cb must be callable!"
        self.repository = repository
        self.volume = volume
        self.essential = essential
        self.format = format
        self.repo_version = repo_version
        self.progress_cb = progress_cb
        self.is_hf = is_hf
        self.reboot = reboot

    def setup(self):
        opts = []

        if (self.version.product.is_bigip and self.version < 'bigip 10.0' or
           self.version.product.is_em and self.version < 'em 2.0'):
            self.api.run('im %s' % self.repository)

        if self.essential:
            opts.append('--nosaveconfig')

        if self.format == 'lvm':
            opts.append('--format=volumes')
        elif self.format == 'partitions':
            opts.append('--format=partitions')
        else:
            if (self.version.product.is_bigip and self.version >= 'bigip 10.1.0' or
               self.version.product.is_em and self.version >= 'em 2.0' or
               self.version.product.is_bigiq):
                opts.append('--force')
            #else:
                #raise NotImplementedError('upgrade path not supported')

        v = max(self.repo_version, self.version)
        if not (self.format and
            v.product.is_bigip and v >= 'bigip 10.2.1' or
            v.product.is_em and v >= 'em 2.1.0' or
            v.product.is_bigiq):
            opts.append('--instslot %s' % self.volume)

        opts.append('--setdefault')

        if self.is_hf:
            opts.append('--hotfix')

        if self.reboot:
            opts.append('--reboot')
        opts.append(self.repository)
        #if self.format:
        #    opts.append(self.repository)

        ret = self.api.run_wait('image2disk %s' % ' '.join(opts),
                                progress=self.progress_cb)

        # status == -1 when the connection is lost.
        if ret.status > 0:
            LOG.error(ret)
            raise SSHCommandError(ret)


audit_software = None
class AuditSoftware(SSHCommand): #@IgnorePep8
    """Parses the output of the software audit script.
    Version dependent.

    @rtype: dict
    """
    def setup(self):
        if self.version.product.is_bigip and self.version < 'bigip 10.2.2' or \
           self.version.product.is_em and self.version < 'em 3.0':
            audit_script = '/usr/sbin/audit'
        else:
            audit_script = '/usr/libexec/iControl/software_audit'

        ret = self.api.run('%s /tmp/f5test2_audit' % audit_script)
        assert not ret.status, "audit script failed"
        ret = self.api.run('cat /tmp/f5test2_audit')
        if not ret.status:
            return audit_parse(ret.stdout)
        else:
            LOG.error(ret)
            raise SSHCommandError(ret)


collect_logs = None
class CollectLogs(SSHCommand): #@IgnorePep8
    """Collects tails from different log files.

    @param last: how many lines to tail
    @type last: int
    """
    def __init__(self, dir, last=100, *args, **kwargs):  # @ReservedAssignment
        super(CollectLogs, self).__init__(*args, **kwargs)
        self.dir = dir
        self.last = last

    def setup(self):
        # Common
        files = ['/var/log/ltm', '/var/log/messages',
                '/var/log/httpd/httpd_errors']
        v = abs(self.version)

        # EM specific
        if v.product.is_em:
            files.append('/var/log/em')
            files.append('/var/log/emrptschedd.log')

        # UI
        if v.product.is_bigip and v > 'bigip 10.0' \
        or v.product.is_em and v > 'em 2.0' \
        or v.product.is_bigiq:
            files.append('/var/log/tomcat/catalina.out')
            files.append('/var/log/liveinstall.log')
            files.append('/var/log/webui.log')
        else:
            files.append('/var/log/tomcat4/catalina.out')

        # REST API
        if v.product.is_bigip and v >= 'bigip 11.4' \
        or v.product.is_em and v >= 'em 3.2' \
        or v.product.is_bigiq:
            files.append('/var/log/restjavad.0.log')

        for filename in files:
            ret = self.api.run('tail -n %d %s' % (self.last, filename))
            local_file = os.path.join(self.dir, os.path.basename(filename))
            with open(local_file, "wt") as f:
                f.write(ret.stdout)

        # Gather the qkview-lite *.tech.out output.
        # Not available in solstice+
        if v.product.is_bigip and v < 'bigip 10.2.2' \
        or v.product.is_em and v < 'em 3.0':
            ret = self.api.run('qkview-lite')
            self.api.get('/var/log/*.tech.out', self.dir, move=True)

        if ret.status:
            LOG.error(ret)
            raise SSHCommandError(ret)


file_exists = None
class FileExists(WaitableCommand, SSHCommand): #@IgnorePep8
    """Checks whether a file exists or not on the remote system.

    @rtype: bool
    """
    def __init__(self, filename, *args, **kwargs):
        super(FileExists, self).__init__(*args, **kwargs)
        self.filename = filename

    def setup(self):
        try:
            self.api.stat(self.filename)
            return True
        except IOError, e:
            if e.errno == 2:
                return False
            raise


cores_exist = None
class CoresExist(SSHCommand): #@IgnorePep8
    """Checks for core files.

    @rtype: bool
    """
    def setup(self):
        ret = self.api.run('ls -1 /var/core|wc -l')

        if not ret.status:
            return bool(int(ret.stdout))
        else:
            LOG.error(ret)
            raise SSHCommandError(ret)


remove_em = None
class RemoveEm(SSHCommand): #@IgnorePep8
    """Remove all EM certificates.
    """
    def setup(self):
        # Avoid deleting self certificate in EM 2.3+ which discovers itself.
        # Alternative: shopt -s extglob && rm !(file1|file2|file3)
        self.api.run('ls /shared/em/ssl.crt/*|grep -v 127.0.0.1|xargs rm -f')
        self.api.run('rm -f /shared/em/ssl.key/*')
        self.api.run('rm -f /config/big3d/client.crt')
        self.api.run('bigstart restart big3d')


get_big3d_version = None
class GetBig3dVersion(SSHCommand): #@IgnorePep8
    """Get the currently running big3d version.

    @rtype: Version
    """
    def setup(self):
        self.api.run('rm -f /config/gtm/server.crt')
        ret = self.api.run('iqsh 127.1.1.1')
        m = re.search(r'<big3d>(.*?)</big3d>', ret.stdout)
        if not m:
            raise CommandError('Version not found in "%s"!' % ret.stdout)

        # big3d Version 10.4.0.11.0
        return Version(m.group(1).split(' ')[2])


enable_debug_log = None
class EnableDebugLog(SSHCommand): #@IgnorePep8
    """
    Enable iControl debug logs. Check /var/log/ltm for more info.

    @param enable: Enable/disable
    @type enable: bool
    """
    def __init__(self, daemon, enable=True, *args, **kwargs):
        super(EnableDebugLog, self).__init__(*args, **kwargs)
        #self.daemon = daemon
        self.enable = enable
        daemon_map = Options()

        # iControl
        daemon_map.icontrol = {}
        daemon_map.icontrol.name = 'iControl'
        daemon_map.icontrol.dbvar = 'iControl.LogLevel'
        daemon_map.icontrol.disable = 'none'
        daemon_map.icontrol.post = 'bigstart restart httpd'

        # EM deviced
        daemon_map.emdeviced = {}
        daemon_map.emdeviced.name = 'EM deviced'
        daemon_map.emdeviced.dbvar = 'log.em.device.level'

        # EM swimd
        daemon_map.emswimd = {}
        daemon_map.emswimd.name = 'EM swimd'
        daemon_map.emswimd.dbvar = 'log.em.swim.level'

        self.daemon = daemon_map.get(daemon)
        assert self.daemon, "Daemon '%s' not defined." % daemon

    def setup(self):
        v = self.ifc.version
        if v.product.is_bigip and v < 'bigip 9.4.0':
            setdb = 'b db'
        else:
            setdb = 'setdb'

        d = self.daemon
        d.setdb = setdb
        d.setdefault('enable', 'debug')
        d.setdefault('disable', 'notice')

        if self.enable:
            LOG.debug('Enable debug log for %s', d.name)
            command = '%(setdb)s %(dbvar)s %(enable)s' % d
        else:
            LOG.debug('Disable debug log for %s', d.name)
            command = '%(setdb)s %(dbvar)s %(disable)s' % d

        if d.pre:
            command = d.pre + ';' + command
        if d.post:
            command = command + ';' + d.post

        self.api.run(command)


parse_version_file = None
class ParseVersionFile(SSHCommand): #@IgnorePep8
    """Parse the /VERSION file and return a dictionary."""

    def setup(self):
        return parse_keyvalue_file('/VERSION', mode=KV_COLONS, ifc=self.ifc)
