'''
Created on Apr 14, 2015

@author: m.ivanitskiy@f5.com
'''

from .....utils.wait import wait
from .base import Reference, Task, TaskError, DEFAULT_TIMEOUT
from f5test.base import AttrDict
import json


class AccessTask(Task):

    def wait(self, rest, resource, loop=None, timeout=DEFAULT_TIMEOUT, interval=1,
             timeout_message=None):
        def get_status():
            resp = rest.api.get(resource.selfLink)
            return resp
        if loop is None:
            loop = get_status
        if rest.version < "bigiq 4.6.0":
            raise TaskError("Task failed: Access supported since bigiq 4.6.0")

        ret = wait(loop, timeout=timeout, interval=interval,
                   timeout_message=timeout_message,
                   condition=lambda x: x.status not in Task.PENDING_STATUSES,
                   progress_cb=lambda x: 'Status: {0}'.format(x.status))
        assert ret.status in Task.FINAL_STATUSES, "{0.status}:{0.error}".format(ret)

        if ret.status == Task.FAIL_STATE:
            msg = json.dumps(ret, sort_keys=True, indent=4, ensure_ascii=False)
            raise TaskError("Task failed.\n%s" % msg)

        return ret


class DeviceManagerTask(AccessTask):
    URI = '/mgmt/cm/access/device-manager'

    def __init__(self, *args, **kwargs):
        super(DeviceManagerTask, self).__init__(*args, **kwargs)
        self.setdefault("devices", AttrDict())
        device = AttrDict()
        device.setdefault('deviceIp')
        device.setdefault('deviceUsername', 'admin')
        device.setdefault('devicePassword', 'admin')
        device.setdefault('automaticallyUpdateFramework', True)
        device.setdefault('rootUser', 'root')
        device.setdefault('rootPassword', 'default')
        self.devices = [device]

    def wait(self, rest, resource, loop=None, timeout=DEFAULT_TIMEOUT, interval=1,
             timeout_message=None):
        ret = super(DeviceManagerTask, self).wait(rest, resource, loop=loop,
                                                  timeout=timeout,
                                                  interval=interval,
                                                  timeout_message=timeout_message)
        msg = "Access Discovery for '%s' failed with error '%s'"
        for device in ret.devices:
            assert not device.errorMessage, msg % (device.deviceIp, device.errorMessage)
        return ret


class RemoveManagementAuthorityTask(AccessTask):
    URI = '/mgmt/cm/access/tasks/remove-management-authority'

    def __init__(self, *args, **kwargs):
        super(RemoveManagementAuthorityTask, self).__init__(*args, **kwargs)
        self.setdefault("deviceOrGroupReference", Reference())
        self.setdefault("unmanage", True)


class DeclareManagementAuthorityTask(AccessTask):
    URI = '/mgmt/cm/access/tasks/declare-mgmt-authority'

    def __init__(self, *args, **kwargs):
        super(DeclareManagementAuthorityTask, self).__init__(*args, **kwargs)
        self.setdefault("deviceReference", Reference())
        self.setdefault('automaticallyUpdateFramework', True)
        self.setdefault('createChildTasks', False)
        self.setdefault('snapshotWorkingConfig', False)
        self.setdefault("deviceGroups", [])


class DeletingAccessGroupTask(AccessTask):
    URI = '/mgmt/cm/access/tasks/mgmt-authority'

    def __init__(self, *args, **kwargs):
        super(DeletingAccessGroupTask, self).__init__(*args, **kwargs)
        self.setdefault("actionType", "RMA_ACCESS_GROUP")
        self.setdefault("groupName")


