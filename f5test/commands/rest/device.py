'''
Created on Jan 30, 2013

@author: jono
'''
from .base import IcontrolRestCommand
from ..base import CommandError
from ...base import Options
from ...utils.wait import wait, wait_args, StopWait
from ...interfaces.rest.emapi.objects import (ManagedDeviceCloud, DeviceResolver,
    DeclareMgmtAuthorityTask, RemoveMgmtAuthorityTask, RemoveMgmtAuthorityTaskV2,
    ManagedDevice)
from ...interfaces.rest.emapi.objects.base import Reference
from ...interfaces.rest.emapi.objects import asm, TaskError
from ...interfaces.rest.emapi import EmapiResourceError
import logging
from netaddr import IPAddress, ipv6_full
import time
import datetime

LOG = logging.getLogger(__name__)
DEFAULT_DISCOVERY_DELAY = 180
VIPRION_DISCOVERY_DELAY = 300
DISCOVERY_TIMEOUT = 180
CLOUD_BACKWARD = 'bigiq 4.3'
DEFAULT_CONFLICT = 'USE_RUNNING'
DEFAULT_CLOUD_GROUP = 'cm-cloud-managed-devices'
DEFAULT_SECURITY_GROUP = 'cm-firewall-allFirewallDevices'
DEFAULT_ASM_GROUP = 'cm-asm-allAsmDevices'
DEFAULT_AUTODEPLOY_GROUP = 'cm-autodeploy-group-manager-autodeployment'
DEFAULT_ALLBIGIQS_GROUP = 'cm-shared-all-big-iqs'


delete = None
class Delete(IcontrolRestCommand):  # @IgnorePep8
    """Delete devices given their selfLink and wait until all devices are gone.

    @param devices: A dictionary of devices as keys and URIs as values
    @rtype: None
    """
    def __init__(self, devices, group=None, *args, **kwargs):
        super(Delete, self).__init__(*args, **kwargs)
        self.devices = list(devices or [])
        self.group = group
        self.uri = None

    def remove_one(self, device, uri):
        LOG.info('Delete started for %s...', device)
        self.api.delete(uri)
        DeviceResolver.wait(self.api, self.group)

    def set_uri(self):
        assert self.group, "A group is required"
        self.uri = DeviceResolver.DEVICES_URI % self.group

    def prep(self):
        super(Delete, self).prep()
        self.set_uri()

    def setup(self):
        if not self.devices:
            return

        # Join our devices with theirs by the discover address (self IP)
        resp = self.api.get(self.uri)
        uris_by_address = dict((IPAddress(x.address), x.selfLink) for x in resp['items'])
        devices = dict((x, uris_by_address.get(IPAddress(x.get_discover_address())))
                       for x in self.devices)

        self.v = self.ifc.version
        for device, uri in devices.items():
            if uri is None:
                raise CommandError('Device %s was not found' % device)
            self.remove_one(device, uri)

        def delete_completed():
            # Changed in 4.1.0
            resp = self.api.get(self.uri)
            theirs = set([x.selfLink for x in resp['items']])
            ours = set(devices.values())
            return not theirs.intersection(ours)

        wait(delete_completed, timeout=30,
             progress_cb=lambda x: 'Pending delete...')


