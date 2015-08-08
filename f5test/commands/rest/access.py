'''
Created on Apr 29, 2015

@author: ivanitskiy
'''

from .base import IcontrolRestCommand
from ...base import AttrDict
from ...interfaces.rest.emapi.objects import access
from ...interfaces.rest.emapi.objects.shared import DeviceResolver
from ...commands.rest.device import DEFAULT_ACCESS_GROUP
from .device_group import GetGroupByName
import logging
from f5test.interfaces.rest.emapi.objects.base import TaskError


LOG = logging.getLogger(__name__)
DEFAULT_TIMEOUT = 60 * 9

create_access_group = None
class CreateAccessGroup(IcontrolRestCommand):  # @IgnorePep8
    """
    Type: POST
    @param group_name: group name, which should be unique, only letters and numbers
    @type group_name: string

    @param devices: devices to add into group
    @type list: list of instances of f5test.interfaces.config.DeviceAccess

    @param source_device: device that is source
    @type instance of f5test.interfaces.config.DeviceAccess

    @return: the task status
    @rtype: attr dict json
    """
    task = access.CreateAccessGroupTask

    def __init__(self, group_name, devices, source_device,
                 *args, **kwargs):
        super(CreateAccessGroup, self).__init__(*args, **kwargs)
        self.group_name = group_name
        self.devices = devices
        self.source_device = source_device
        self.task_self_link = None

    def setup(self):
        """Add a device to access group"""
        uri = DeviceResolver.DEVICES_URI % DEFAULT_ACCESS_GROUP
        rest_devices = self.api.get(uri)
        device_references = AttrDict()
        for device in self.devices:
            device_address = device.get_address()
            retst_resp = None
            for x in rest_devices["items"]:
                if x.managementAddress == device_address:
                    retst_resp = x
                    break
            if retst_resp is not None:
                device_references[device] = retst_resp.selfLink
        source_ref = device_references[self.source_device]
        dma = self.task()
        # let's check the stats of the devices
        # Task will fail, if devices are not healthy
        # BZ 514242 and  https://docs.f5net.com/display/PDBIGIQACCESS/BIG-IQ+Device+Health+Stats
        dma.check_health_status(self.ifc, device_references)

        device_references.pop(self.source_device)
        dma.groupName = self.group_name
        dma.sourceDeviceReference.link = source_ref
        for item in device_references:
            dma.nonSourceDeviceReferences.append({"link": device_references[item]})
        uri = access.CreateAccessGroupTask.URI
        LOG.info("Creating access group '{0}' with source: '{1} and non-source:'{2}'".format(self.group_name, source_ref, device_references))

        task = self.api.post(uri, payload=dma)
        self.task_self_link = task.selfLink
        return dma.wait(self.ifc, task, timeout=DEFAULT_TIMEOUT,
                        timeout_message="Access 'declare-mgmt-authority' task did not complete in {0} seconds")

    def revert(self):
        # if access group failed we need to cancel the task
        resp = self.api.get(self.task_self_link)
        if resp.status == "FAILED":
            LOG.debug("Status is FAILED, nothing to rever")
        else:
            LOG.info("Task '%s' did not compete. It's needed to cancel the task" % self.task_self_link)
            self.api.patch(self.task_self_link, {"status": "CANCELED"})
            if get_access_group_by_name(self.group_name) is not None:
                LOG.info("Group creation failed. It's needed to remove access group %s " % self.group_name)
                delete_access_group_by_name(self.group_name)

change_source_device_in_access_group = None
class ChangeSourceDeviceInAccessGroup(IcontrolRestCommand):  # @IgnorePep8
    """
    Type: POST, PATCH
    @param group_name: group name, which should be unique, only letters and numbers
    @type group_name: string

    @param source_device: a new source device (member of that group)
    @type instance of f5test.interfaces.config.DeviceAccess

    @return: the task status
    @rtype: attr dict json
    """
    task = access.ChangeSourceDeviceInAccessGroupTask

    def __init__(self, group_name, devices, source_device,
                 *args, **kwargs):
        super(ChangeSourceDeviceInAccessGroup, self).__init__(*args, **kwargs)
        self.group_name = group_name
        self.source_device = source_device
        self.task_self_link = None

    def setup(self):
        pass

