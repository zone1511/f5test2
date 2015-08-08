"""All commands that run over the SSH interface."""

from .base import SSHCommand, CommandNotSupported, SSHCommandError
from ..base import CachedCommand, WaitableCommand, CommandError, ContextManagerCommand
from ...base import Options, AttrDict
from ...interfaces.subprocess import ShellInterface
from ...interfaces.ssh import SSHInterface
from ...interfaces.testcase import LOGCOLLECT_CONTAINER
from ...utils.parsers.version_file import colon_pairs_dict, equals_pairs_dict
from ...utils.parsers.audit import audit_parse
from ...utils.version import Version
from ...utils.wait import wait, wait_args
from paramiko import RSAKey
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
class Generic(WaitableCommand, SSHCommand):  # @IgnorePep8
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
class ScpPut(SSHCommand):  # @IgnorePep8
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
                   # '-c arcfour256',  # High performance cipher.
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
class ScpGet(ScpPut):  # @IgnorePep8
    upload = False


parse_keyvalue_file = None
class ParseKeyvalueFile(SSHCommand):  # @IgnorePep8
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
class GetVersion(SSHCommand):  # @IgnorePep8
    """Parses the /VERSION file and returns a version object.
    For: bigip 9.3.1+, em 1.6.0+

    @rtype: Version
    """

    def setup(self):
        """SCP a file from local system to one device."""
        ret = parse_keyvalue_file('/VERSION', mode=KV_COLONS, ifc=self.ifc)
        return Version("%(product)s %(version)s %(build)s" % ret)


get_platform = None
class GetPlatform(CachedCommand, SSHCommand):  # @IgnorePep8
    """Parses the /PLATFORM file and return a dictionary.
    For: bigip 9.3.1+, em 1.6.0+

    @rtype: dict
    """
    def setup(self):
        return parse_keyvalue_file('/PLATFORM', mode=KV_EQUALS, ifc=self.ifc)


license = None  # @ReservedAssignment
class License(SSHCommand):  # @IgnorePep8
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
class Relicense(SSHCommand):  # @IgnorePep8
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
class ParseLicense(CachedCommand, SSHCommand):  # @IgnorePep8
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
class GetPrompt(WaitableCommand, SSHCommand):  # @IgnorePep8
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
class Reboot(SSHCommand):  # @IgnorePep8
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
class Switchboot(SSHCommand):  # @IgnorePep8
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
class InstallSoftware(SSHCommand):  # @IgnorePep8
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
            # else:
                # raise NotImplementedError('upgrade path not supported')

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
        # if self.format:
        #    opts.append(self.repository)

        ret = self.api.run_wait('image2disk %s' % ' '.join(opts),
                                progress=self.progress_cb)

        # status == -1 when the connection is lost.
        if ret.status > 0:
            LOG.error(ret)
            raise SSHCommandError(ret)


audit_software = None
class AuditSoftware(SSHCommand):  # @IgnorePep8
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
class CollectLogs(SSHCommand):  # @IgnorePep8
    """Collects tails from different log files.

    @param last: how many lines to tail
    @type last: int
    """
    LINE_COUNT = 100

    def __init__(self, dir, *args, **kwargs):  # @ReservedAssignment
        super(CollectLogs, self).__init__(*args, **kwargs)
        self.dir = dir

    def setup(self):
        # Common
        files = ['/var/log/ltm', '/var/log/messages']
        v = abs(self.version)

        # httpd removed in bigiq 4.3
        if not (v.product.is_bigiq and v > 'bigiq 4.2'):
            files.append('/var/log/httpd/httpd_errors')

        # EM specific
        if v.product.is_em:
            files.append('/var/log/em')
            files.append('/var/log/emrptschedd.log')

        # UI
        if v.product.is_bigip and v > 'bigip 10.0' \
        or v.product.is_em and v > 'em 2.0' \
        or v.product.is_bigiq:
            files.append('/var/log/liveinstall.log')
            if not v > 'bigiq 4.0':
                files.append('/var/log/tomcat/catalina.out')
                files.append('/var/log/webui.log')
            if v >= 'bigiq 4.2':
                files.append('/var/log/guiserver.out')
            if v >= 'bigiq 4.3' and v <= 'bigiq 4.4':
                files.append('/var/log/nginx_errors.log')
            if v >= 'bigiq 4.5':
                files.append('/var/log/webd/errors.log*')
        else:
            files.append('/var/log/tomcat4/catalina.out')

        # REST API
        if v.product.is_bigip and v >= 'bigip 11.4' \
        or v.product.is_em and v >= 'em 3.2' \
        or v.product.is_bigiq:
            files.append('/var/log/restjavad.0.log')

        # SELinux API
        if v.product.is_bigip and v >= 'bigip 11.5' \
        or v.product.is_bigiq:
            files.append('/var/log/auditd/audit.log')

        # ASM
        if v.product.is_bigip and v >= 'bigip 11.5':
            files.append('/var/log/asm')

        if v.product.is_bigiq and v >= 'bigiq 4.4':
            files.append('/var/log/restjavad*.0.log')

        for filename in files:
            ret = self.api.run('tail -n %d %s' % (self.LINE_COUNT, filename))
            local_file = os.path.join(self.dir, os.path.basename(filename))
            local_file = local_file.replace('*', '_')
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
class FileExists(WaitableCommand, SSHCommand):  # @IgnorePep8
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
class CoresExist(SSHCommand):  # @IgnorePep8
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
class RemoveEm(SSHCommand):  # @IgnorePep8
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
class GetBig3dVersion(SSHCommand):  # @IgnorePep8
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
class EnableDebugLog(SSHCommand):  # @IgnorePep8
    """
    Enable iControl debug logs. Check /var/log/ltm for more info.

    @param enable: Enable/disable
    @type enable: bool
    """
    def __init__(self, daemon, enable=True, *args, **kwargs):
        super(EnableDebugLog, self).__init__(*args, **kwargs)
        # self.daemon = daemon
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
class ParseVersionFile(SSHCommand):  # @IgnorePep8
    """Parse the /VERSION file and return a dictionary."""

    def setup(self):
        return parse_keyvalue_file('/VERSION', mode=KV_COLONS, ifc=self.ifc)


