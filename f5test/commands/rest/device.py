'''
Created on Jan 30, 2013

@author: jono
'''
import datetime
import logging
import time

from netaddr import IPAddress, ipv6_full

from ...base import Options
from ...interfaces.rest.emapi import EmapiResourceError
from ...interfaces.rest.emapi.objects import (ManagedDeviceCloud, DeviceResolver,
                                              DeclareMgmtAuthorityTask,
                                              RemoveMgmtAuthorityTask,
                                              RemoveMgmtAuthorityTaskV2,
                                              ManagedDevice)
from ...interfaces.rest.emapi.objects.adc import RefreshCurrentConfig
from ...interfaces.rest.emapi.objects.firewall import SecurityTaskV2
from ...interfaces.rest.emapi.objects import asm
from ...interfaces.rest.emapi.objects import access
from ...interfaces.rest.emapi.objects.shared import DeviceGroup
from ...utils.wait import wait, wait_args, StopWait
from ..base import CommandError
from .base import IcontrolRestCommand


LOG = logging.getLogger(__name__)
DEFAULT_DISCOVERY_DELAY = 180
VIPRION_DISCOVERY_DELAY = 300
DISCOVERY_TIMEOUT = 600
ACCESS_DISCOVERY_TIMEOUT = 600
ACCESS_DELETE_TIMEOUT = 65
CLOUD_BACKWARD = 'bigiq 4.3'
DEFAULT_CONFLICT = 'USE_RUNNING'
DEFAULT_CLOUD_GROUP = 'cm-cloud-managed-devices'
DEFAULT_SECURITY_GROUP = 'cm-firewall-allFirewallDevices'
DEFAULT_ASM_GROUP = 'cm-asm-allAsmDevices'
DEFAULT_AUTODEPLOY_GROUP = 'cm-autodeploy-group-manager-autodeployment'
DEFAULT_ALLBIGIQS_GROUP = 'cm-shared-all-big-iqs'
ASM_ALL_GROUP = 'cm-asm-allDevices'
FIREWALL_ALL_GROUP = 'cm-firewall-allDevices'
SECURITY_SHARED_GROUP = 'cm-security-shared-allDevices'
BIG_IP_HA_DEVICE_GROUP = 'tm-shared-all-big-ips'
DEFAULT_ACCESS_GROUP = 'cm-access-allBigIpDevices'

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
        uris_by_address = dict((IPAddress(x.managementAddress), x.selfLink) for x in resp['items'])
        devices = dict((x, uris_by_address.get(IPAddress(x.get_address())))
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

    def wait_for_availability(self, resource, timeout):
        stats_link = resource.selfLink + '/stats'
        return wait_args(self.api.get, func_args=[stats_link],
                         condition=lambda x: x.entries.get('health.summary.available', {}).get('value') == 1,
                         progress_cb=lambda x: 'Pending health check...',
                         timeout=timeout,
                         timeout_message="Object %s not available after {0} seconds" % resource.selfLink)

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
        resp = wait_args(self.api.get, func_args=[resp.selfLink],
                         condition=lambda x: x.state not in DeviceResolver.PENDING_STATES,
                         progress_cb=lambda x: 'Discovery pending...',
                         timeout=self.timeout,
                         timeout_message="Discovery task did not complete in {0} seconds")
        if self.v >= 'bigiq 4.5':
            self.wait_for_availability(resp, self.timeout)
        return resp

    def refresh_one(self, device, state):
        LOG.info('Refreshing device %s in %s...', device, self.group)
        payload = DeviceResolver()
        payload.address = device.get_discover_address()
        payload.userName = device.get_admin_creds().username
        payload.password = device.get_admin_creds().password
        payload.rootUser = device.get_root_creds().username
        payload.rootPassword = device.get_root_creds().password
        payload.automaticallyUpdateFramework = True
        payload.state = 'ACTIVE'
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
                raise
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
        self.v = self.ifc.version

        # Add any devices that are not already discovered.
        # Discovery of multiple devices at once is not supported by API.
        for address in set(ours) - theirs_set:
            device = ours[address]

            delay = VIPRION_DISCOVERY_DELAY \
                if device.specs.get('is_cluster', False) \
                else DEFAULT_DISCOVERY_DELAY

            if device.specs.has_tmm_restarted:
                diff = datetime.datetime.now() - device.specs.has_tmm_restarted
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

        return self.post_discovery_steps()

    def post_discovery_steps(self):
        # Map our devices to their selfLinks
        resp = self.api.get(self.uri)
        theirs = dict([(IPAddress(x.address), x) for x in resp['items']])
        return dict((x, theirs[IPAddress(x.get_discover_address())]) for x in self.devices)


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

        if self.v >= 'bigiq 4.5':
            rma = SecurityTaskV2()
            return rma.wait(self.ifc, task)
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
        if self.ifc.version >= 'bigiq 4.5':
            LOG.info('Declare Management Authority for %s...', device)
            dma = SecurityTaskV2()
            dma.deviceIp = device.get_discover_address()
            dma.deviceUsername = device.get_admin_creds().username
            dma.devicePassword = device.get_admin_creds().password
            dma.rootUser = device.get_root_creds().username
            dma.rootPassword = device.get_root_creds().password
            dma.snapshotWorkingConfig = True
            dma.automaticallyUpdateFramework = True
            dma.createChildTasks = True

            task = self.api.post(self.task.URI, payload=dma)

            return dma.wait(self.ifc, task, timeout=self.timeout,
                            timeout_message="Security DMA task did not complete in {0} seconds")
        else:
            return self.add_one_legacy(device)

    def add_one_legacy(self, device):
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
        if self.ifc.version >= 'bigiq 4.5':
            state = ret.status
            assert state == 'FINISHED', \
                'Discovery of {0} failed: {1}'.format(device, state)
        else:
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
        if self.ifc.version >= "bigiq 4.5.0":
            super(DeleteCloud, self).set_uri()
        else:
            LOG.debug("Using old URI...")
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

    def remove_one(self, device, uri):
        LOG.info('RMA started for %s...', device)
        if self.v < 'bigiq 4.1':
            rma = RemoveMgmtAuthorityTask()
            rma.deviceLink = uri
            task = self.api.post(RemoveMgmtAuthorityTask.URI, payload=rma)
            return rma.wait(self.api, task)
        elif self.v < 'bigiq 4.5':
            rma = self.task()
            rma.deviceReference.link = uri
            task = self.api.post(self.task.URI, payload=rma)
            return rma.wait(self.api, task)
        else:
            rma = self.task()
            rma.deviceReference.link = uri
            task = self.api.post(self.task.URI, payload=rma)
            return rma.wait_status(self.api, task)


discover_asm = None
class DiscoverAsm(DiscoverSecurity):  # @IgnorePep8
    group = DEFAULT_ASM_GROUP
    task = asm.DeclareMgmtAuthority

    def add_one(self, device):
        LOG.info('Declare Management Authority for %s...', device)
        if self.ifc.version < 'bigiq 4.5':
            dma = self.task()
            dma.deviceAddress = device.get_discover_address()
            dma.username = device.get_admin_creds().username
            dma.password = device.get_admin_creds().password
        else:
            dma = asm.DeclareMgmtAuthorityV2()
            dma.deviceIp = device.get_discover_address()
            dma.deviceUsername = device.get_admin_creds().username
            dma.devicePassword = device.get_admin_creds().password
            dma.createChildTasks = True
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

        if self.ifc.version < 'bigiq 4.5':
            msg = "ASM DMA task did not complete in {0} seconds. Last status: {1.overallStatus}"
            return dma.wait(self.api, task, timeout=self.timeout,
                            timeout_message=msg)
        else:
            msg = "ASM DMA task did not complete in {0} seconds. Last status: {1.status}"
            return dma.wait_status(self.api, task, timeout=self.timeout,
                                   timeout_message=msg)

    def completed(self, device, ret):
        if self.ifc.version < 'bigiq 4.5':
            assert ret.status in ['COMPLETED'], \
                'Discovery of {0} failed: {1}:{2}'.format(device, ret.overallStatus,
                                                          ret.error)
        else:
            assert ret.status in ['FINISHED'], \
                'Discovery of {0} failed: {1}:{2}'.format(device, ret.status,
                                                          ret.errorMessage)

discover_adc = None
class DiscoverAdc(Discover):  # @IgnorePep8
    """Makes sure all devices are discovered.

    @param devices: A list of f5test.interfaces.config.DeviceAccess instances.
    @param refresh: A bool flag, if set it will re-discover existing devices.
    @rtype: None
    """

    def prep(self):
        super(DiscoverAdc, self).prep()
        self.discovered_count = 0

        # Set the ADC specific properties
        adc = Options(properties={})
        prop = adc.properties
        prop.dmaConfigPathScope = 'full'
        prop.isRestProxyEnabled = True
        prop.isSoapProxyEnabled = True
        prop.isTmshProxyEnabled = False
        self.options.update(adc)

    def completed(self, device, ret):
        super(DiscoverAdc, self).completed(device, ret)
        self.discovered_count += 1
        LOG.info('Waiting for any refresh task to finish...')

        # odata = Options(filter='status eq STARTED')
        odata = Options(orderby='lastUpdateMicros desc', top=1)
        wait(lambda: self.api.get(RefreshCurrentConfig.URI, odata_dict=odata)['items'][0],
             condition=lambda x: x.status == 'FINISHED', timeout=90, stabilize=15,
             progress_message="{0.status}:{0.subStatus}",
             interval=1)

    def post_discovery_steps(self):
        odata = Options(filter='status eq STARTED')

        LOG.info('Waiting for any refresh task to finish...')
        wait(lambda: self.api.get(RefreshCurrentConfig.URI, odata_dict=odata),
             condition=lambda x: not x.totalItems, timeout=90, stabilize=5,
             interval=1)

        odata = Options(orderby='lastUpdateMicros desc', top=1)
        tasks = self.api.get(RefreshCurrentConfig.URI, odata_dict=odata)['items']
        if tasks:
            ret = tasks[0]
            assert ret.status == 'FINISHED', 'Most recent RefreshCurrentConfig task failed: {0.status}:{0.errorMessage}'.format(ret)

        resp = self.api.get(self.uri)
        theirs = dict([(IPAddress(x.address), x) for x in resp['items']])
        return dict((x, theirs[IPAddress(x.get_discover_address())])
                    for x in self.devices)

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
                elif device_group not in CleanDgCerts.DEVICE_GROUPS:
                    LOG.info("Deleting {0} from {1}".format(device.address, device_group))
                    api.delete(device.selfLink)
            DeviceResolver.wait(api, device_group)

            # Remove device groups that aren't the default ones
            if device_group not in CleanDgCerts.DEVICE_GROUPS:
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

discover_access = None
class DiscoverAccess(Discover):  # @IgnorePep8
    """Makes sure all devices are discovered.

    @param devices: A list of f5test.interfaces.config.DeviceAccess instances.
    @param refresh: A bool flag, if set it will re-discover existing devices.
    @rtype: None
    """
    group = DEFAULT_ACCESS_GROUP
    task = access.DeviceManagerTask
    URI = '/mgmt/cm/access/device-manager'

    def __init__(self, *args, **kwargs):
        super(DiscoverAccess, self).__init__(*args, **kwargs)
        self.group = self.__class__.group
        self.uri = access.DeviceManagerTask.URI
        self.timeout = ACCESS_DISCOVERY_TIMEOUT

    def set_uri(self):
        self.uri = DeviceGroup.DEVICES_URI % DEFAULT_ACCESS_GROUP

    def setup(self):
        # get all discovered Access devices from big-iq
        # check requested devices that some of them was not discovered in Access module:
        # - discovered in access     => skip
        # - not discovered in Access => discover
        # TODO: re-discover is not implemented

        discovered_devices = self.api.get(DeviceGroup.DEVICES_URI % DEFAULT_ACCESS_GROUP)
        ours = dict([(IPAddress(x.get_discover_address()), x) for x in self.devices])
        theirs = dict([(IPAddress(x.address), x) for x in discovered_devices['items']])

        LOG.info(ours)
        LOG.info(theirs)

        for address in set(theirs) - set(ours):
            theirs.pop(address)

        theirs_set = set([x for x in theirs if theirs[x].state == 'ACTIVE'])
        self.set_uri()
        # Add any devices that are not already discovered.
        # Discovery of multiple devices at once is not supported by API.
        for address in set(ours) - theirs_set:
            device = ours[address]

            delay = VIPRION_DISCOVERY_DELAY \
                if device.specs.get('is_cluster', False) \
                else DEFAULT_DISCOVERY_DELAY

            if device.specs.has_tmm_restarted:
                diff = datetime.datetime.now() - device.specs.has_tmm_restarted
                if diff < datetime.timedelta(seconds=delay) \
                   and device.get_discover_address() != device.get_address():
                    delay -= diff.seconds
                    LOG.info('XXX: Waiting %d seconds for tmm to come up...' % delay)
                    time.sleep(delay)

            if address in theirs:
                # Device already discovered
                # TODO: rediscover/refresh
                pass
            else:
                ret = self.add_one(device)
                self.completed(device, ret)

        return self.post_discovery_steps()

    def add_one(self, device):
        # uri for device manager task
        uri = access.DeviceManagerTask.URI
        # sends a request to devices-manager to discover Access device
        # waits for status "Finished" for the task
        LOG.info('Adding device %s to %s...', device, self.group)
        dma = self.task()
        # Access "device-manager"  worker is able to process several
        # devices in one request. let's add only one device per requests.
        # setup() will invoke add_one() and pass only one device, then will
        # check the task status and check that device was discovered properly
        # TODO: discover multiple devices in one request
        dma.devices[0].deviceIp = device.get_discover_address()
        dma.devices[0].deviceUsername = device.get_admin_creds().username
        dma.devices[0].devicePassword = device.get_admin_creds().password
        dma.devices[0].rootUser = device.get_root_creds().username
        dma.devices[0].rootPassword = device.get_root_creds().password
        dma.devices[0].automaticallyUpdateFramework = True
        dma.update(self.options)
        task = self.api.post(uri, payload=dma)
        return dma.wait(self.ifc, task, timeout=self.timeout,
                        timeout_message="Access 'device-manager' task did not complete in {0} seconds")

    def completed(self, device, ret):

        assert ret.status in ['FINISHED'], \
                'Discovery of {0} failed: {1}:{2}'.format(device, ret.status,
                                                          ret.selfLink)
        for item in ret.devices:
            assert item.deviceReference, 'Discovery of {0} failed: {1}'.format(device, item.errorMessage)
        return ret.devices


delete_access = None
class DeleteAccess(Delete):  # @IgnorePep8
    group = DEFAULT_ACCESS_GROUP
    task = access.RemoveManagementAuthorityTask

    def remove_one(self, device, uri):
        LOG.info('Remove-management-authority task started for %s...', device)
        rma = self.task()
        rma.deviceOrGroupReference.link = uri
        task = self.api.post(self.task.URI, payload=rma)
        return rma.wait(self.ifc, task, timeout=ACCESS_DELETE_TIMEOUT,
                        timeout_message="Access 'remove-management-authority' task did not complete in {0} seconds")
