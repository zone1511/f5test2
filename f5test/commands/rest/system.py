'''
Created on Feb 11, 2014

@author: a.dobre@f5.com
'''
from .base import IcontrolRestCommand
from ..base import CommandError
from ...base import Options, AttrDict
from ...utils.wait import wait, WaitTimedOut
from .device import DEFAULT_ALLBIGIQS_GROUP, DEFAULT_CLOUD_GROUP
from ...interfaces.testcase import ContextHelper
from ...interfaces.rest.emapi.objects import DeviceResolver, FailoverState
from ...interfaces.rest.emapi.objects.base import Link
from ...interfaces.rest.emapi.objects.shared import UserRoles, \
    UserCredentialData, HAPeerRemover, EventAnalysisTasks, EventAggregationTasks, \
    DeviceInfo, DeviceGroup
from netaddr import IPAddress, ipv6_full
import logging
import json

LOG = logging.getLogger(__name__)
PARAMETER = 'shared:device-partition:devicepartitionparameters'
DEFAULT_AUTODEPLOY_GROUP = 'cm-autodeploy-group-manager-autodeployment'
DEFAULT_SECURITY_GROUP = 'cm-firewall-allDevices'


add_user = None
class AddUser(IcontrolRestCommand):  # @IgnorePep8
    """Adds one user via the icontrol rest api

    @param name: name #mandatory
    @type name: string
    @param password: password #optional #will set it as the username if not specified
    @type password: string
    @param displayname: display name #optional
    @type displayname: string

    @return: the user's api resp
    @rtype: attr dict json
    """
    def __init__(self, name, password=None, displayname=None,
                 *args, **kwargs):
        super(AddUser, self).__init__(*args, **kwargs)
        self.name = name
        if password is None:
            password = name
        self.password = password
        self.displayname = displayname

    def setup(self):
        """Adds one user."""
        LOG.debug("Creating User '{0}'...".format(self.name))

        payload = UserCredentialData(name=self.name, password=self.password)
        if self.displayname:
            payload['displayName'] = self.displayname

        resp = self.api.post(UserCredentialData.URI, payload=payload)
        LOG.info("Created User '{0}'...further result in debug.".format(self.name))

        # workaround for BZ474147 in 4.4.0 RTM
        if self.ifc.version < "bigiq 4.5.0":
            wait(lambda: self.api.get(UserCredentialData.ITEM_URI % self.name),
                 progress_cb=lambda _: "Waiting until user appears...",
                 interval=1,
                 timeout=60)

        return resp


assign_role_to_user = None
class AssignRoleToUser(IcontrolRestCommand):  # @IgnorePep8
    """Assigns a role to a user

    @param rolename: rolename #mandatory
    @type rolename: string
    @param username: username #mandatory
    @type username: string

    @return: the role's api resp
    @rtype: attr dict json
    """
    def __init__(self, rolename, username,
                 *args, **kwargs):
        super(AssignRoleToUser, self).__init__(*args, **kwargs)
        self.rolename = rolename
        self.username = username

    def setup(self):

        LOG.debug("Assigning role '{0}' to user '{1}'."
                 .format(self.rolename, self.username))
        payload = UserRoles()
        payload.update(self.api.get(UserRoles.URI % self.rolename))  # @UndefinedVariable

        user_resp = self.api.get(UserCredentialData.ITEM_URI % (self.username))
        payload.userReferences.append(user_resp)

        resp = self.api.put(UserRoles.URI % self.rolename, payload=payload)
        LOG.info("Assigned role '{0}' to user '{1}'. further results in debug."
                 .format(self.rolename, self.username))

        return resp