discover = None
class Discover(IcontrolRestCommand):  # @IgnorePep8
    """Makes sure all devices are "identified" in a certain group by the
    DeviceResolver.

    @param devices: A list of f5test.interfaces.config.DeviceAccess instances.
    @param refresh: A bool flag, if set it will re-discover existing devices.
    @rtype: None
    """

    def __init__(self, devices, group=None, refresh=False,
                 timeout=DISCOVERY_TIMEOUT, options={},
                 *args, **kwargs):
        super(Discover, self).__init__(*args, **kwargs)
        self.devices = list(devices)
        self.refresh = refresh
        self.group = group
        self.uri = None
        self.timeout = timeout
        self.options = options

    def add_one(self, device):
        LOG.info('Adding device %s to %s...', device, self.group)
        payload = DeviceResolver()
        payload.address = device.get_discover_address()
        payload.userName = device.get_admin_creds().username
        payload.password = device.get_admin_creds().password
        payload.rootUser = device.get_root_creds().username
        payload.rootPassword = device.get_root_creds().password
        payload.automaticallyUpdateFramework = True
        payload.update(self.options)

        resp = self.api.post(self.uri, payload=payload)
        return wait_args(self.api.get, func_args=[resp.selfLink],
                         condition=lambda x: x.state not in DeviceResolver.PENDING_STATES,
                         progress_cb=lambda x: 'Discovery pending...',
                         timeout=self.timeout,
                         timeout_message="Discovery task did not complete in {0} seconds")

    def refresh_one(self, device, state):
        LOG.info('Refreshing device %s in %s...', device, self.group)
        payload = DeviceResolver()
        payload.address = device.get_discover_address()
        payload.userName = device.get_admin_creds().username
        payload.password = device.get_admin_creds().password
        payload.rootUser = device.get_root_creds().username
        payload.rootPassword = device.get_root_creds().password
        payload.automaticallyUpdateFramework = True
        payload.update(self.options)

        resp = self.api.patch(state.selfLink, payload=payload)
        return wait_args(self.api.get, func_args=[resp.selfLink],
                         condition=lambda x: x.state not in DeviceResolver.PENDING_STATES,
                         progress_cb=lambda x: 'Refresh pending...',
                         timeout=self.timeout,
                         timeout_message="Refresh task did not complete in {0} seconds")

    def set_uri(self):
        assert self.group, "A group is required"
        self.uri = DeviceResolver.DEVICES_URI % self.group

    def prep(self):
        super(Discover, self).prep()
        self.set_uri()

        LOG.info('Waiting for REST framework to come up...')

        # An authz error indicates a user error and most likely we won't find
        # the framework to be up that way.
        def is_up(*args):
            try:
                return self.api.get(*args)
            except EmapiResourceError, e:
                if 'Authorization failed' in e.msg:
                    raise StopWait(e)
        self.resp = wait_args(is_up, func_args=[self.uri])

    def completed(self, device, ret):
        assert ret.state in ['ACTIVE'], \
               'Discovery of {0} failed: {1}:{2}'.format(device, ret.state,
                                                         ret.errors)

    def setup(self):
        # Make mapping of what's on the server and what's in our config
        resp = self.resp
        theirs = dict([(IPAddress(x.address), x) for x in resp['items']])
        ours = dict([(IPAddress(x.get_discover_address()), x) for x in self.devices])

        for address in set(theirs) - set(ours):
            theirs.pop(address)

        theirs_set = set() if self.refresh else set([x for x in theirs
                                                     if theirs[x].state == 'ACTIVE'])

        # Add any devices that are not already discovered.
        # Discovery of multiple devices at once is not supported by API.
        discovered_count = 0
        for address in set(ours) - theirs_set:
            device = ours[address]

            delay = VIPRION_DISCOVERY_DELAY \
                if device.specs.get('is_cluster', False) \
                else DEFAULT_DISCOVERY_DELAY

            if device.specs.configure_done:
                diff = datetime.datetime.now() - device.specs.configure_done
                if diff < datetime.timedelta(seconds=delay) \
                   and device.get_discover_address() != device.get_address():
                    delay -= diff.seconds
                    LOG.info('XXX: Waiting %d seconds for tmm to come up...' % delay)
                    time.sleep(delay)

            if address in theirs and (self.refresh or theirs[address].state not in ['UNDISCOVERED']):
                ret = self.refresh_one(device, theirs[address])
            else:
                ret = self.add_one(device)
                self.completed(device, ret)
            discovered_count += 1

        # Map our devices to their selfLinks
        resp = self.api.get(self.uri) if discovered_count else self.resp
        theirs = dict([(IPAddress(x.address), x) for x in resp['items']])
        return dict((x, theirs[IPAddress(x.get_discover_address())].selfLink) for x in self.devices)