is_cluster = None
class IsCluster(CachedCommand, SSHCommand):  # @IgnorePep8
    """Check to see if the platfom we're running on is a cluster."""

    def setup(self):
        v = self.ifc.version
        if v.product.is_bigip and v > 'bigip 10.0.0':
            return self.api.run('getdb clustered.environment').stdout.strip() == 'true'
        return False


key_exchange = None
class KeyExchange(SSHCommand):  # @IgnorePep8
    """Exchange SSH key between two remote devices."""
    AUTHORIZED_KEYS = '.ssh/authorized_keys'
    IDENTITY_SSH1 = '/root/.ssh/identity'  # Hardcoded because ssh always look here even though $HOME is not /root

    def __init__(self, device, address=None, *args, **kwargs):
        super(KeyExchange, self).__init__(*args, **kwargs)
        self.device = device
        self.address = address if address else self.device.address

    def setup(self):
        LOG.debug('Doing key exchange between %s and %s', self.api.address,
                  self.device.get_address())
        sftp = self.api.sftp()

        # Currently works only with RSA keys (v1)
        f = sftp.open(KeyExchange.IDENTITY_SSH1)
        pk = RSAKey.from_private_key(f)
        with SSHInterface(device=self.device) as sshifc:
            sshifc.api.exchange_key(key=pk, name=self.api.address)

        # Make sure known_hosts is updated
        self.api.run('ssh-keygen -R %s' % self.address)
        self.api.run('ssh -n -o StrictHostKeyChecking=no root@%s /bin/true' % 
                     self.address)


audit_port = None
class AuditPort(SSHCommand):  # @IgnorePep8
    """Checks if a port is opened. It will return either incoming/outgoing
    for string result use: str(@return.stdout)
    @return: SSHResult
    """

    def __init__(self, port, *args, **kwargs):
        super(AuditPort, self).__init__(*args, **kwargs)
        self.port = port

    def setup(self):
        return self.api.run('netstat -anp |grep "{0}"'.format(self.port))

wait_for_port_closing = None
class WaitForPortClosing(SSHCommand):  # @IgnorePep8
    """Waits for a port to be closed. Incoming only
    @return: Bool
    """
    def __init__(self, port, timeout=20, interval=5, *args, **kwargs):
        super(WaitForPortClosing, self).__init__(*args, **kwargs)
        self.port = port
        self.timeout = timeout
        self.interval = interval

    def setup(self):
        def is_port_released():
            x = self.api.run('netstat -anp |grep ":{0} "'.format(self.port))
            LOG.debug("Audit PORT Status (check for closed): status/stdout/stderr: '{0}'/'{1}'/'{2}'"
                      .format(x.status, str(x.stdout), str(x.stderr)))
            if (x.status == 1 and str(x.stdout) == "" and str(x.stderr) == ""):