wait_restjavad = None
class WaitRestjavad(IcontrolRestCommand):  # @IgnorePep8
    """Waits until devices in DEFAULT_ALLBIGIQS_GROUP are done pending.

    @return: None
    """
    def __init__(self, devices, *args, **kwargs):
        super(WaitRestjavad, self).__init__(*args, **kwargs)
        self.devices = devices
        self.group = DEFAULT_ALLBIGIQS_GROUP

    def prep(self):
        self.context = ContextHelper(__file__)

    def cleanup(self):
        self.context.teardown()

    def setup(self):
        LOG.info('Waiting until devices finished PENDING: %s' % self.devices)

        for device in self.devices:
            p = self.context.get_icontrol_rest(device=device).api

            # Wait until devices appear in items (there should be at least localhost)
            wait(lambda: p.get(DeviceResolver.DEVICES_URI % self.group)['items'],
                 progress_cb=lambda ret: 'Waiting for restjavad on {0}.'.format(device))
            DeviceResolver.wait(p, self.group)

            wait(lambda: p.get(FailoverState.URI),
                 progress_cb=lambda _: 'Waiting for FailoverState on {0}'.format(device))

setup_ha = None
class SetupHa(IcontrolRestCommand):  # @IgnorePep8
    """Adds a new pair in System->High Availability.

    Original author: John Wong

    @param peers: Peer BIGIQs for HA
    @type peers: tuple, list

    @return: None
    """
    def __init__(self, peers, *args, **kwargs):
        super(SetupHa, self).__init__(*args, **kwargs)
        self.peers = peers
        self.group = DEFAULT_ALLBIGIQS_GROUP

    def prep(self):
        self.context = ContextHelper(__file__)
        WaitRestjavad(self.peers).run()

    def cleanup(self):
        self.context.teardown()

    def setup(self):
        LOG.info("Setting up HA with %s...", self.peers)
        skip_expect_down = True
        gossipers = {}
        # Delegate the default bigiq to be the active device and verify only 1 exists.
        api = self.ifc.api
        active_device = self.ifc.device

        ret = api.get(DeviceResolver.DEVICES_URI % self.group)
        theirs = {x.address: x for x in ret['items']}

        active_full_ip = IPAddress(active_device.get_discover_address()).format(ipv6_full)
        gossipers[active_device] = theirs[active_full_ip]

        LOG.info('Set relativeRank=0 on active_device...')
        self_device = next(x for x in ret['items'] if x.address == active_full_ip)
        payload = Options()
        payload.properties = Options()
        payload.properties[PARAMETER] = Options()
        payload.properties[PARAMETER].relativeRank = 0
        api.patch(self_device.selfLink, payload=payload)

        # Add standby BigIQs to group on active device
        for device in self.peers:
            payload = DeviceResolver()
            payload.address = IPAddress(device.get_discover_address()).format(ipv6_full)
            payload.userName = device.get_admin_creds().username
            payload.password = device.get_admin_creds().password

            if theirs.get(payload.address) and \
               theirs[payload.address].state != 'ACTIVE' and \
               theirs[payload.address].state not in  DeviceResolver.PENDING_STATES:
                LOG.info('Deleting device {0}...'.format(payload.address))
                api.delete(theirs[payload.address].selfLink)
                DeviceResolver.wait(api, self.group)
                theirs.pop(payload.address)

            if payload.address not in theirs:
                LOG.info('Adding device {0} using {1}...'.format(device, payload.address))
                ret = api.post(DeviceResolver.DEVICES_URI % self.group, payload)
                gossipers[device] = ret
                skip_expect_down = False
            else:
                gossipers[device] = theirs[payload.address]

        for device in self.peers:
            p = self.context.get_icontrol_rest(device=device).api
            wait(lambda: p.get(DeviceResolver.DEVICES_URI % self.group),
                  condition=lambda resp: len(resp['items']) >= len(self.peers),
                  progress_cb=lambda resp: "device group:{0}   bigiqs:{1} ".format(len(resp['items']), len(self.peers)))
            DeviceResolver.wait(p, self.group)

        def expect_down():
            ret = []
            for device in self.peers:
                try:
                    p = self.context.get_icontrol_rest(device=device).api
                    p.get(DeviceResolver.DEVICES_URI % self.group)
                    ret.append(False)
                except:
                    ret.append(True)
            return ret

        if not skip_expect_down:
            wait(lambda: all(expect_down()),
                 progress_cb=lambda resp: "Wait until peer devices are down...",
                 timeout=60, interval=5)

        WaitRestjavad(self.peers).run()

        for device in self.peers + [active_device]:
            p = self.context.get_icontrol_rest(device=device).api
            FailoverState.wait(p, timeout=60)