reimport_source_device_in_access_group = None
class ReimportSourceDeviceInAccessGroup(IcontrolRestCommand):  # @IgnorePep8
    """
    Type: POST, PATCH
    @param group_name: group name, which should be unique, only letters and numbers
    @type group_name: string

    @return: the task status
    @rtype: attr dict json
    """
    task = access.ReimportSourceDeviceInAccessGroupTask

    def resolve_conflicts(self, resp):
        result = resp
        if resp.currentStep == "PENDING_CONFLICTS" and resp.status == "FINISHED":
            LOG.info("The re-import task requires resolving conflicts...")
            mgmt_summary_resp = self.api.get(resp.mgmtAuthoritySummaryReference.link)
            dma_task_ref_link = None
            for item in mgmt_summary_resp.devices:
                if item.dmaTaskReference is not None and item.currentStep == "PENDING_CONFLICTS":
                    dma_task_ref_link = item.dmaTaskReference.link
                    break

            if dma_task_ref_link is not None:
                payload = AttrDict()
                payload.dmaTaskReference = item.dmaTaskReference
                payload.status = "STARTED"
                payload.acceptConflicts = True

                task = self.api.patch(resp.selfLink, payload=payload)
                reimport_task = self.task()
                patched_task = reimport_task.wait(self.ifc, task, timeout=DEFAULT_TIMEOUT,
                                                  timeout_message="Task: 'mgmt-authority'; actionType: REIMPORT_SOURCE_DEVICE did not complete in {0} seconds")
                result = self.resolve_conflicts(patched_task)

            else:
                raise TaskError("Could not find dmaTaskReference in response\n%s" % resp)
        elif resp.currentStep == "COMPLETE" and resp.status == "FINISHED":
            LOG.info("Conflicts were resolved. re-import task completed.")
            return result
        else:
            LOG.debug("Current response for mgmt-authority task:\n %s" % resp)
            raise TaskError("Could not determine state of the task...")

    def __init__(self, group_name,
                 *args, **kwargs):
        super(ReimportSourceDeviceInAccessGroup, self).__init__(*args, **kwargs)
        self.group_name = group_name
        self.task_self_link = None

    def setup(self):
        # Get source device uuid
        uri = DeviceResolver.DEVICES_URI % self.group_name
        odata_dict = AttrDict(filter="'properties/cm:access:source-device' eq 'true'")
        rest_access_config = self.api.get(uri, odata_dict=odata_dict)
        source_ref = "https://localhost" + DeviceResolver.DEVICE_URI % (DEFAULT_ACCESS_GROUP, rest_access_config["items"][0].uuid)
        reimport_task = self.task()
        reimport_task.groupName = self.group_name
        reimport_task.sourceDeviceReference.link = source_ref
        LOG.info("Re-importing source device for access group '{0}'".format(self.group_name))
        task = self.api.post(reimport_task.URI, payload=reimport_task)
        resp = reimport_task.wait(self.ifc, task, timeout=DEFAULT_TIMEOUT,
                                  timeout_message="Task: 'mgmt-authority'; actionType: REIMPORT_SOURCE_DEVICE did not complete in {0} seconds")
        result = self.resolve_conflicts(resp)
        return result

get_access_groups = None
class GetAccessGroups(IcontrolRestCommand):  # @IgnorePep8
    pass


get_access_group_by_name = None
class GetAccessGroupByName(GetGroupByName):  # @IgnorePep8
    pass


delete_by_display_name = None
class DeleteByDisplayName(IcontrolRestCommand):  # @IgnorePep8
    pass