delete_security = None
class DeleteSecurity(Delete):  # @IgnorePep8
    """Delete devices given their selfLink and wait until all devices are gone.

    @param devices: A dictionary of devices as keys and URIs as values
    @rtype: None
    """
    group = DEFAULT_SECURITY_GROUP
    task = RemoveMgmtAuthorityTaskV2

    def __init__(self, *args, **kwargs):
        super(DeleteSecurity, self).__init__(*args, **kwargs)
        self.group = self.__class__.group

    def set_uri(self):
        if self.ifc.version < 'bigiq 4.1':
            self.uri = ManagedDevice.URI
        else:
            assert self.group, "A group is required starting with 4.1"
            self.uri = DeviceResolver.DEVICES_URI % self.group

    def remove_one(self, device, uri):
        LOG.info('RMA started for %s...', device)
        if self.v < 'bigiq 4.1':
            rma = RemoveMgmtAuthorityTask()
            rma.deviceLink = uri
            task = self.api.post(RemoveMgmtAuthorityTask.URI, payload=rma)
        else:
            rma = self.task()
            rma.deviceReference.link = uri
            task = self.api.post(self.task.URI, payload=rma)
        return rma.wait(self.api, task)


discover_security = None
class DiscoverSecurity(Discover):  # @IgnorePep8
    """Makes sure all devices are discovered.

    @param devices: A list of f5test.interfaces.config.DeviceAccess instances.
    @param refresh: A bool flag, if set it will re-discover existing devices.
    @rtype: None
    """
    group = DEFAULT_SECURITY_GROUP
    task = DeclareMgmtAuthorityTask

    def __init__(self, *args, **kwargs):
        super(DiscoverSecurity, self).__init__(*args, **kwargs)
        self.group = self.__class__.group

    def set_uri(self):
        if self.ifc.version < 'bigiq 4.1':
            self.uri = ManagedDevice.URI
        else:
            # Changed in 4.1.0
            assert self.group, "A group is required starting with 4.1"
            self.uri = DeviceResolver.DEVICES_URI % self.group

    def add_one(self, device):
        LOG.info('Declare Management Authority for %s...', device)
        subtask = Options()
        subtask.deviceIp = device.get_discover_address()
        subtask.deviceUsername = device.get_admin_creds().username
        subtask.devicePassword = device.get_admin_creds().password
        subtask.rootUser = device.get_root_creds().username
        subtask.rootPassword = device.get_root_creds().password
        subtask.snapshotWorkingConfig = True
        subtask.automaticallyUpdateFramework = True
        subtask.clusterName = ''
        subtask.update(self.options)
        dma = self.task()
        dma.subtasks.append(subtask)

        task = self.api.post(self.task.URI, payload=dma)

        def custom_loop():
            resp = self.api.get(task.selfLink)
            if resp.subtasks[0].status == 'PENDING_CONFLICTS':
                LOG.info('Conflicts detected, setting resolution: %s' % DEFAULT_CONFLICT)
                for conflict in resp.subtasks[0].conflicts:
                    conflict.resolution = DEFAULT_CONFLICT
                resp = self.api.patch(task.selfLink, payload=resp)
            return resp

        return dma.wait(self.api, task, loop=custom_loop, timeout=self.timeout,
                        timeout_message="Security DMA task did not complete in {0} seconds")

    def completed(self, device, ret):
        state = ret.subtasks[0].status
        assert state in ['COMPLETE'], \
               'Discovery of {0} failed: {1}'.format(device, state)

delete_cloud = None
class DeleteCloud(Delete):  # @IgnorePep8
    """Delete devices given their selfLink and wait until all devices are gone.

    @param devices: A dictionary of devices as keys and URIs as values
    @rtype: None
    """
    def __init__(self, *args, **kwargs):
        super(DeleteCloud, self).__init__(*args, **kwargs)
        self.group = DEFAULT_CLOUD_GROUP

    def set_uri(self):
        self.uri = ManagedDeviceCloud.URI

    def remove_one(self, device, uri):
        LOG.info('Delete started for %s...', device)
        return self.api.delete(uri)