class CreateAccessGroupTask(AccessTask):
    """Create a new Access Group. Source DevicesReference is required.
    Request includes
    1) groupName
    2) actionType - Type of action to do
    3) sourceDeviceReference - RestReference to the source device: /mgmt/shared/resolver/device-groups/cm-access-allBigIpDevices/devices/xxx
    4) non Source Device References - RestReference to the nonSourceDeviceReferences: List of devices:  /mgmt/shared/resolver/device-groups/cm-access-allBigIpDevices/devices/xxx
    """
    URI = '/mgmt/cm/access/tasks/mgmt-authority'

    def __init__(self, *args, **kwargs):
        super(CreateAccessGroupTask, self).__init__(*args, **kwargs)
        self.setdefault("actionType", "CREATE_ACCESS_GROUP")
        self.setdefault("groupName")
        self.setdefault("sourceDeviceReference", Reference())
        self.setdefault("nonSourceDeviceReferences", [])

    def check_health_status(self, rest, device_refs):

        for item in device_refs:
            uri = device_refs[item] + "/stats"
            payload = rest.api.get(uri)
            self.wait_for_health(rest, payload)

    def wait_for_health(self, rest, payload):
        """waits for a health state of a device"""

        def is_healthy():
            resp = rest.api.get(payload.selfLink)
            value = resp.entries['health.summary.available'].value
            if value == 1.0:
                return True

        ret = wait(is_healthy, timeout=60, interval=5,
                   progress_cb=lambda x: "Device is Not healthy")
        return ret


class EditingDevicesInAccessGroupTask(AccessTask):
    """Edit existing Access Group
    Request includes
    1) groupName - name of access group to be edited
    2) actionType = EDIT_ACCESS_GROUP  Type of action to do
    3) rmaNonSourceDeviceReferences - RestReference to delete devices in the group (List of devices:  /mgmt/shared/resolver/device-groups/cm-access-allBigIpDevices/devices/xxx)
    4) nonSourceDeviceReferences - RestReference to the nonSourceDeviceReferences to be added (List of devices:  /mgmt/shared/resolver/device-groups/cm-access-allBigIpDevices/devices/xxx)
    """
    URI = '/mgmt/cm/access/tasks/mgmt-authority'

    def __init__(self, *args, **kwargs):
        super(EditingDevicesInAccessGroupTask, self).__init__(*args, **kwargs)
        self.setdefault("actionType", "EDIT_ACCESS_GROUP")
        self.setdefault("groupName")
        self.setdefault("rmaNonSourceDeviceReferences", [Reference()])
        self.setdefault("nonSourceDeviceReferences", [Reference()])


class ReimportSourceDeviceInAccessGroupTask(AccessTask):
    """ Re-import Source DEvice in Access Group
    Request includes
    1) groupName
    2) actionType - Type of action to do. In this case its re-import
    3) sourceDeviceReference - RestReference of the source device to do the re-import.
    """
    URI = '/mgmt/cm/access/tasks/mgmt-authority'

    def __init__(self, *args, **kwargs):
        super(ReimportSourceDeviceInAccessGroupTask, self).__init__(*args, **kwargs)
        self.setdefault("actionType", "REIMPORT_SOURCE_DEVICE")
        self.setdefault("groupName")
        self.setdefault("sourceDeviceReference", Reference())


class ChangeSourceDeviceInAccessGroupTask(AccessTask):
    """
    Request includes
    1) groupName
    2) actionType - Type of action to do. In this case its change source
    3) sourceDeviceReference - RestReference of the new source device source device to do the re-import.
    """
    URI = '/mgmt/cm/access/tasks/mgmt-authority'

    def __init__(self, *args, **kwargs):
        super(ChangeSourceDeviceInAccessGroupTask, self).__init__(*args, **kwargs)
        self.setdefault("actionType", "CHANGE_SOURCE_DEVICE")
        self.setdefault("groupName")
        self.setdefault("sourceDeviceReference", Reference())


class DeployConfigurationTask(AccessTask):
    """doc: https://docs.f5net.com/display/PDBIGIQACCESS/Access+Deployment+APIs
    If skipDistribution is false it deploys the configuration to devices.
    if skipDistribution is true, it only evaluates the configuration.
    """
    URI = '/mgmt/cm/access/tasks/deploy-configuration'

    def __init__(self, *args, **kwargs):
        super(DeployConfigurationTask, self).__init__(*args, **kwargs)
        self.setdefault("name", "Deploy-sample-task")
        self.setdefault("description", "Deploy sample task description")
        self.setdefault('deviceGroupReference', Reference())
        self.setdefault("deviceReferences", [])