#                 or ((x.status == 0 and str(x.stderr) == "" and \
#                      (str(self.port) + " ") not in str(x.stdout) and \
#                         (str(self.port) + "/") not in str(x.stdout))):
                return True
        wait(is_port_released,
             progress_cb=lambda x: "PORT Not released yet...",
             timeout=self.timeout,
             interval=self.interval,
             timeout_message="Port not released after {0}s")
        return True

wait_for_port_opening = None
class WaitForPortOpening(SSHCommand):  # @IgnorePep8
    """Waits for a port to be opened. Incoming only
    @return: Bool
    """
    def __init__(self, port, timeout=16, interval=2, *args, **kwargs):
        super(WaitForPortOpening, self).__init__(*args, **kwargs)
        self.port = port
        self.timeout = timeout
        self.interval = interval

    def setup(self):
        def is_port_opened():
            x = self.api.run('netstat -anp |grep ":{0} "'.format(self.port))
            LOG.debug("Audit PORT Status (check for opened): status/stdout/stderr: '{0}'/'{1}'/'{2}'"
                      .format(x.status, str(x.stdout), str(x.stderr)))
            return "LISTEN" in str(x.stdout)
        wait(is_port_opened,
             progress_cb=lambda x: "PORT Not Opened yet...",
             timeout=self.timeout,
             interval=self.interval,
             timeout_message="Port not Opened after {0}s")
        return True

get_current_micros = None
class GetCurrentMicros(SSHCommand):  # @IgnorePep8
    """Returns the number of seconds + X no of current nanoseconds since the epoch
    @return: string
    """

    def __init__(self, n=None, *args, **kwargs):
        super(GetCurrentMicros, self).__init__(*args, **kwargs)
        if not n:
            n = 6
        self.n = n

    def setup(self):
        return (str(self.api.run('date +"%s%{0}N"'.format(self.n)).stdout)).rstrip()

get_system_stats = None
class GetSystemStats(SSHCommand):  # @IgnorePep8
    """ Returns values for current disk usage, current cpu usage,
    and memory usage.
    @return: dict
    """
    def __init__(self, partition=None, *args, **kwargs):
        super(GetSystemStats, self).__init__(*args, **kwargs)
        if not partition:
            partition = '/'
        self.partition = partition

    def setup(self):
        self.usage_stats = AttrDict()
        cpuUse = str(self.ifc.api.run("mpstat -P ALL | awk '{print $10}'").
                    stdout).strip().split('\n')[1:]  # skip header line
        self.usage_stats.CPU = cpuUse[0]
        self.usage_stats.CPUPERCORE = cpuUse[1:]  # get all but cpu average
        self.usage_stats.DISK = (str(self.ifc.api.run("df %s | tail -1 | awk '{print $4+0}'" % self.partition).stdout)).rstrip()
        self.usage_stats.MEM = (str(self.ifc.api.run("free -m | grep Mem | awk '{print $3/$2 * 100.0}'").stdout)).rstrip()
        self.usage_stats.CPUFORMATTED = "%.2f%%" % (
                        100 - float(self.usage_stats.CPU))
        self.usage_stats.CPUFORMATTEDPERCORE = []
        for cpu in self.usage_stats.CPUPERCORE:
            self.usage_stats.CPUFORMATTEDPERCORE.append("%.2f%%" % (
                        100 - float(cpu)))
        return self.usage_stats


get_running_processes = None
class GetRunningProcesses(SSHCommand):  # @IgnorePep8
    """
    Retrieves the processes by CPU usage as a list
    If no count is passed, all procs are returned.
    Otherwise it will retrieve <count> off the top
    e.g. count=10 would be the top 10 processes
    @return: list
    """
    def __init__(self, count=None, *args, **kwargs):
        super(GetRunningProcesses, self).__init__(*args, **kwargs)
        self.count = count

    def setup(self):
        if self.count:
            self.top_procs = self.ifc.api.run("ps axo %%cpu,%%mem,args | sort -rb | head -n %s" % self.count).stdout.strip().split('\n')
        else:
            self.top_procs = self.ifc.api.run("ps axo %%pu,%%mem,args | sort -rb" % self.count).stdout.strip().split('\n')
        return self.top_procs


