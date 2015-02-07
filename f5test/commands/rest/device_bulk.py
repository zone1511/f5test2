'''
Created on Jan 23, 2015

@author: jwong
'''
import datetime
import logging
import time

from netaddr import IPAddress

from ...base import Options
from ...interfaces.rest.emapi import EmapiResourceError
from ...interfaces.rest.emapi.objects import DeviceResolver
from ...interfaces.rest.emapi.objects.adc import RefreshCurrentConfig
from ...interfaces.rest.emapi.objects.system import BulkDiscovery, FileTransfer
from ...utils.wait import wait, wait_args, StopWait
from ..base import CommandError
from .base import IcontrolRestCommand
from .device import (DEFAULT_CLOUD_GROUP, VIPRION_DISCOVERY_DELAY,
                     DEFAULT_DISCOVERY_DELAY, DEFAULT_AUTODEPLOY_GROUP)


LOG = logging.getLogger(__name__)
DISCOVERY_TIMEOUT = 300
DEVICES_CSV = 'devices.csv'

discover = None
class Discover(IcontrolRestCommand):  # @IgnorePep8
    """Makes sure all devices are "identified" in a certain group by the
    DeviceResolver.

    @param devices: A list of f5test.interfaces.config.DeviceAccess instances.
    @rtype: None
    """

    def __init__(self, devices, group=None, timeout=DISCOVERY_TIMEOUT,
                 options={}, *args, **kwargs):
        super(Discover, self).__init__(*args, **kwargs)
        self.devices = list(devices)
        self.group = group
        self.uri = None
        self.timeout = timeout
        self.options = options

        v = self.ifc.version
        if v < 'bigiq 4.4':
            raise CommandError("Bulk discovery doesn't exist on " % v)

    def create_csv(self, devices):
        # Upload a CSV File to BIG-IQ
        LOG.info("Generating CSV file for bulk discover.")
        content = str()
        for device in devices:
            admin_name = device.get_admin_creds().username
            admin_pw = device.get_admin_creds().password
            self_ip = device.get_discover_address()
            root_name = device.get_root_creds().username
            root_pw = device.get_root_creds().password
            content += "%s,%s,%s,True,%s,%s\n" % (self_ip, admin_name,
                                                  admin_pw, root_name,
                                                  root_pw)
        return FileTransfer.upload(self.api, content, file_name=DEVICES_CSV)

    def set_uri(self):
        assert self.group, "A group is required"
        self.uri = DeviceResolver.DEVICES_URI % self.group

    def prep(self):
        super(Discover, self).prep()
        self.set_uri()

        if self.group not in (DEFAULT_CLOUD_GROUP, DEFAULT_AUTODEPLOY_GROUP):
            raise CommandError("Cannot use bulk discovery on %s" % self.group)

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

    def completed(self, ret):
        assert ret.status in ['FINISHED'], \
            'Bulk Discovery Failed: {0}.'.format(ret.status)

    def setup(self):
        # Make mapping of what's on the server and what's in our config
        resp = self.resp
        theirs = dict([(IPAddress(x.address), x) for x in resp['items']])
        ours = dict([(IPAddress(x.get_discover_address()), x) for x in self.devices])

        for address in set(theirs) - set(ours):
            theirs.pop(address)

        theirs_set = set([x for x in theirs if theirs[x].state == 'ACTIVE'])

        # Check to see if there are any VIPRIONs in the harness
        is_viprion = sum(1 for device in self.devices
                         if device.specs.get('is_cluster', False))

        delay = VIPRION_DISCOVERY_DELAY if is_viprion else \
                DEFAULT_DISCOVERY_DELAY

        # Get times where BIG-IPs were restarted
        times_restarted = set(device.specs.has_tmm_restarted for device
                              in self.devices if device.specs.has_tmm_restarted)

        mgmts = set(IPAddress(x.get_address()) for x in self.devices)

        diff = datetime.datetime.now() - max(times_restarted) \
               if times_restarted else None

        if times_restarted and mgmts.difference(set(ours)) and \
           diff < datetime.timedelta(seconds=delay):
            delay -= diff.seconds
            LOG.info('XXX: Waiting %d seconds for tmm to come up...' % delay)
            time.sleep(delay)

        # Start bulk discovery. API here is used to discover many BIG-IPs.
        # Does not work with security module
        undiscovered_devices = (set(ours) - theirs_set)
        if undiscovered_devices:
            devices = [ours[address] for address in undiscovered_devices]
            resp = self.create_csv(devices)
            path = resp.localFilePath

            resp = self.api.get(DeviceResolver.ITEM_URI % self.group)
            payload = BulkDiscovery(filePath=path)
            payload.update(self.options)
            payload.groupReference = resp
            bulk = self.api.post(BulkDiscovery.URI, payload)
            resp = BulkDiscovery.wait(self.api, bulk, timeout=self.timeout)
            self.completed(resp)

        return self.post_discovery_steps()

    def post_discovery_steps(self):
        # Map our devices to their selfLinks
        resp = self.api.get(self.uri)
        theirs = dict([(IPAddress(x.address), x) for x in resp['items']])
        return dict((x, theirs[IPAddress(x.get_discover_address())]) for x in self.devices)