teardown_ha = None
class TeardownHa(IcontrolRestCommand):  # @IgnorePep8
    """Removes peer from HA pair in System->High Availability.

    Original author: John Wong

    @param peers: Peer BIGIQs
    @type peers: tuple, list

    @return: None
    """
    def __init__(self, peers, *args, **kwargs):
        super(TeardownHa, self).__init__(*args, **kwargs)
        self.peers = peers
        self.group = DEFAULT_ALLBIGIQS_GROUP

    def prep(self):
        self.context = ContextHelper(__file__)

    def cleanup(self):
        self.context.teardown()

    def setup(self):
        LOG.info("Unsetting HA with %s...", self.peers)
        api = self.ifc.api
        resp = api.get(DeviceResolver.DEVICES_URI % self.group)

        uris_by_address = dict((IPAddress(x.address).format(ipv6_full), x) for x in resp['items'])
        devices = dict((x, uris_by_address.get(IPAddress(x.get_discover_address()).format(ipv6_full)))
                       for x in self.peers if uris_by_address.get(IPAddress(x.get_discover_address()).format(ipv6_full)))
        for item in devices.values():
            payload = HAPeerRemover()
            payload.peerReference = item
            api.post(HAPeerRemover.URI, payload=payload)
            DeviceResolver.wait(api, self.group)

        # Wait until cm-shared-all-big-iqs from peer devices are out of pending state.
        for device in self.peers:
            p = self.context.get_icontrol_rest(device=device).api
            DeviceResolver.wait(p, self.group)

bz_help1 = None
class BzHelp1(IcontrolRestCommand):  # @IgnorePep8
    """BZ468263.

    Original author: John Wong

    @param peers: Peer BIGIQs
    @type peers: tuple, list

    @return: None
    """
    def __init__(self, peers, *args, **kwargs):
        super(BzHelp1, self).__init__(*args, **kwargs)
        self.peers = peers

    def get_devices(self):
        ret = {}
        api = self.ifc.api
        resp = api.get(DeviceResolver.URI)
        device_groups = [x.groupName for x in resp['items']]
        for device_group in device_groups:
            resp = api.get(DeviceResolver.DEVICES_URI % device_group)
            ret[device_group] = resp
        return ret

    def setup(self):
        # Added to help narrow down what is happening after HA removal for BZ468263
        api = self.ifc.api
        peers = set(IPAddress(x.get_discover_address()).format(ipv6_full) for x in self.peers)
        if not peers:
            LOG.info("No peers, do nothing.")
            return

        try:
            resp = wait(self.get_devices,
                    condition=lambda ret: peers.intersection(set(y.address
                                     for x in ret.values()for y in x['items'])),
                   progress_cb=lambda ret: 'Peer BIGIQs: {0}; Default BIGIQ: {1}'.format(peers,
                        set(y.address for x in ret.values()for y in x['items'])),
                   timeout=60)

            for items in resp.values():
                for item in items['items']:
                    if item.address in peers:
                        LOG.warning("Deleting peer BIGIQ as it showed back up per BZ474786")
                        api.delete(item.selfLink)

        except WaitTimedOut:
            LOG.info("Peer BIG-IQ never appears in {0}".format(self.get_devices().keys()))