port_redirector = None
class PortRedirector(SSHCommand, ContextManagerCommand):  # @IgnorePep8
    """Used to execute commands while a port redirector is running on host

    $ socat -d -d -ls TCP4-LISTEN:8083,fork,reuseaddr TCP4:localhost:8100 &
    <execute your code>
    $ kill $!
    """
    def __init__(self, port, dest_host='localhost', dest_port=8100,
                 proto='TCP4-LISTEN', dest_proto='TCP4',
                 *args, **kwargs):
        super(PortRedirector, self).__init__(*args, **kwargs)
        self.port = port
        self.dest_host = dest_host
        self.dest_port = dest_port
        self.proto = proto
        self.dest_proto = dest_proto
        self.shell = None
        self.pid = None

    def prep(self):
        super(PortRedirector, self).prep()
        shell = self.ifc.api.interactive()
        shell.sendline('socat -d -d -ls {0.proto}:{0.port},fork,reuseaddr {0.dest_proto}:{0.dest_host}:{0.dest_port} &'.
                       format(self))
        # TODO: check for failure to start
        shell.expect('\[\d+\] (\d+)')
        self.pid = int(shell.match.groups()[0])
        self.shell = shell

    def cleanup(self):
        try:
            self.shell.expect('#')
            self.shell.sendline('kill {0} && wait {0}'.format(self.pid))
        finally:
            self.shell.close()


tcpdump = None
class Tcpdump(SSHCommand, ContextManagerCommand):  # @IgnorePep8
    """Used to execute commands while tcpdump is running. It also passes it to
    logcollect plugin via testcase instance (optional).

    By default it'll capture any packet on eth0. This behavior can be changed
    via the arguments parameter.

    $ tcpdump -nni eth0 -s0 -w /tmp/a.cap &
    <execute your code>
    $ kill $!

    @param filename: The full path to the .cap file (default /tmp/tcpdump.cap)
    @type filename: str
    @param arguments: tcpdump arguments
    @type arguments: str
    @param test: TestCase instance if used from inside a testcase (optional)
    @type test: <f5test.interfaces.testcase.InterfaceTestCase> instance

    @author: i.turturica@f5.com
    """
    def __init__(self, filename='/tmp/tcpdump.cap', arguments=None, test=None,
                 *args, **kwargs):
        super(Tcpdump, self).__init__(*args, **kwargs)
        self.filename = filename
        self.arguments = arguments if arguments else '-nni eth0 -s0'
        self.test = test
        self.shell = None

    def prep(self):
        super(Tcpdump, self).prep()
        shell = self.ifc.api.interactive()
        shell.sendline('tcpdump {} -w {} &'.format(self.arguments, self.filename))
        self.shell = shell
        if self.test:
            name = os.path.basename(self.filename)
            self.test.set_data((self.ifc, self.filename), name,
                               container=LOGCOLLECT_CONTAINER)

    def cleanup(self):
        try:
            self.shell.send('kill $!')
        finally:
            self.shell.close()


get_file_metadata = None
class GetFileMetadata(SSHCommand):  # @IgnorePep8
    """
    - Use when information of a large quantity of files/directories is needed and stat is too slow
    - Retrieves all files from a given directory or an individual file
    - If no filename filter is passed, it will return all files
    - Will return a list of dictionaries related to each file like so:
        Example: [{'file_name': 'name1',
                            'type': 'file',
                            'size': XXXX, 
                            'mtime': 'XX-XX-XX XX:XX:XX', 
                            'owner': 'ownername', 
                            'group': 'groupname', 
                            'permissions': '-rwxr-xr-x'}},
                        {'file_name': 'name2',
                            'type': 'directory',
                            'size': XXXX, 
                            etc:etc}]
    @return: list
    """
    def __init__(self, path=None, query_term=None, *args, **kwargs):
        super(GetFileMetadata, self).__init__(*args, **kwargs)
        self.path = path
        if query_term:
            self.query_term = query_term
        else:
            self.query_term = None

    def setup(self):
        dir_contents = []
        if self.query_term:
            dir_results = self.ifc.api.run('ls -qlSA --time-style=+%%s %s | grep -F %s'
                % (self.path, self.query_term)).stdout.split('\n')
        else:
            dir_results = self.ifc.api.run('ls -qlSA --time-style=+%%s %s' % self.path).stdout.split('\n')
        for each in dir_results[1:]:
            # Check for empty string
            if each:
                split_filedata = each.split(' ')
                split_stats = [x for x in split_filedata if x]
                filename = split_stats[6]
                filedata = AttrDict()
                filedata.file_name = filename
                if split_stats[0].startswith('-'):
                    filedata.type = 'file'
                elif split_stats[0].startswith('d'):
                    filedata.type = 'directory'
                elif split_stats[0].startswith('l'):
                    filedata.type = 'link'
                else:
                    filedata.type = 'UNKNOWN'
                filedata.permissions = split_stats[0]
                filedata.owner = split_stats[2]
                filedata.group = split_stats[3]
                filedata.size = split_stats[4]
                filedata.mtime = split_stats[5]
            dir_contents.append(filedata)
        return dir_contents

