from .base import IcontrolCommand
from ..base import CachedCommand, WaitableCommand
from ...utils import Version
from ...utils.parsers.version_file import colon_pairs_dict
from ...interfaces.config import ConfigInterface, KEYSET_LOCK, KEYSET_ALL
from ...interfaces.icontrol import IcontrolInterface, AuthFailed
from ...interfaces.icontrol.driver import UnknownMethod, IControlFault
import base64
import time

import logging
LOG = logging.getLogger(__name__)
DF_CHUNK_SIZE = 1024 * 1024  # 1MB


get_version = None
class GetVersion(IcontrolCommand):
    """Get the active software version."""

    def setup(self):
        ic = self.api
        db = ic.Management.DBVariable
        version = ' '.join([x['value'] for x in db.query(variables=['version.product',
                                                                    'version.version',
                                                                    'version.build'])])
        return Version(version)


get_platform = None
class GetPlatform(CachedCommand, IcontrolCommand):
    """Get the platform ID."""

    def setup(self):
        ic = self.api
        return ic.System.SystemInfo.get_system_information()['platform']


upload_file = None
class UploadFile(IcontrolCommand):
    """
    Upload a local file.
    """

    def __init__(self, filename, stream, *args, **kwargs):
        super(UploadFile, self).__init__(*args, **kwargs)
        self.filename = filename
        self.stream = stream

    def setup(self):
        ic = self.api

        done = False
        first = True
        while not done:
            text = base64.b64encode(self.stream.read(DF_CHUNK_SIZE))

            if first:
                chain_type = 'FILE_FIRST'
                first = False
            else:
                if len(text) < DF_CHUNK_SIZE:
                    chain_type = 'FILE_LAST'
                    done = True
                else:
                    chain_type = 'FILE_MIDDLE'

            ic.System.ConfigSync.upload_file(file_name=self.filename,
                                             file_context=dict(file_data=text,
                                                               chain_type=chain_type))


download_file = None
class DownloadFile(IcontrolCommand):
    """
    Download a remote file.
    """

    def __init__(self, filename, *args, **kwargs):
        super(DownloadFile, self).__init__(*args, **kwargs)
        self.filename = filename

    def setup(self):
        ic = self.api

        chunks = []
        done = False
        offset = 0
        while not done:
            ret = ic.System.ConfigSync.download_file(file_name=self.filename,
                                                     chunk_size=DF_CHUNK_SIZE,
                                                     file_offset=offset)
            done = ret['return']['chain_type'] in ('FILE_FIRST_AND_LAST',
                                                   'FILE_LAST')
            chunks.append(ret['return']['file_data'])
            offset = ret['file_offset']

        return ''.join(chunks)


parse_version_file = None
class ParseVersionFile(IcontrolCommand):
    """Parse the /VERSION file and return a dictionary."""

    def setup(self):
        ret = download_file('/VERSION', ifc=self.ifc)
        return colon_pairs_dict(ret)


set_password = None
class SetPassword(WaitableCommand, IcontrolCommand):
    """Resets the password for admin and root accounts.

    @param adminpassword: new password the admin user
    @type adminpassword: str
    @param rootpassword: new password the root user
    @type rootpassword: str
    """

    def __init__(self, keyset=KEYSET_LOCK, *args, **kwargs):
        super(SetPassword, self).__init__(*args, **kwargs)

        self.keyset = keyset

    def setup(self):
        """- Change the active partition to 'Common'.
           - Set passwords to both 'admin' and 'root' accounts.
        """
        config = ConfigInterface()
        assert self.ifc.device
        alias = self.ifc.device.get_alias()
        access = config.get_device(device=alias)

        admin = config.get_device(alias).get_admin_creds(keyset=self.keyset)
        root = config.get_device(alias).get_root_creds(keyset=self.keyset)

        for cred in access.get_admin_creds(keyset=KEYSET_ALL).values():
            ic = IcontrolInterface(address=access.address,
                                   username=cred.username,
                                   password=cred.password).open()
            try:
                try:
                    ic.Management.Partition.set_active_partition(
                                                      active_partition='Common')
                except UnknownMethod:
                    LOG.debug('%s must be a 9.3.1.', access.address)
                ic.Management.UserManagement.change_password(
                    user_names=[admin.username, root.username],
                    passwords=[admin.password, root.password])
                LOG.info('Passwords on %s set (%s, %s).',
                         access.address, admin, root)
                access.specs._keyset = self.keyset
                return True
            except AuthFailed:
                LOG.info('Bad credential "%s" for %s.', cred, access.address)
                continue

        LOG.warning('Password on %s not set.', access.address)
        return False


reboot = None
class Reboot(IcontrolCommand):
    """Reboot the system.

    @param post_sleep: number of seconds to sleep after reboot
    @type interface: int
    """

    def __init__(self, post_sleep=60, *args, **kwargs):
        super(Reboot, self).__init__(*args, **kwargs)
        self.post_sleep = post_sleep

    def setup(self):
        ic = self.api
        uptime_before = None
        try:
            uptime_before = ic.System.SystemInfo.get_uptime()
        except:
            LOG.debug('get_uptime() not available (probably a 9.3.1)')
            pass
        ic.System.Services.reboot_system(seconds_to_reboot=0)

        LOG.debug('Reboot post sleep')
        time.sleep(self.post_sleep)

        return uptime_before


has_rebooted = None
class HasRebooted(WaitableCommand, IcontrolCommand):
    """Get the uptime.

    @param post_sleep: number of seconds to sleep after reboot
    @type interface: int
    """

    def __init__(self, uptime, *args, **kwargs):
        super(HasRebooted, self).__init__(*args, **kwargs)
        self.uptime = uptime

    def setup(self):
        ic = self.api
        try:
            return ic.System.SystemInfo.get_uptime() < self.uptime
        except:
            return True


is_service_up = None
class IsServiceUp(WaitableCommand, IcontrolCommand):
    """Returns the state of TOMCAT service.
    """

    def __init__(self, service, *args, **kwargs):
        super(IsServiceUp, self).__init__(*args, **kwargs)
        self.service = service

    def setup(self):
        ic = self.api
        service = 'SERVICE_' + self.service
        status = ic.System.Services.get_service_status(
                                                services=[service])[0]
        return status['status'] == 'SERVICE_STATUS_UP'


file_exists = None
class FileExists(WaitableCommand, IcontrolCommand):
    """Checks the existence of a remote file.
    """

    def __init__(self, filename, *args, **kwargs):
        super(FileExists, self).__init__(*args, **kwargs)
        self.filename = filename

    def setup(self):
        ic = self.api
        try:
            ic.System.ConfigSync.download_file(file_name=self.filename,
                                               chunk_size=10, file_offset=0)
            return True
        except IControlFault, e:
            if 'Error opening file for read operations' in e.faultstring:
                return False
            raise
