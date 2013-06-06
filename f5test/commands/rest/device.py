'''
Created on Jan 30, 2013

@author: jono
'''
from .base import RestCommand
# from ..base import CommandError
from ...base import Options
from ...utils.wait import wait, wait_args
from ...interfaces.rest.emapi.objects import (ManagedDevice, ManagedDeviceCloud,
    DeclareMgmtAuthorityTask, RemoveMgmtAuthorityTask)
import logging
import time

LOG = logging.getLogger(__name__)
DEFAULT_DISCOVERY_DELAY = 90
DEFAULT_CONFLICT = 'USE_RUNNING'


delete = None
class Delete(RestCommand):
    """Delete devices given their selfLink and wait until all devices are gone.

    @param devices: A dictionary of devices as keys and URIs as values
    @rtype: None
    """
    def __init__(self, devices, *args, **kwargs):
        super(Delete, self).__init__(*args, **kwargs)
        self.devices = devices

    def setup(self):
        if not self.devices:
            return

        for device, uri in self.devices.items():
            LOG.info('RMA started for %s...', device)
            rma = RemoveMgmtAuthorityTask()
            rma.deviceLink = uri
            task = self.api.post(RemoveMgmtAuthorityTask.URI, payload=rma)
            rma.wait(self.api, task)

        def delete_completed():
            resp = self.api.get(ManagedDevice.URI)
            theirs = set([x['selfLink'] for x in resp['items']])
            ours = set(self.devices.values())
            return not theirs.intersection(ours)

        # Now we wait until devices are really gone...
        # Can it be dumber than this?
        wait(delete_completed,
             progress_cb=lambda x: 'Pending delete...')


discover = None
class Discover(RestCommand):
    """Makes sure all devices are discovered.

    @rtype: None
    """
    def __init__(self, devices, refresh=False, *args, **kwargs):
        super(Discover, self).__init__(*args, **kwargs)
        self.devices = devices
        self.refresh = refresh
        self.uri = ManagedDevice.URI

    def setup(self):
        # Key device objects and device IDs by address.
        devices = Options()

        # Delete any failed previous attempts
        resp = self.api.get(self.uri)
        delete(dict([(x['address'], x.selfLink) for x in resp['items'] if x.state != 'ACTIVE']),
               ifc=self.ifc)

        # Make mapping of what's on the server and what's in our config
        resp = self.api.get(self.uri)
        theirs = dict([(x['address'], Options(x)) for x in resp['items']])
        ours = dict([(x.get_discover_address(), x) for x in self.devices])

        # Delete anything that doesn't match our config
        delete(dict([(x, theirs[x].selfLink) for x in set(theirs) - set(ours)]),
               ifc=self.ifc)
        for address in set(theirs) - set(ours):
            theirs.pop(address)

        if self.refresh:
            theirs = set()

        delay = DEFAULT_DISCOVERY_DELAY
        # Add any devices that are not already discovered.
        # Discovery of multiple devices at once is not supported by API.
        for address in set(ours) - set(theirs):
            device = ours[address]
            if delay and device.specs._x_tmm_bug and device.get_discover_address() != device.get_address():
                LOG.info('XXX: Waiting %d seconds for tmm to come up...' % delay)
                time.sleep(delay)
                device.specs._x_tmm_bug = False

            LOG.info('Adding device %s...', device)
            subtask = Options()
            subtask.deviceIp = device.get_discover_address()
            subtask.deviceUsername = device.get_admin_creds().username
            subtask.devicePassword = device.get_admin_creds().password
            dma = DeclareMgmtAuthorityTask()
            dma.subtasks.append(subtask)

            task = self.api.post(DeclareMgmtAuthorityTask.URI, payload=dma)

            def custom_loop():
                resp = self.api.get(task.selfLink)
                if resp.subtasks[0].status == 'PENDING_CONFLICTS':
                    LOG.info('Conflicts detected, setting resolution: %s' % DEFAULT_CONFLICT)
                    for conflict in resp.subtasks[0].conflicts:
                        conflict.resolution = DEFAULT_CONFLICT
                    resp = self.api.patch(task.selfLink, payload=resp)
                return resp

            dma.wait(self.api, task, loop=custom_loop, timeout=60)

        resp = self.api.get(self.uri)
        for item in resp['items']:
            device = next(x for x in self.devices
                            if x.get_discover_address() == item.address)
            devices[device] = item.selfLink

        return devices


discover_cloud = None
class DiscoverCloud(RestCommand):
    """Makes sure all devices are discovered for BIGIQ Cloud.

    @rtype: None
    """
    def __init__(self, devices, *args, **kwargs):
        super(DiscoverCloud, self).__init__(*args, **kwargs)
        self.devices = devices
        self.uri = ManagedDeviceCloud.URI

    def setup(self):
        # Key device objects and device IDs by address.
        device_uris = []

        # Delete any failed previous attempts
        resp = self.api.get(self.uri)
        delete_cloud([x.selfLink for x in resp['items'] if x.state != 'ACTIVE'],
               ifc=self.ifc)

        # Make mapping of what's on the server and what's in our config
        resp = self.api.get(self.uri)
        theirs = dict([(x['address'], Options(x)) for x in resp['items']])
        ours = dict([(x.get_discover_address(), x) for x in self.devices])

        # Delete anything that doesn't match our config
        delete_cloud([theirs[x].selfLink for x in set(theirs) - set(ours)],
               ifc=self.ifc)
        for address in set(theirs) - set(ours):
            theirs.pop(address)
        device_uris.extend([x.selfLink for x in theirs.values()])

        delay = DEFAULT_DISCOVERY_DELAY
        # Add any devices that are not already discovered.
        for address in set(ours) - set(theirs):
            device = ours[address]
            if delay and device.specs._x_tmm_bug and device.get_discover_address() != device.get_address():
                LOG.info('XXX: Waiting %d seconds for tmm to come up...' % delay)
                time.sleep(delay)
                device.specs._x_tmm_bug = False

            LOG.info('Adding device %s...', device)
            payload = ManagedDevice()
            payload.deviceAddress = device.get_discover_address()
            payload.username = device.get_admin_creds().username
            payload.password = device.get_admin_creds().password
            resp = self.api.post(self.uri, payload=payload)
            device_uris.append(resp.selfLink)

            device = wait_args(self.api.get, func_args=[resp.selfLink],
                               condition=lambda x: x.state != 'PENDING',
                               progress_cb=lambda x: 'Discovery pending...')
            assert device.state == 'ACTIVE', "%s: %s" % (device.state, device.errors)

        return device_uris


delete_cloud = None
class DeleteCloud(RestCommand):
    """Delete devices. Works only for Cloud devices.

    @rtype: None
    """
    def __init__(self, device_uris, *args, **kwargs):
        super(DeleteCloud, self).__init__(*args, **kwargs)
        self.device_uris = device_uris
        self.uri = ManagedDeviceCloud.URI

    def setup(self):
        if not self.device_uris:
            return

        for device_uri in self.device_uris:
            LOG.debug('Deleting %s...', device_uri)
            self.api.delete(device_uri)

        def delete_completed():
            resp = self.api.get(self.uri)
            theirs = set([x['selfLink'] for x in resp['items']
                                        if not x.get('isLocal')])
            ours = set(self.device_uris)
            return not theirs.intersection(ours)

        wait(delete_completed,
             progress_cb=lambda x: 'Deleting...')