discover_cloud = None
class DiscoverCloud(Discover):  # @IgnorePep8
    """Makes sure all devices are discovered.

    @param devices: A list of f5test.interfaces.config.DeviceAccess instances.
    @param refresh: A bool flag, if set it will re-discover existing devices.
    @rtype: None
    """

    def __init__(self, *args, **kwargs):
        super(DiscoverCloud, self).__init__(*args, **kwargs)
        self.group = DEFAULT_CLOUD_GROUP

    def set_uri(self):
        if self.ifc.version < CLOUD_BACKWARD:
            self.uri = ManagedDeviceCloud.URI
        else:
            # Changed in 4.3.0
            assert self.group, "A group is required starting with 4.3"
            self.uri = DeviceResolver.DEVICES_URI % self.group

    def add_one(self, device):
        LOG.info('Cloud discovery for %s...', device)
        if self.ifc.version < CLOUD_BACKWARD:
            payload = ManagedDeviceCloud()
            payload.deviceAddress = device.get_discover_address()
        else:
            payload = Options()
            payload.address = device.get_discover_address()

        payload.userName = device.get_admin_creds().username
        payload.password = device.get_admin_creds().password
        payload.rootUser = device.get_root_creds().username
        payload.rootPassword = device.get_root_creds().password
        payload.automaticallyUpdateFramework = True
        payload.update(self.options)
        resp = self.api.post(self.uri, payload=payload)

        return wait_args(self.api.get, func_args=[resp.selfLink],
                         condition=lambda x: x.state not in ManagedDeviceCloud.PENDING_STATES,
                         progress_cb=lambda x: 'Discovery pending...',
                         timeout=self.timeout,
                         timeout_message="Cloud discovery task did not complete in {0} seconds")


delete_asm = None
class DeleteAsm(DeleteSecurity):  # @IgnorePep8
    group = DEFAULT_ASM_GROUP
    task = asm.RemoveMgmtAuthority


discover_asm = None
class DiscoverAsm(DiscoverSecurity):  # @IgnorePep8
    group = DEFAULT_ASM_GROUP
    task = asm.DeclareMgmtAuthority

    def add_one(self, device):
        LOG.info('Declare Management Authority for %s...', device)
        dma = self.task()
        dma.deviceAddress = device.get_discover_address()
        dma.username = device.get_admin_creds().username
        dma.password = device.get_admin_creds().password
        dma.rootUser = device.get_root_creds().username
        dma.rootPassword = device.get_root_creds().password
        dma.automaticallyUpdateFramework = True
        # Unable to get version through rest interface before discovery...
        # discoverSharedSecurity Feature - Firestone and above only BZ474503
        if self.context.get_icontrol(device=device).version < 'bigip 11.5.1 4.0.128' or\
           self.ifc.version < 'bigiq 4.5':
            dma.discoverSharedSecurity = False
        else:
            dma.discoverSharedSecurity = True
        dma.update(self.options)

        task = self.api.post(self.task.URI, payload=dma)

        return dma.wait(self.api, task, timeout=self.timeout, interval=5,
                        timeout_message="ASM DMA task did not complete in {0} seconds. Last status: {1.overallStatus}")

    def completed(self, device, ret):
        assert ret.status in ['COMPLETED'], \
               'Discovery of {0} failed: {1}:{2}'.format(device, ret.status,
                                                         ret.error)

