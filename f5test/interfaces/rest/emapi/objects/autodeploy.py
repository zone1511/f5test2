'''
Created on Jan 9, 2014

/mgmt/cm/autodeploy workers

@author: jono
'''
from .....base import AttrDict, enum
from ...base import BaseApiObject
from .base import Reference
from .....utils.wait import wait


# Ref- https://peterpan.f5net.com/twiki/bin/view/Cloud/CMAPIAutodeploySoftwareImages
class Image(BaseApiObject):
    URI = '/mgmt/cm/autodeploy/software-images'
    ITEM_URI = '/mgmt/cm/autodeploy/software-images/%s'


# Ref- https://peterpan.f5net.com/twiki/bin/view/Cloud/CMAPIAutodeployConfigs
class StoredConfig(BaseApiObject):
    URI = '/mgmt/cm/autodeploy/stored-configs'
    ITEM_URI = '/mgmt/cm/autodeploy/stored-configs/%s'

    def __init__(self, *args, **kwargs):
        super(StoredConfig, self).__init__(*args, **kwargs)
        self.setdefault('description', 'sample_description')


# Ref- https://peterpan.f5net.com/twiki/bin/view/Cloud/CMAPIRebootDeviceWorker
class RebootDevice(BaseApiObject):
    URI = '/mgmt/cm/autodeploy/reboot-device'

    def __init__(self, *args, **kwargs):
        super(RebootDevice, self).__init__(*args, **kwargs)
        self.setdefault('netboot', 'disable')
        self.setdefault('reboot', True)
        self.setdefault('volumes', [])


# Ref- https://peterpan.f5net.com/twiki/bin/view/Cloud/CMAPIAutodeployJobs
class AutodeployJob(BaseApiObject):
    URI = '/mgmt/cm/autodeploy/jobs'
    ITEM_URI = '/mgmt/cm/autodeploy/jobs/%s'
    RUNNING_STATE = 'RUNNING'
    FINAL_STATES = ['COMPLETED', 'FAILED']
    EMPTY_JOB = 0
    CREATE_VIRTUAL_DEVICE = 1
    MODIFY_VIRTUAL_DEVICE = 2
    INSTALL_SOFTWARE_IMAGE = 3
    DELETE_VIRTUAL_DEVICE = 4

    def __init__(self, *args, **kwargs):
        super(AutodeployJob, self).__init__(*args, **kwargs)
        self.setdefault('name', '')
        self.setdefault('configReference', Reference())
        self.setdefault('deviceReference', Reference())
        self.setdefault('softwareImageReference', Reference())
        self.setdefault('performFactoryInstall', False)
        self.setdefault('makeInstallVolumeActive', False)
        self.setdefault('makeInstallVolumeDefault', False)
        self.setdefault('installVolumeName', '')
        self.setdefault('state', '')
        self.setdefault('properties', AttrDict())

    @staticmethod
    def run_job(rest, job_id, payload, timeout=30, interval=1):

        def job_completed(uri):
            return rest.get(uri)

        resp = job_completed(AutodeployJob.ITEM_URI % job_id)
        assert resp.state == 'RUNNABLE', 'Job not in Runnable state'

        payload.state = AutodeployJob.RUNNING_STATE
        rest.patch(resp.selfLink, payload=payload)

        wait(lambda: job_completed(resp.selfLink),
             condition=lambda temp: temp.state in AutodeployJob.FINAL_STATES,
             progress_cb=lambda temp: 'Message: {0}, State: {1}' .format(temp.message, temp.state),
             interval=interval, timeout=timeout)


class PhysicalDevice(AutodeployJob):
    def __init__(self, *args, **kwargs):
        super(PhysicalDevice, self).__init__(*args, **kwargs)
        self.setdefault('regKeyReference', Reference())
        self.setdefault('addOnKeys', [])


class VirtualDevice(AutodeployJob):
    def __init__(self, *args, **kwargs):
        super(VirtualDevice, self).__init__(*args, **kwargs)
        self.setdefault('nodeTemplateReference', Reference())
        self.setdefault('revokePoolLicense', False)
        self.setdefault('licensePoolReference', Reference())
        self.setdefault('licenseUnitOfMeasure', '')
        self.setdefault('deleteCloudNode', False)


# Ref- https://peterpan.f5net.com/twiki/bin/view/Cloud/DefaultBootVolumeWorker
class DefaultBootVolume(BaseApiObject):
    URI = '/mgmt/cm/autodeploy/default-boot-volume'

    def __init__(self, *args, **kwargs):
        super(DefaultBootVolume, self).__init__(*args, **kwargs)
        self.setdefault('defaultVolume', '')


