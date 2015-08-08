'''
Created on April 3rd, 2015

@author: jinwen.wang
'''

from ...interfaces.rest.emapi.objects import DeviceResolver
from ...interfaces.rest.emapi.objects.shared import DeviceGroup
from ...utils.wait import wait
from .base import IcontrolRestCommand
import logging


LOG = logging.getLogger(__name__)
DEFAULT_CLOUD_GROUP = 'cm-cloud-managed-devices'
DEFAULT_SECURITY_GROUP = 'cm-firewall-allFirewallDevices'
DEFAULT_ASM_GROUP = 'cm-asm-allAsmDevices'
DEFAULT_AUTODEPLOY_GROUP = 'cm-autodeploy-group-manager-autodeployment'
DEFAULT_ALLBIGIQS_GROUP = 'cm-shared-all-big-iqs'
ASM_ALL_GROUP = 'cm-asm-allDevices'
FIREWALL_ALL_GROUP = 'cm-firewall-allDevices'
SECURITY_SHARED_GROUP = 'cm-security-shared-allDevices'
BIG_IP_HA_DEVICE_GROUP = 'tm-shared-all-big-ips'


delete = None
class Delete(IcontrolRestCommand):  # @IgnorePep8
    """Delete a device group, including removing all devices from this group.
    Type: DELETE

    @param group: A dictionary of group as keys and URIs as values
    @rtype: dictionary

    @return: None
    @rtype: None
    """
    def __init__(self, group, *args, **kwargs):
        super(Delete, self).__init__(*args, **kwargs)
        self.group = group

    def remove_all_devices(self):
        LOG.info("Delete all devices in group '%s' ...", self.group['groupName'])
        uri = DeviceGroup.DEVICES_URI % self.group['groupName']
        self.api.delete(uri)

    def remove_group(self):
        LOG.info("Deleting device group '%s' ...", self.group['groupName'])
        uri = DeviceGroup.ITEM_URI % self.group['groupName']
        self.api.delete(uri)

    def delete_completed(self):
        resp = self.api.get(DeviceGroup.URI)
        existing_groups = set([x.selfLink for x in resp['items']])
        group = self.group['selfLink']
        return not existing_groups.__contains__(group)

    def setup(self):
        self.remove_all_devices()
        self.remove_group()

        wait(self.delete_completed, timeout=30,
             progress_cb=lambda x: 'Pending delete...')

        return

delete_by_name = None
class DeleteByName(IcontrolRestCommand):  # @IgnorePep8
    """Delete device group given its group name.
    Type: DELETE

    @param group_name: group name
    @type group_name: string
    """
    def __init__(self, group_name, *args, **kwargs):
        super(DeleteByName, self).__init__(*args, **kwargs)
        self.group_name = group_name
        self.group = None

    def setup(self):
        # Join our devices with theirs by the discover address (self IP)
        group = get_group_by_name(self.group_name)
        if group is not None:
            delete(group)

        return

delete_by_display_name = None
class DeleteByDisplayName(IcontrolRestCommand):  # @IgnorePep8
    """Delete device groups given the display name.
    Type: DELETE

    @param display_name: display name of the device group, not necessarily unique, can contain special char.
    @type display_name: string

    Optional parameters:

    @param deleteonlyone: delete only when there is one and only one group with the given display_name
    @type deleteonlyone: bool, False by default
    """
    def __init__(self, display_name, deleteonlyone=False, *args, **kwargs):
        super(DeleteByDisplayName, self).__init__(*args, **kwargs)
        self.display_name = display_name
        self.deleteonlyone = deleteonlyone
        self.groups = []

    def setup(self):
        # Join our devices with theirs by the discover address (self IP)
        groups = get_groups_by_display_name(self.display_name)
        if not self.deleteonlyone:
            for group in groups:
                delete(group)
        else:
            if len(groups) == 1:
                delete(groups[0])
        return

add_device_group = None
class AddDeviceGroup(IcontrolRestCommand):  # @IgnorePep8
    """Adds a Device Group to a device
    Type: POST

    Optional parameters: (at least one of group_name and display_name not None)
    @param group_name: group name, which should be unique, only letters and numbers
    @type group_name: string

    @param display_name: display name of the device group, not necessarily unique, can contain special char.
    @type display_name: string

    @param parent_link: selfLink of the parent group, None means group will be created under root.
    @type parent_link: string

    @param description: description
    @type description: string

    @return: the created group
    @rtype: attr dict json
    """
    def __init__(self, group_name=None, display_name=None,
                 parent_group=None, description=None,
                 *args, **kwargs):
        super(AddDeviceGroup, self).__init__(*args, **kwargs)
        self.group_name = group_name
        self.display_name = display_name
        self.parent_group = parent_group
        self.description = description

    def setup(self):
        """add a group."""

        if self.group_name is None and self.display_name is None:
            assert "group name and display name can't be both None."

        group = None
        groupresp = self.api.get(DeviceGroup.URI)['items']
        for item in groupresp:
            if item['groupName'] == self.group_name:
                group = item
        if not group:
            LOG.info("Adding Device Group...")

            payload = DeviceGroup()
            payload['groupName'] = self.group_name
            if self.display_name is not None:
                payload['displayName'] = self.display_name
            if self.description is not None:
                payload['description'] = self.description
            if self.parent_group is not None:
                payload['parentLink'] = self.parent_group['selfLink']
            payload['properties'] = {'cm:gui:module': ['device']}
            group = self.api.post(DeviceGroup.URI, payload=payload)
            name = group['groupName']
            LOG.info("group created is '%s'" % name)
        else:
            LOG.info("Device Group already there ({0})...".format(self.group_name))

        DeviceResolver.wait(self.api, group=group['groupName'])
        return group

get_groups_by_display_name = None
class GetGroupsByDisplayName(IcontrolRestCommand):  # @IgnorePep8
    """Get Device Groups by Display Name
    Type: GET

    @param display_name: display name of the device group, not necessarily unique, can contain special char.
    @type display_name: string

    @return: a set of device groups with the given display name
    @rtype: attr dict json[]
    """
    def __init__(self, display_name,
                 *args, **kwargs):
        super(GetGroupsByDisplayName, self).__init__(*args, **kwargs)
        self.display_name = display_name

    def setup(self):
        """get device groups according to display name."""
        groups = [g for g in self.api.get(DeviceGroup.URI)['items'] if g.get('displayName') == self.display_name]
        return groups

get_group_by_name = None
class GetGroupByName(IcontrolRestCommand):  # @IgnorePep8
    """Get Device Groups by Group Name
    Type: GET

    @param group_name: group name
    @type group_name: string

    @return: the api resp or None if there is no such group
    @rtype: attr dict json or None
    """
    def __init__(self, group_name,
                 *args, **kwargs):
        super(GetGroupByName, self).__init__(*args, **kwargs)
        self.group_name = group_name

    def setup(self):
        """get a device group by group name."""

        group = None
        groupsresp = self.api.get(DeviceGroup.URI)['items']

        for item in groupsresp:
            if item['groupName'] == self.group_name:
                group = item
                break

        return group