clean_dg_certs = None
class CleanDgCerts(IcontrolRestCommand):  # @IgnorePep8
    """Resets the certs on the default BIG-IQ because of BZ472991.

    Original author: John Wong

    @param biq: BIGIQ
    @type biq: Device
    @param bip: List of devices
    @type bip: List
    @param group: Device Group of what should be returned.
    @type group: string

    @return: Dictionary from Discovery class
    """
    DEFAULT_AUTODEPLOY = 'cm-autodeploy-group-manager-autodeployment'
    DEVICE_GROUPS = [DEFAULT_CLOUD_GROUP, DEFAULT_SECURITY_GROUP,
                     DEFAULT_ALLBIGIQS_GROUP, DEFAULT_ASM_GROUP, DEFAULT_AUTODEPLOY,
                     'cm-firewall-allDevices', 'cm-asm-allAsmLoggingNodes',
                     'cm-asm-allDevices', 'cm-asm-logging-nodes-trust-group',
                     'cm-autodeploy-group-manager-autodeployment',
                     'cm-security-shared-allDevices',
                     'cm-security-shared-allSharedDevices']

    def __init__(self, bips, group=None, *args, **kwargs):
        super(CleanDgCerts, self).__init__(*args, **kwargs)
        self.bips = bips
        self.group = group

    def setup(self):
        is_deleted_from = {x: False for x in CleanDgCerts.DEVICE_GROUPS}
        api = self.ifc.api
        resp = api.get(DeviceResolver.URI)
        device_groups = [x.groupName for x in resp['items']]
        default_full = IPAddress(self.ifc.device.get_discover_address()).format(ipv6_full)

        # Remove bigips from harness
        for device_group in device_groups:
            bigips = []
            resp = api.get(DeviceResolver.DEVICES_URI % device_group)
            for device in resp['items']:
                bigips.extend([x for x in self.bips if device.address == x.get_discover_address()])

            if device_group == DEFAULT_ASM_GROUP and bigips:
                LOG.info("Deleting {0} from {1}".format(bigips, device_group))
                DeleteAsm(bigips).run()
                is_deleted_from[device_group] = True

            elif device_group == DEFAULT_SECURITY_GROUP and bigips:
                LOG.info("Deleting {0} from {1}".format(bigips, device_group))
                DeleteSecurity(bigips).run()
                is_deleted_from[device_group] = True

            elif device_group == DEFAULT_CLOUD_GROUP and bigips:
                LOG.info("Deleting {0} from {1}".format(bigips, device_group))
                DeleteCloud(bigips).run()
                is_deleted_from[device_group] = True

            elif device_group == CleanDgCerts.DEFAULT_AUTODEPLOY and bigips:
                LOG.info("Deleting {0} from {1}".format(bigips, device_group))
                Delete(bigips, group=CleanDgCerts.DEFAULT_AUTODEPLOY).run()
                is_deleted_from[device_group] = True

        # Remove other devices that are not localhost
        for device_group in device_groups:
            resp = api.get(DeviceResolver.DEVICES_URI % device_group)
            for device in resp['items']:
                # not including UNDISCOVERED devices as it might be from EC2.
                if device.address != default_full and device.state != 'UNDISCOVERED':
                    LOG.info("Deleting {0} from {1}".format(device.address, device_group))
                    api.delete(device.selfLink)
                    is_deleted_from[device_group] = True if device.product == 'BIG-IP' else False
                elif not device_group in CleanDgCerts.DEVICE_GROUPS:
                    LOG.info("Deleting {0} from {1}".format(device.address, device_group))
                    api.delete(device.selfLink)
            DeviceResolver.wait(api, device_group)

            # Remove device groups that aren't the default ones
            if not device_group in CleanDgCerts.DEVICE_GROUPS:
                LOG.info("Deleting unknown device group: {0}".format(device_group))
                api.delete(DeviceResolver.ITEM_URI % device_group)

        ret = None
        if self.group == DEFAULT_ASM_GROUP:
            ret = DiscoverAsm(self.bips).run()
        elif self.group == DEFAULT_CLOUD_GROUP:
            ret = DiscoverCloud(self.bips).run()
        elif self.group == CleanDgCerts.DEFAULT_AUTODEPLOY:
            ret = Discover(self.bips, group=CleanDgCerts.DEFAULT_AUTODEPLOY).run()
        elif self.group == DEFAULT_SECURITY_GROUP:
            ret = DiscoverSecurity(self.bips).run()

        if is_deleted_from[DEFAULT_ASM_GROUP] and self.group != DEFAULT_ASM_GROUP:
            DiscoverAsm(self.bips).run()
        if is_deleted_from[DEFAULT_CLOUD_GROUP] and self.group != DEFAULT_CLOUD_GROUP:
            DiscoverCloud(self.bips).run()
        if is_deleted_from[CleanDgCerts.DEFAULT_AUTODEPLOY] and self.group != CleanDgCerts.DEFAULT_AUTODEPLOY:
            Discover(self.bips, group=CleanDgCerts.DEFAULT_AUTODEPLOY).run()
        if is_deleted_from[DEFAULT_SECURITY_GROUP] and self.group != DEFAULT_SECURITY_GROUP:
            DiscoverSecurity(self.bips).run()

        return ret