change_date = None
class ChangeDate(SSHCommand):  # @IgnorePep8
    """Change date through ssh
    (changing in utc if with_local_tz is False) - Default.
    @param todate: string in ISO 8610: 2013-10-07T15:27:26
    @return string: date now in ISO 8610 - utc format with rfc-822
    """
    def __init__(self, todate, with_local_tz=False, *args, **kwargs):
        super(ChangeDate, self).__init__(*args, **kwargs)
        self.todate = todate
        self.with_local_tz = with_local_tz

    def setup(self):

        nowu = str(self.ifc.api.run('date -u +"%Y-%m-%dT%H:%M:%S.%3N%z"').stdout).rstrip()
        nowl = str(self.ifc.api.run('date +"%Y-%m-%dT%H:%M:%S.%3N%z"').stdout).rstrip()
        # micros_now = get_current_micros(ifc=ifc)
        LOG.info("Date Was: [{0} | {1}]".format(nowu, nowl))
        LOG.info("Changing date to [{1}] [{0}]..."
                 .format(self.todate, "UTC" if not self.with_local_tz else "LTZ"))
        utcformat = None
        localdate = None
        if not self.with_local_tz:
            # utc format: 100700002013.00 - [MMDDhhmm[[CC]YY][.ss]]
            utcformat = (self.todate[5:7] +  # MM
                         self.todate[8:10] +  # DD
                         self.todate[11:13] +  # hh
                         self.todate[14:16] +  # mm
                         self.todate[:4] + "." +  # YYYY
                         self.todate[-2:])  # ss
            self.ifc.api.run('date -u "{0}"'.format(utcformat))
        else:
            # "MM/DD/YYYY HH:MM:SS"
            localdate = (self.todate[5:7] + "/" +  # MM
                         self.todate[8:10] + "/" +  # DD
                         self.todate[:4] + " " +  # YYYY
                         self.todate[11:13] + ":" +  # hh
                         self.todate[14:16] + ":" +  # mm
                         self.todate[-2:])  # ss
            self.ifc.api.run('date -s "{0}"'.format(localdate))

        nowu = str(self.ifc.api.run('date -u +"%Y-%m-%dT%H:%M:%S.%3N%z"').stdout).rstrip()
        nowl = str(self.ifc.api.run('date +"%Y-%m-%dT%H:%M:%S.%3N%z"').stdout).rstrip()
        # micros_now = get_current_micros(ifc=ifc)
        LOG.info("New Date shows: [{0} | {1}]".format(nowu, nowl))
        if not self.with_local_tz:
            assert nowu.startswith(self.todate[:4]), "Date was not changed properly..."
        else:
            assert nowl.startswith(self.todate[:4]), "Date was not changed properly..."
        # return now[-4:-2] + ":" + now[-2:]
        return nowu

wait_for_year = None
class WaitForYear(SSHCommand):  # @IgnorePep8
    """wait for the date to start/not start with a specified year.
    to be used when changing dates or ntps, etc..
    """
    def __init__(self, year, negated=False, *args, **kwargs):
        super(WaitForYear, self).__init__(*args, **kwargs)
        self.year = [year]
        self.negated = negated

    def setup(self):
        self.now = None

        def is_year(year):
            self.now = str(self.api.run('date -u +"%Y-%m-%dT%H:%M:%S.%3N%z"').stdout).rstrip()
            return self.now.startswith(year) if not self.negated else not self.now.startswith(year)
        wait_args(is_year, self.year,
                  progress_cb=lambda x: "Year still not changed...Got: [{0}]".format(self.now),
                  timeout=60, interval=1,
                  timeout_message="Check year failed, tried for {0}s..")

scan_for_error_threshold = None
class ScanForErrorThreshold(SSHCommand):  # @IgnorePep8
    def __init__(self, level="WARNING", threshold=1000, *args, **kwargs):
        super(ScanForErrorThreshold, self).__init__(*args, **kwargs)
        self.level = level
        self.command = 'grep "{}" /var/log/restjavad.*.log'.format(level)
        self.threshold = threshold
        self.errormsg = "Found %s {0} messages, threshold is {1}".format(level, threshold)

    def setup(self):
        ssh_response = self.api.run(self.command)
        # grep returns a non-zero exit status if it doesn't find the search pattern. Won't complain
        # if log files are missing, but will be logged as a warning by ssh.driver. Add
        # "and ssh_response.stderr != ''" check here if that becomes a problem for some reason.
        if ssh_response.status != 0:
            LOG.info("No {} messages found.".format(self.level))
            return
        errors = ssh_response.stdout.strip()
        LOG.debug(errors)
        errorcount = len(errors.split('\n'))
        assert (errorcount < self.threshold), self.errormsg % errorcount