# Ref - https://peterpan.f5net.com/twiki/bin/view/Cloud/AnalyticsDesign
# Ref - https://peterpan.f5net.com/twiki/bin/view/Cloud/EventAnalyticsAPI
add_aggregation_task = None
class AddAggregationTask(IcontrolRestCommand):  # @IgnorePep8
    """Adds an Aggregation Task via the icontrol rest api
    Example usage:
    add_aggregation_task(name="test-aggregation-task-1",
                        specs={'eventSourcePollingIntervalMillis': 1000,
                               'itemCountCommitThreshold': 100,
                               'isIndexingRequired': True,
                               'description': 'TestEAT',
                               'generation': 0,
                               'lastUpdateMicros': 0,
                               'expirationMicros': 1400194354500748
                               }
                        logspecs={'tcpListenEndpoint': 'http://localhost:9020',

                                 })

    @param name: name #mandatory
    @type name: string

    @param specs: Default Item Specs as a dict
    @type specs: Dict
    @param logspecs: sysLogConfig Item Specs as a dicts
    @type logspecs: Dict

    @return: the api resp
    @rtype: attr dict json
    """
    def __init__(self, name,
                 specs=None, logspecs=None,
                 *args, **kwargs):
        super(AddAggregationTask, self).__init__(*args, **kwargs)
        self.name = name
        self.specs = specs
        self.logspecs = logspecs

    def setup(self):
        """Adds an aggregation task."""
        LOG.debug("Creating Aggregation Task '{0}'...".format(self.name))

        payload = EventAggregationTasks(name=self.name)
        if self.specs:
            for item, value in self.specs.iteritems():
                payload[item] = value
        if self.logspecs:
            x = AttrDict()
            for item, value in self.logspecs.iteritems():
                x[item] = value
            payload.sysLogConfig.update(x)

        resp = self.api.post(EventAggregationTasks.URI, payload=payload)
        self.wait_to_start(resp)

        return resp

    def wait_to_start(self, payload):
        """waits for a task to be started (accepting events)"""

        self.payload = payload

        def is_status_started():
            payload = self.api.get(EventAggregationTasks.ITEM_URI % self.payload.id)
            if payload.status == 'STARTED':
                return True

        wait(is_status_started,
             progress_cb=lambda x: "Aggregation Task Status Not Started Yet",
             timeout=10,
             timeout_message="Aggregation Task is not Started after {0}s")
        return True

# Ref - https://peterpan.f5net.com/twiki/bin/view/Cloud/AnalyticsDesign
# Ref - https://peterpan.f5net.com/twiki/bin/view/Cloud/EventAnalyticsAPI
cancel_aggregation_task = None
class CancelAggregationTask(IcontrolRestCommand):  # @IgnorePep8
    """Cancels an Aggregation Task via the icontrol rest api using task id or name
    Type: PATCH

    @param name: name
    @type name: string
    @param itemid: the item id
    @type itemid: string

    @return: the api resp
    @rtype: attr dict json
    """
    def __init__(self, name=None, itemid=None, timeout=60,
                 *args, **kwargs):
        super(CancelAggregationTask, self).__init__(*args, **kwargs)
        self.name = name
        self.itemid = itemid
        self.timeout = timeout

    def setup(self):
        """Cancel an aggregation task."""
        LOG.info("Canceling Aggregation Task '{0}'...".format(self.name or self.itemid))

        payload = None
        if self.itemid:
            payload = self.api.get(EventAggregationTasks.ITEM_URI % self.itemid)
        else:
            for item in self.api.get(EventAggregationTasks.URI)['items']:
                if item.name:
                    if item.name == self.name:
                        payload = item
                        self.itemid = item.id

        if payload.status != "CANCELED":
            payload['status'] = "CANCEL_REQUESTED"
            self.api.patch(EventAggregationTasks.ITEM_URI % payload.id, payload)

        self.resp = None

        def is_status_canceled():
            self.resp = self.api.get(EventAggregationTasks.ITEM_URI % self.itemid)
            if self.resp.status == "CANCELED":
                return True
        wait(is_status_canceled,
             progress_cb=lambda x: "Task Status: {0}".format(self.resp.status),
             timeout=self.timeout,
             interval=2,
             timeout_message="Task is not Canceled after {0}s")

        return self.resp