# Ref- https://peterpan.f5net.com/twiki/bin/view/Cloud/CMAPIAutodeploySoftwareVolumeInstall
class SoftwareVolumeInstall(BaseApiObject):
    URI = '/mgmt/cm/autodeploy/software-volume-install'

    INITIAL_JOB_STATUS = enum('CREATED', 'STARTED')
    FINAL_JOB_STATUS = ['FINISHED', 'FAILED']
    POST_INSTALL_ACTION = enum('SET_DEFAULT_BOOT_VOLUME',
                               'REBOOT_INTO_VOLUME')

    def __init__(self, *args, **kwargs):
        super(SoftwareVolumeInstall, self).__init__(*args, **kwargs)
        self.setdefault('softwareImageReference', Reference())
        self.setdefault('softwareVolumeName', '')
        self.setdefault('postInstallAction', '')
        self.setdefault('status', SoftwareVolumeInstall.INITIAL_JOB_STATUS.CREATED)

    @staticmethod
    def start_job(rest, uri, timeout=30, interval=1):

        def job_completed(uri):
            return rest.get(uri)

        payload = {}
        payload['status'] = SoftwareVolumeInstall.INITIAL_JOB_STATUS.STARTED
        rest.patch(uri, payload=payload)

        resp = wait(lambda: job_completed(uri),
                condition=lambda temp: temp.status in SoftwareVolumeInstall.FINAL_JOB_STATUS,
                progress_cb=lambda temp: 'Job Status: {0}, Sub-state: {1}, Progress: {2}' .format(temp.status, temp.subState, temp.progress),
                interval=interval, timeout=timeout)

        return resp


class SoftwareStatus(BaseApiObject):
    URI = '/mgmt/tm/cloud/net/software-status'


# Ref - https://confluence.pdsea.f5net.com/pages/viewpage.action?title=UpgradeAdvisorWorker&spaceKey=PDCLOUD
class UpgradeAdvisor(BaseApiObject):
    URI = '/mgmt/cm/autodeploy/upgrades/upgrade-advisor'
    ITEM_URI = 'mgmt/cm/autodeploy/upgrades/upgrade-advisor/%s'

    STATUS = enum('READY_FOR_UPGRADE', 'UPGRADE_IMPOSSIBLE', 'IN_PROGRESS',
                  'UPGRADING', 'FINISHED', 'FAILED', 'INTERNAL_FAILURE')

    def __init__(self, *args, **kwargs):
        super(UpgradeAdvisor, self).__init__(*args, **kwargs)
        self.setdefault('softwareImageReference', Reference())
        self.setdefault('deviceReference', Reference())
        self.setdefault('targetVolumeName', '')
        self.setdefault('adminUser', '')
        self.setdefault('adminPass', '')
        self.setdefault('rootUser', '')
        self.setdefault('rootPass', '')
        self.setdefault('status', '')

    @staticmethod
    def wait_for_ready(rest, uri, timeout=30, interval=1):

        def check_done(uri):
            return rest.get(uri)

        resp = wait(lambda: check_done(uri), condition=lambda temp: temp.status not in [UpgradeAdvisor.STATUS.IN_PROGRESS,
                                                                                        UpgradeAdvisor.STATUS.UPGRADING],
                     progress_cb=lambda temp: 'Status: {0}' .format(temp.status),
                     timeout=timeout, interval=interval)

        return resp


# Ref - https://confluence.pdsea.f5net.com/pages/viewpage.action?title=LegacyLiveInstallWorker&spaceKey=PDCLOUD
class LegacyLiveInstallWorker(BaseApiObject):
    URI = '/mgmt/cm/autodeploy/upgrades/legacy-volume-install'
    ITEM_URI = '/mgmt/cm/autodeploy/upgrades/legacy-volume-install/%s'

    STATUS = enum('INSTALLING', 'COMPLETE', 'FAILED')

    def __init__(self, *args, **kwargs):
        super(LegacyLiveInstallWorker, self).__init__(*args, **kwargs)
        self.setdefault('softwareImageReference', Reference())
        self.setdefault('deviceReference', Reference())
        self.setdefault('softwareVolumeName', '')
        self.setdefault('username', '')
        self.setdefault('password', '')


class Check(BaseApiObject):
    VERSION_CHECK_URI = '/mgmt/cm/autodeploy/upgrades/checks/version'
    ITEM_VERSION_CHECK_URI = '/mgmt/cm/autodeploy/upgrades/checks/version/%s'
    CONNECT_CHECK_URI = '/mgmt/cm/autodeploy/upgrades/checks/connect'
    ITEM_CONNECTOR_CHECK_URI = '/mgmt/cm/autodeploy/upgrades/checks/connect/%s'

    STATUS = enum('UNCHECKED', 'CHECKING', 'CHECK_OK', 'CHECK_FAILED', 'CHECK_NA',
                  'VALIDATING', 'VALIDATE_OK', 'VALIDATE_FAILED', 'VALIDATE_NA')

    @staticmethod
    def wait_for_check(rest, uri, timeout=30, interval=1):

        def check_ready(uri):
            return rest.get(uri)

        wait(lambda: check_ready(uri), condition=lambda temp: temp.status not in [Check.STATUS.UNCHECKED, Check.STATUS.CHECKING, Check.STATUS.VALIDATING],
             progress_cb=lambda temp: '{0} Status: {1}' .format(temp.name, temp.status),
             timeout=timeout, interval=interval)