discover_cloud = None
class DiscoverCloud(Discover):  # @IgnorePep8
    """Makes sure all devices are discovered.

    @param devices: A list of f5test.interfaces.config.DeviceAccess instances.
    @rtype: None
    """

    def __init__(self, *args, **kwargs):
        super(DiscoverCloud, self).__init__(*args, **kwargs)
        self.group = DEFAULT_CLOUD_GROUP

    def set_uri(self):
        assert self.group, "A group is required starting with 4.3"
        self.uri = DeviceResolver.DEVICES_URI % self.group


discover_adc = None
class DiscoverAdc(Discover):  # @IgnorePep8
    """Makes sure all devices are discovered.

    @param devices: A list of f5test.interfaces.config.DeviceAccess instances.
    @rtype: None
    """

    def prep(self):
        super(DiscoverAdc, self).prep()

        # Set the ADC specific properties
        adc = Options(properties={})
        prop = adc.properties
        prop.dmaConfigPathScope = 'full'
        prop.isRestProxyEnabled = True
        prop.isSoapProxyEnabled = True
        prop.isTmshProxyEnabled = False
        self.options.update(adc)

    def completed(self, ret):
        super(DiscoverAdc, self).completed(ret)
        count = len(self.devices) * 2
        LOG.info('Waiting for any refresh task to finish...')

        odata = Options(orderby='lastUpdateMicros desc', top=count)
        wait(lambda: self.api.get(RefreshCurrentConfig.URI, odata_dict=odata)['items'],
             condition=lambda x: not set(y.status for y in x).
             difference(set(['FINISHED'])),
             progress_cb=lambda x: "%s : %s" % (set(y.status for y in x),
                                                set(y.subStatus for y in x)),
             timeout=self.timeout, stabilize=15, interval=5)

    def post_discovery_steps(self):
        odata = Options(filter='status eq STARTED')
        LOG.info('Waiting for any refresh task to finish...')
        wait(lambda: self.api.get(RefreshCurrentConfig.URI, odata_dict=odata),
             condition=lambda x: not x.totalItems, timeout=90, stabilize=5,
             interval=1)

        err_msg = dict()
        ret = self.api.get(RefreshCurrentConfig.URI)['items']
        for item in ret:
            if item.status != 'FINISHED':
                err_msg.update(item)
        if err_msg:
            import json
            msg = json.dumps(err_msg, sort_keys=True, indent=4,
                             ensure_ascii=False)
            assert "Refresh Current Config failed:\n %s" % msg

        resp = self.api.get(self.uri)
        theirs = dict([(IPAddress(x.address), x) for x in resp['items']])
        return dict((x, theirs[IPAddress(x.get_discover_address())])
                    for x in self.devices)