# Ref - https://peterpan.f5net.com/twiki/bin/view/Cloud/AnalyticsDesign
# Ref - https://peterpan.f5net.com/twiki/bin/view/Cloud/EventAnalyticsAPI
add_analysis_task = None
class AddAnalysisTask(IcontrolRestCommand):  # @IgnorePep8
    """Adds an Analysis Task via the icontrol rest api
    Example usage:
    add_analysis_task(aggregationreference="id_of_aggregation_task or id_of_device_group",
                        specs={'collectFilteredEvents': True,
                               },
                        histograms=[{},
                                 ])

    @param point_to:  link reference to Aggregation task or device group #mandatory
    @type point_to: string

    @param multitier: if used for collecting from multiple aggregation tasks
    @type multitier: Boolean

    Optional params:
    @param specs: Default Item Specs as a dict
    @type specs: Dict
    @param histograms: histograms as a list of dicts
    @type histograms: List of AttrDicts

    @return: the api resp
    @rtype: attr dict json
    """
    def __init__(self, point_to,
                 specs=None, histograms=None,
                 multitier=False,
                 multitierspecs=None,
                 *args, **kwargs):
        super(AddAnalysisTask, self).__init__(*args, **kwargs)
        self.aggregationreference = point_to
        self.specs = specs
        self.histograms = histograms
        self.multitier = multitier
        self.multitierspecs = multitierspecs

    def setup(self):
        """Adds an analysis task."""
        LOG.debug("Creating Analysis Task for '{0}'...".format(self.aggregationreference))

        payload = EventAnalysisTasks()
        if not self.multitier:
            if not self.aggregationreference.endswith("/worker/"):
                self.aggregationreference += "/worker/"
            payload['eventAggregationReference'] = Link(link=self.aggregationreference)
        else:
            multitierconfig = AttrDict(deviceGroupReference=Link(link=self.aggregationreference),
                                       eventAggregationTaskFilter="description eq '*'",
                                       completionCheckIntervalSeconds=2,
                                       )
            if self.multitierspecs:
                for item, value in self.multitierspecs.iteritems():
                    multitierconfig[item] = value
            payload['multiTierConfig'] = multitierconfig
        if self.specs:
            for item, value in self.specs.iteritems():
                payload[item] = value
        if self.histograms:
            payload['histograms'] = []
            for histogram in self.histograms:
                x = AttrDict()
                for item, value in histogram.iteritems():
                    x[item] = value
                payload.histograms.extend([x])
        # print "Payload sent to analysis:"
        # print json.dumps(payload, sort_keys=True, indent=4, ensure_ascii=False)
        resp = self.api.post(EventAnalysisTasks.URI, payload=payload)

        return resp


# Ref - https://peterpan.f5net.com/twiki/bin/view/Cloud/AnalyticsDesign
# Ref - https://peterpan.f5net.com/twiki/bin/view/Cloud/EventAnalyticsAPI
cancel_analysis_task = None
class CancelAnalysisTask(IcontrolRestCommand):  # @IgnorePep8
    """Cancels an Analysis Task via the icontrol rest api using selflink
    Forces the Finshed state to it so it can be deleted afterwards.
    Type: PUT

    @param selflink: selflink
    @type selflink: string

    @return: the api resp
    @rtype: attr dict json
    """
    def __init__(self, selflink=None, timeout=60,
                 *args, **kwargs):
        super(CancelAnalysisTask, self).__init__(*args, **kwargs)
        self.selflink = selflink
        self.timeout = timeout

    def setup(self):
        """Cancel an analysis task."""
        LOG.info("Canceling Analysis Task '{0}'...".format(self.selflink))

        payload = self.api.get(self.selflink)

        if payload.status not in ["CANCELED", "FINISHED", "DELETED"]:
            # Issue a put with status="FINISHED" only
            self.api.put(self.selflink, AttrDict(status="FINISHED"))

        self.resp = None

        def is_status_canceled():
            self.resp = self.api.get(self.selflink)
            if self.resp.status:
                if self.resp.status in ["CANCELED", "FINISHED", "DELETED"]:
                    return True
        wait(is_status_canceled,
             progress_cb=lambda x: "Task Status: {0}".format(self.resp.status),
             timeout=self.timeout,
             timeout_message="Task is not Canceled after {0}s")

        return self.resp