delete_access_group_by_name = None
class DeleteAccessGroupByName(IcontrolRestCommand):  # @IgnorePep8

    task = access.DeletingAccessGroupTask

    def __init__(self, group_name=None, *args, **kwargs):
        super(DeleteAccessGroupByName, self).__init__(*args, **kwargs)
        self.group_name = group_name

    def setup(self):
        """Rest API to delete Access Group"""
        group = get_access_group_by_name(self.group_name)
        if group is not None:
            rma = self.task()
            rma.groupName = self.group_name
            LOG.info("Removing access group '%s'" % self.group_name)
            task = self.api.post(rma.URI, payload=rma)
            return rma.wait(self.ifc, task, timeout=DEFAULT_TIMEOUT,
                            timeout_message="Access delete access group ('mgmt-authority' task) did not complete in {0} seconds")


delete_all_access_groups = None
class DeleteAllAccessGroups(IcontrolRestCommand):  # @IgnorePep8

    def setup(self):
        """Rest API command to delete All Access Groups"""
        uri = DeviceResolver.URI
        odata_dict = AttrDict(expand="devicesReference", filter="'properties/cm:access:config_group' eq 'true'")
        rest_access_config = self.api.get(uri, odata_dict=odata_dict)
        LOG.debug("Deleting already created access groups")
        for x in rest_access_config["items"]:
            group_name = x.groupName
            delete_access_group_by_name(group_name=group_name)


create_access_config_deployment = None
class CreateAccessConfigDeployment(IcontrolRestCommand):  # @IgnorePep8
    """Creates a new deployment
    Type: POST
    Doc: https://docs.f5net.com/display/PDBIGIQACCESS/Access+Deployment+APIs

    @param group_name: group name, which should be unique, only letters and numbers
    @type group_name: string

    @param devices: list devices to deploy to
    @type list: list of instances of f5test.interfaces.config.DeviceAccess

    @param options: deployment options
    @type AttrDict
            if options is None, then it will use default one:

            options.skipDistribution = False or True
                - False it deploys the configuration to devices.
                - True, it only evaluates the configuration.
            options.skipVerifyConfig = False or True
                -
                -
            options.properties = AttrDict()
            options.properties["cm:access:post-deploy-config:apply-policies"] = True or False
                - if below property is set to true then policies will be applied
                  after successfully deploying. If no properties are specified
                  default behavior is policies will be applied. If property value
                  is set to false policies will not be applied.

            options.properties["cm:access:post-deploy-config:kill-sessions"] = False

    @return: the task status
    @rtype: attr dict json
    """
    task = access.DeployConfigurationTask

    def __init__(self, group_name, devices, options=AttrDict(), *args, **kwargs):
        super(CreateAccessConfigDeployment, self).__init__(*args, **kwargs)
        self.group_name = group_name
        self.devices = devices
        self.options = AttrDict()
        if not options:
            options = AttrDict()
            options.skipDistribution = True
            options.skipVerifyConfig = True
            options.properties = AttrDict()
            options.properties["cm:access:post-deploy-config:apply-policies"] = True
            options.properties["cm:access:post-deploy-config:kill-sessions"] = False
        self.options.update(options)

    def setup(self):
        """add a device to access group"""
        group = get_access_group_by_name(self.group_name)
        rest_devices = self.api.get(DeviceResolver.DEVICES_URI % DEFAULT_ACCESS_GROUP)
        device_references = []
        for device in self.devices:
            device_address = device.get_address()
            retst_resp = None
            for x in rest_devices["items"]:
                if x.managementAddress == device_address:
                    retst_resp = x
                    break
            if retst_resp is not None:
                device_references.append({"link": retst_resp.selfLink})

        deployment = self.task()
        deployment.deviceGroupReference.link = group.selfLink
        deployment.deviceReferences = device_references
        deployment.update(self.options)
        LOG.info("Creating a new Access deployment '%s'..." % deployment.name)
        task = self.api.post(self.task.URI, payload=deployment)
        self.task_self_link = task.selfLink
        return deployment.wait(self.ifc, task, timeout=DEFAULT_TIMEOUT,
                               timeout_message="Access 'deploy-configuration' task did not complete in {0} seconds")