wait_rest_ifc = None
class WaitRestIfc(IcontrolRestCommand):  # @IgnorePep8
    """Waits until devices can be reached and are in a group.

    @return: None
    """
    def __init__(self, devices, group=None, *args, **kwargs):
        super(WaitRestIfc, self).__init__(*args, **kwargs)
        self.devices = devices
        if not group:
            group = DEFAULT_ALLBIGIQS_GROUP
        self.group = group

    def prep(self):
        self.context = ContextHelper(__file__)

    def cleanup(self):
        self.context.teardown()

    def setup(self):
        LOG.info('Waiting until devices can be reached: %s' % self.devices)

        for device in self.devices:
            self.p = None

            def is_rest_ready():
                self.p = self.context.get_icontrol_rest(device=device).api
                self.p.get(DeviceInfo.URI)
                return True
            wait(is_rest_ready, interval=1,
                 progress_cb=lambda ret: 'Waiting for rest api on {0}.'.format(device),
                 timeout=60,
                 timeout_message="Couldn't grab rest interface after {0}s")

            # Wait until devices appear in items (there should be at least localhost)
            wait(lambda: self.p.get(DeviceResolver.DEVICES_URI % self.group)['items'],
                 progress_cb=lambda ret: 'Waiting for group on {0}.'.format(device))
            DeviceResolver.wait(self.p, self.group)

add_device_group = None
class AddDeviceGroup(IcontrolRestCommand):  # @IgnorePep8
    """Adds a Device Group to a device
    Type: POST

    @param groupname: groupname
    @type groupname: string

    @return: the api resp
    @rtype: attr dict json
    """
    def __init__(self, groupname,
                 *args, **kwargs):
        super(AddDeviceGroup, self).__init__(*args, **kwargs)
        self.groupname = groupname

    def setup(self):
        """add a group."""

        resp = None
        groupresp = self.api.get(DeviceGroup.URI)['items']
        for item in groupresp:
            if item.groupName == self.groupname:
                resp = item
        if not resp:
            LOG.info("Adding Device Group '{0}'...".format(self.groupname))
            payload = DeviceGroup()
            payload['groupName'] = self.groupname
            resp = self.api.post(DeviceGroup.URI, payload=payload)
        else:
            LOG.info("Device Group already there ({0})...".format(self.groupname))
        LOG.info("Waiting for group to have localhost....")
        DeviceResolver.wait(self.api, group=self.groupname)
        return resp


check_device_group_exists = None
class CheckDeviceGroupExists(IcontrolRestCommand):  # @IgnorePep8
    """Checks if a device Group exists on a device
    Type: GET

    @param groupname: groupname
    @type groupname: string

    @return: the api resp or None
    @rtype: attr dict json or None
    """
    def __init__(self, groupname,
                 *args, **kwargs):
        super(CheckDeviceGroupExists, self).__init__(*args, **kwargs)
        self.groupname = groupname

    def setup(self):
        """check for group"""

        group = None
        groupresp = self.api.get(DeviceGroup.URI)['items']
        for item in groupresp:
            if item.groupName == self.groupname:
                group = item

        return group
