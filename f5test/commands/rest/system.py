'''
Created on Feb 11, 2014

@author: a.dobre@f5.com
'''
from .base import IcontrolRestCommand, CommandFail
from ...base import Options, AttrDict
from ...utils.wait import wait, WaitTimedOut, wait_args
from .device import (DEFAULT_ALLBIGIQS_GROUP, DEFAULT_CLOUD_GROUP,
                     ASM_ALL_GROUP, FIREWALL_ALL_GROUP, DEFAULT_AUTODEPLOY_GROUP,
                     SECURITY_SHARED_GROUP, Discover)
from ...interfaces.testcase import ContextHelper
from ...interfaces.rest.emapi.objects.shared import DeviceResolver, FailoverState
from ...interfaces.rest.emapi.objects.base import Link
from ...interfaces.rest.emapi.objects.shared import UserRoles, \
    UserCredentialData, HAPeerRemover, EventAnalysisTasks, EventAggregationTasks, \
    DeviceInfo, DeviceGroup, TaskScheduler
from netaddr import IPAddress, ipv6_full
import logging

LOG = logging.getLogger(__name__)
PARAMETER = 'shared:device-partition:devicepartitionparameters'


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
    DEVICE_GROUPS = [SECURITY_SHARED_GROUP, DEFAULT_AUTODEPLOY_GROUP,
                     ASM_ALL_GROUP, FIREWALL_ALL_GROUP, SECURITY_SHARED_GROUP,
                     DEFAULT_CLOUD_GROUP, 'cm-asm-logging-nodes-trust-group',
                     'cm-websafe-logging-nodes-trust-group']

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

        api = self.ifc.api
        active_device = self.ifc.device

        ret = api.get(DeviceResolver.DEVICES_URI % self.group)
        peer_ips = set(IPAddress(x.get_discover_address()).format(ipv6_full) for x in self.peers)

        active_full_ip = IPAddress(active_device.get_discover_address()).format(ipv6_full)

        LOG.info('Set relativeRank=0 on active_device...')
        self_device = next(x for x in ret['items'] if x.address == active_full_ip)
        payload = Options()
        payload.properties = Options()
        payload.properties[PARAMETER] = Options()
        payload.properties[PARAMETER].relativeRank = 0
        api.patch(self_device.selfLink, payload=payload)

        options = Options()
        options.automaticallyUpdateFramework = False
        Discover(self.peers, group=DEFAULT_ALLBIGIQS_GROUP).run()

        # Wait until until peer BIG-IQs are added to the device groups.
        # This should remove the 'expect down' code that was here.
        for device_group in SetupHa.DEVICE_GROUPS:
            if self.ifc.version < 'bigiq 4.5.0' and device_group == 'cm-websafe-logging-nodes-trust-group':
                LOG.info('Skipping wait for {0} as this is older than 4.5.0'.format(device_group))
                continue

            wait(lambda: self.api.get(DeviceResolver.DEVICES_URI % device_group),
                 condition=lambda ret: len(peer_ips) == len(peer_ips.intersection(set(x.address for x in ret['items']))),
                 progress_cb=lambda ret: 'Waiting until {0} appears in {1}'.format(peer_ips, device_group),
                 interval=10, timeout=600)

        WaitRestjavad(self.peers).run()


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

        # Do a long 2 minute pause because of BZ484543 for BIG-IQ 4.5.0
        if devices.values() and abs(self.ifc.version) == 'bigiq 4.5.0':
            LOG.info("Pausing for 2 minutes before removing HA per BZ484543...")
            import time
            time.sleep(120)

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
    EXCLUDE = ['cm-websafe-logging-nodes-trust-group', 'iAppGroup', 'cm-asm-logging-nodes-trust-group']

    def __init__(self, peers, *args, **kwargs):
        super(BzHelp1, self).__init__(*args, **kwargs)
        self.peers = peers

    def prep(self):
        self.context = ContextHelper(__file__)

    def cleanup(self):
        self.context.teardown()

    def get_devices(self):
        ret = {}
        resp = self.api.get(DeviceResolver.URI)
#         device_groups = [x.groupName for x in resp['items']
#                          if not x.groupName in BzHelp1.EXCLUDE and
#                          abs(self.ifc.version) == 'bigiq 4.5.0']
        device_groups = [x.groupName for x in resp['items']]
        for device_group in device_groups:
            resp = self.api.get(DeviceResolver.DEVICES_URI % device_group)
            ret[device_group] = resp
        return ret

    def setup(self):
        # Added to help narrow down what is happening after HA removal for BZ468263
        peers = set(IPAddress(x.get_discover_address()).format(ipv6_full) for x in self.peers)
        v = self.ifc.version
        if not peers:
            LOG.info("No peers, do nothing.")
            return

        try:
            resp = wait(self.get_devices,
                        condition=lambda ret: peers.intersection(set(y.address
                                                                     for x in ret.values()for y in x['items'])),
                        progress_cb=lambda ret: 'Peer BIGIQs: {0}; Default BIGIQ: {1}'
                            .format(peers, set(y.address for x in ret.values()for y in x['items'])),
                        timeout=60)

            for items in resp.values():
                for item in items['items']:
                    if item.address in peers and v < "bigiq 4.5.0":
                        LOG.warning("Deleting peer BIGIQ as it showed back up per BZ474786")
                        self.api.delete(item.selfLink)
                    elif item.address in peers and v >= "bigiq 4.5.0":
                        raise CommandFail("Peer BIG-IQ showed back up after HA removal (BZ474786).")

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

    def get_task(self):
        """get the payload/uri/method back for sending to another API"""

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

        ret = AttrDict()
        ret["uri"] = EventAggregationTasks.URI
        ret["payload"] = payload
        ret["method"] = "POST"

        return ret

    def setup(self):
        """Adds an aggregation task."""

        ret = self.get_task()
        resp = self.api.post(ret.uri, payload=ret.payload)
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


aggregation_task_stats = None
class AggregationTaskStats(IcontrolRestCommand):  # @IgnorePep8
    """Get stats for Aggregation Tasks via the icontrol rest api

    @param eagt_id: aggregation task id #mandatory
    @type eagt_id: string

    @param expectmincount: can wait for minimum indexed count in stats
    @type expectmincount: int

    @return: the api resp
    @rtype: attr dict json
    """
    def __init__(self, eagt_id, expectmincount=None, delay=None,
                 timeout=45,
                 *args, **kwargs):
        super(AggregationTaskStats, self).__init__(*args, **kwargs)
        if not delay:
            delay = 6
        self.eagt_id = eagt_id
        self.expectmincount = expectmincount
        self.delay = delay
        self.timeout = timeout

    def setup(self):
        """get aggregation task stats."""

        stats = self.api.get(EventAggregationTasks.STATS_ITEM_URI % self.eagt_id)["entries"]

        if self.expectmincount:
            self.wait_for_index_stats(self.expectmincount, self.delay)

        return stats

    def wait_for_index_stats(self, expectmincount, delay=0):

        lookin = "com.f5.rest.workers.analytics.EventAggregationWorker.eventCount"

        def is_stats_there():
            stats = self.api.get(EventAggregationTasks.STATS_ITEM_URI % self.eagt_id)["entries"]
            if stats.get(lookin) and stats.get(lookin).value >= expectmincount:
                LOG.info("/WaitForIndexStats/Received: [{0}]. Expecting at least: {1}"
                         .format(stats.get(lookin).value, expectmincount))
                return True
        wait(is_stats_there,
             progress_cb=lambda x: "Index not ready yet...Expecting: {0}".format(expectmincount),
             timeout=self.timeout, interval=2,
             timeout_message="Index not ready or aggregator stats not there after {0}s. ")
        if delay > 0:
            LOG.info("Sleep another {0} seconds... per dev...".format(delay))
            import time
            time.sleep(delay)
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

    def get_task(self):
        """get the payload/uri/method back for sending to another API"""

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

        ret = AttrDict()
        ret["uri"] = EventAnalysisTasks.URI
        ret["payload"] = payload
        ret["method"] = "POST"
        # print "Payload sent to analysis:"
        # print json.dumps(ret, sort_keys=True, indent=4, ensure_ascii=False)

        return ret

    def setup(self):
        """Adds an analysis task."""

        LOG.debug("Creating Analysis Task for '{0}'...".format(self.aggregationreference))

        task = self.get_task()
        return self.api.post(task.uri, payload=task.payload)


verify_histogram_content = None
class VerifyHistogramContent(IcontrolRestCommand):  # @IgnorePep8
    """Verifies indexed logs via the links provided in a histogram that comes back from analytics

    @param analysis_now:  payload of an analytics task #mandatory
    @type analysis_now: AttrDict()

    @param logsno: number of total items expected in the index
    @type logsno: int

    @param nbins: number of bins expected in the hystogram (default 1)
                 Normally, the number of BQs in the harness or more
    @type nbins: int

    @param terms:  list of logs to check against (optional)
    @type terms: list [of actual logs]

    @return: True if verified or False
    @rtype: bool
    """
    def __init__(self, analysis_now, logsno,
                 nbins=None, terms=None,
                 *args, **kwargs):
        super(VerifyHistogramContent, self).__init__(*args, **kwargs)
        if not nbins:
            nbins = 1
        self.analysis_now = analysis_now
        self.logsno = logsno
        self.nbins = nbins
        self.terms = terms

    def setup(self):
        """Verifies logs against terms from a given analytics with hystogram payload
        Will verify one to one comparison if terms are passed.
        - Takes a full get of an analysis histogram
        - Takes the number of logs to verify (what is known it should be there)
        - Takes number of nbins expected
        - If maxResultCount was in the histogram, then we can expect indexmetadata total no.
        - Takes exact terms for 1 to 1 comparison (skipped if terms is None).
        - Returns True or fails
        """

        LOG.info("Verify sent logs with actual (actual histogram/container(s))...")
        # verify proper count first
        expect_cap = False
        histogram = self.analysis_now.histograms[0]
        assert histogram is not None, "Histogram in Analysis Histogram was found None"
        totalevents = histogram.totalEventCount
        assert totalevents is not None, "totalEventCount in Analysis Histogram was " \
                                        "found None"
        if histogram.maxResultCount and histogram.maxResultCount <= self.logsno:
            expect_cap = True
        if not expect_cap:
            assert self.logsno == totalevents, "Event no total received (histogram.totalEventCount={0}) in " \
                                               "analysis hisogram is not {1}" \
                                               .format(totalevents, self.logsno)
        else:
            assert totalevents == totalevents, "Event no total received ({0}) in " \
                                               "analysis hisogram is not {1}" \
                                               .format(totalevents, self.logsno)

        assert self.nbins == len(histogram.bins), "Nbins received is not same with " \
                                                  "histogram.bins: {0} vs {1}" \
                                                  .format(self.nbins, len(histogram.bins))
        binstotalcountfound = 0
        binstotalresultsfound = []
        totallogs = []
        for abin in histogram.bins:
            binstotalcountfound += abin.updateCount
            if abin.resultReferences:
                binstotalresultsfound += abin.resultReferences
                for containerlink in abin.resultReferences:
                    LOG.debug(":===============================Container Link: {0}"
                              .format(containerlink))
                    aloglist = self.api.get(containerlink.link)['items']  # list of logs
                    for i in aloglist:
                        LOG.debug(i[18:41])
                    totallogs += aloglist
        LOG.info("Calculated log no |updateCount parameter has: {0}".format(binstotalcountfound))
        LOG.info("Calculated log no |from actual containers is: {0}".format(len(totallogs)))
        if not expect_cap:
            assert self.logsno == binstotalcountfound, "Event no total received " \
                                                       "calculated by bin updateCount ({0}) "\
                                                       "in analysis histogram is not {1}"\
                                                       .format(binstotalcountfound, self.logsno)

            assert self.logsno == len(totallogs), "Event no total received calculated by the total actual count of GET on each resultReferences" \
                                                  " ({0}) in analysis histogram is not {1}" \
                                                  .format(len(totallogs), self.logsno)
            LOG.info("Verified received No Of Logs/Expected: {0}/{1}."
                     .format(binstotalcountfound, self.logsno))
        else:
            assert self.logsno <= binstotalcountfound, "Considering cap at {2}. Event no total received calculated by bin updateCount" \
                                                       " ({0}) in analysis histogram is not <= {1}" \
                                                       .format(binstotalcountfound, self.logsno, histogram.maxResultCount)
            assert self.logsno <= len(totallogs), "Considering cap at {2}. Event no total received calculated by the total " \
                                                  "actual count of GET on each resultReferences" \
                                                  " ({0}) in analysis histogram is not <= {1}" \
                                                  .format(len(totallogs), self.logsno, histogram.maxResultCount)
            LOG.info("Verified received No Of Logs/Expected: {0}/{1}. Considering cap at {2}.."
                     .format(binstotalcountfound, self.logsno, histogram.maxResultCount))

        # make sure items in container(s) are the proper ones
        if self.terms:
            LOG.info("1 to 1 comparison from received to what was sent...")

            assert self.assert_proper_logs(terms=self.terms,
                                           loglist=totallogs) is True, "Logs received in analysis histogram do not match logs sent..."

        return True

    def assert_proper_logs(self, terms, loglist):
        """assert for unique terms in received logs
        @param terms: terms to search for
            (must expect to be at beginning of the to be searched string)
        @type terms: list of texts
        @param loglist: list of json items as strings
        @type loglist: list
        """
        assert len(terms) == len(loglist), "Bad Len of terms received to be verified against " \
                                           "item logs. {0} vs {1}".format(len(terms), len(loglist))

        sortedlist = sorted(terms)
        sortedlogs = sorted(loglist)

        for term, item in zip(sortedlist, sortedlogs):
            if term not in item:
                LOG.error("1 on 1: Term {0} not found in Item: {1}".format(term, item))
                LOG.debug("Here is what happened:")
                LOG.debug("List of actual logs[trim] received (not sorted):")
                for i in loglist:
                    LOG.debug(i[18:41])
                LOG.debug("Supposed to compare with [hostname only] (not sorted):")
                for i in terms:
                    LOG.debug(i)
                LOG.debug("List of actual logs[trim] received (sorted):")
                for i in sortedlogs:
                    LOG.debug(i[18:41])
                LOG.debug("Supposed to compare with [hostname only] (sorted):")
                for i in sortedlist:
                    LOG.debug(i)
                LOG.debug("Failed When trying to zip them as follows:")
                for term, item in zip(sortedlist, sortedlogs):
                    LOG.debug(item[18:41])
                    LOG.debug(term)
                LOG.debug("XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")
                return False
        return True

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


wait_analysis_histogram = None
class WaitAnalysisHistogram(IcontrolRestCommand):  # @IgnorePep8
    """Analysis Histograms waits and checks.
    Check an Analysis Histogram state and return the entire get.
    It will fail on "FAILED" state;
    It will expect a FINISHED state by default, for continuous, use "STARTED".
    Can wait for (and expect) specific no of events.

    @param eat_id:  The Analytics Task Item ID (guid) #mandatory
    @type eat_id: string

    Optional params:
    @param expect_state: default "FINISHED", use "STARTED" for Continuous Tasks
    @type expect_state: string

    @param expect_no_of_events: can wait until this number of events is expected
                        (will wait only if the state is not yet FINISHED or FAILED)
    @type expect_no_of_events: int

    @param expect_no_index_meta: can wait until index meta data no reaches this
                        (will wait only if the state is not yet FINISHED or FAILED)
    @type expect_no_index_meta: int

    @param expect_cap: used if the histogram was intended to be capped at less than index;
                          in conjunction with maxResultCount
                        (will wait only if the state is not yet FINISHED or FAILED)
    @type expect_cap: Bool

    @return: the api resp of the entire analytics task
    @rtype: attr dict json
    """

    FAILED_STATES = ["FAILED", "CANCELED"]

    def __init__(self, eat_id,
                 expect_state=None,
                 expect_no_of_events=None,
                 expect_no_index_meta=None,
                 expect_cap=False,
                 timeout=120,
                 *args, **kwargs):
        super(WaitAnalysisHistogram, self).__init__(*args, **kwargs)
        if not expect_state:
            expect_state = "FINISHED"
        if timeout < 5:
            timeout = 5
        self.eat_id = eat_id
        self.expect_state = expect_state
        self.expect_no_of_events = expect_no_of_events
        self.expect_no_index_meta = expect_no_index_meta
        self.expect_cap = expect_cap
        self.timeout = timeout

    def setup(self):

        self.analysis_now = None
        self.status_now = None
        self.totalevents = 0

        def is_histogram_ready_or_is_number_of_events():
            self.is_expected_meta = True
            self.analysis_now = self.api.get(EventAnalysisTasks.ITEM_URI % self.eat_id)
            # import json
            # print json.dumps(self.analysis_now, sort_keys=True, indent=4, ensure_ascii=False)
            self.status_now = self.analysis_now.status
            if self.status_now in WaitAnalysisHistogram.FAILED_STATES:
                return True
            if self.expect_no_of_events or self.expect_no_index_meta:
                try:
                    histogram = self.analysis_now.histograms[0]
                    self.totalevents = histogram.totalEventCount
                    LOG.info("Total Events Now: {0}".format(self.totalevents))
                    if self.expect_no_index_meta:
                        if not self.expect_cap:
                            if (self.analysis_now.indexMetadata.totalEventCount != self.expect_no_index_meta):
                                # and (self.analysis_now.indexMetadata.storageUtilizationInMegaBytes >= 1):
                                self.is_expected_meta = False
                        else:
                            if (self.analysis_now.indexMetadata.totalEventCount < self.expect_no_index_meta):
                                # and (self.analysis_now.indexMetadata.storageUtilizationInMegaBytes >= 1):
                                self.is_expected_meta = False
                except Exception:
                    pass
                if not self.expect_cap:
                    if self.status_now == "FINISHED" and not \
                       (self.totalevents == self.expect_no_of_events and self.is_expected_meta):
                        return True
                    else:
                        return (self.status_now == self.expect_state and
                                self.totalevents == self.expect_no_of_events and
                                self.is_expected_meta)
                # if expecting a cap on logs whitin the histogram vs of what is in index
                else:
                    if self.status_now == "FINISHED" and not \
                       (self.totalevents >= self.expect_no_of_events and self.is_expected_meta):
                        return True
                    else:
                        return (self.status_now == self.expect_state and
                                self.totalevents >= self.expect_no_of_events and
                                self.is_expected_meta)
            return self.status_now == self.expect_state

        wait(is_histogram_ready_or_is_number_of_events,
             progress_cb=lambda x: "Histogram not ready yet: Status:[{0}]; {1}"
             .format(self.status_now,
                     ("Current Count: " + str(self.totalevents) + ".") if self.expect_no_of_events else ""),
             timeout=self.timeout, interval=5,
             timeout_message="Analysis Hystogram not %s or "
                             "number of events%s not there%s. after {0}s. "
                             % (self.expect_state, " " + str(self.expect_no_of_events) if self.expect_no_of_events else "",
                                ". Current Count: " + str(self.totalevents) if self.expect_no_of_events else ""))

        if self.status_now in WaitAnalysisHistogram.FAILED_STATES:
            raise CommandFail("Analysis hystogram returned '{0}' status. Was expecting: '{1}'."
                              .format(self.status_now, self.expect_state))

        if not self.expect_no_of_events:
            self.expect_no_of_events = self.totalevents
        if not self.expect_cap:
            if self.status_now == "FINISHED" and not \
               (self.totalevents == self.expect_no_of_events and self.is_expected_meta):
                raise CommandFail("Analysis hystogram returned 'FINISHED' status, "
                                  "total events were [{0}] vs expected [{1}]; "
                                  "also got: [{2}] for indexMetadata "  # " and [{3}] for storageUtilizationInMegaBytes."
                                  .format(self.totalevents,
                                          self.expect_no_of_events,
                                          self.analysis_now.indexMetadata.totalEventCount,
                                          # self.analysis_now.indexMetadata.storageUtilizationInMegaBytes,
                                          ))
        else:
            if self.status_now == "FINISHED" and not \
               (self.totalevents >= self.expect_no_of_events and self.is_expected_meta):
                raise CommandFail("Analysis hystogram returned 'FINISHED' status, "
                                  "total events were [{0}] vs expected [{1}]; "
                                  "also got: [{2}] for indexMetadata "  # "and [{3}] for storageUtilizationInMegaBytes."
                                  .format(self.totalevents,
                                          self.expect_no_of_events,
                                          self.analysis_now.indexMetadata.totalEventCount,
                                          # self.analysis_now.indexMetadata.storageUtilizationInMegaBytes,
                                          ))
        # special case for a continuous hystogram as we need to wait for
        # resultReferences to get updated (race condition), even if the count is already there
        # import json
        # print json.dumps(self.analysis_now, sort_keys=True, indent=4, ensure_ascii=False)
        if self.status_now == "STARTED" and self.expect_state == "STARTED":
            LOG.info("Detected continuous hystogram, totalcount is as expected, "
                     "determine if there are bins and return... ")

            def wait_for_result_update_container_links():
                self.analysis_now = self.api.get(EventAnalysisTasks.ITEM_URI % self.eat_id)
                # import json
                # print json.dumps(self.analysis_now, sort_keys=True, indent=4, ensure_ascii=False)
                histogram = self.analysis_now.histograms[0]
                self.totalevents = histogram.totalEventCount
                LOG.info("Total Events In Continous H, Now: {0}".format(self.totalevents))
                if self.totalevents != self.expect_no_of_events:
                    LOG.error("Did we hit BZ490459?.. retrying")
                    return False
                if histogram.bins:
                    for abin in histogram.bins:
                        # print abin.updateCount
                        # print abin.resultReferences
                        if abin.updateCount and abin.updateCount > 0 and not abin.resultReferences:
                            return False
                return True
            wait(wait_for_result_update_container_links,
                 progress_cb=lambda x: "Continous task did not refresh containers yet...",
                 timeout=self.timeout, interval=5,
                 timeout_message="BZ490459 - Continous task still returned empty bins after {0}s")

        # import json
        # print json.dumps(self.analysis_now, sort_keys=True, indent=4, ensure_ascii=False)

        return self.analysis_now


wait_rest_ifc = None
class WaitRestIfc(IcontrolRestCommand):  # @IgnorePep8
    """Waits until devices can be reached and are in a group.

    @return: None
    """
    def __init__(self, devices, group=None, timeout=90, *args, **kwargs):
        super(WaitRestIfc, self).__init__(*args, **kwargs)
        self.devices = devices
        if not group:
            group = DEFAULT_ALLBIGIQS_GROUP
        self.group = group
        self.timeout = timeout

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
                 timeout=self.timeout,
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

# Ref - https://confluence.pdsea.f5net.com/display/PDBIGIQPLATFORM/Task+Scheduler#
# Ref - https://confluence.pdsea.f5net.com/display/PDCLOUD/TaskSchedulerAPI
add_task_schedule = None
class AddTaskSchedule(IcontrolRestCommand):  # @IgnorePep8
    """Adds a Schedule via the icontrol rest api
    Example usage:

    @param name: name #mandatory
    @type name: string

    @param type: type #mandatory
    @type type: string

    @param task: mandatory - what task to run in the form:
                 {'method': 'POST', 'uri': '/mgmt/etc', 'payload': {}}
    @type task: AttrDict

    @param specs: Payload Item Specs as a dict
    @type specs: Dict

    @return: the api resp
    @rtype: attr dict json
    """
    def __init__(self, name, stype, task,
                 specs=None,
                 *args, **kwargs):
        super(AddTaskSchedule, self).__init__(*args, **kwargs)
        self.name = name
        self.specs = specs
        self.task = task
        self.stype = stype

    def setup(self):
        """Adds a task schedule."""
        LOG.debug("Creating Task Schedule (Scheduler) '{0}'...".format(self.name))

        payload = TaskScheduler(name=self.name,
                                scheduleType=self.stype)
        if self.task.uri:
            payload.taskReferenceToRun = self.task.uri
        if self.task.payload:
            payload.taskBodyToRun = self.task.payload
        if self.task.method:
            payload.taskRestMethodToRun = self.task.method
        if self.specs:
            for item, value in self.specs.iteritems():
                payload[item] = value

        if self.stype == TaskScheduler.TYPE.BASIC_WITH_INTERVAL:  # @UndefinedVariable
            assert payload.interval
            assert payload.intervalUnit
        elif self.stype == TaskScheduler.TYPE.DAYS_OF_THE_WEEK:  # @UndefinedVariable
            assert payload.intervalUnit
            payload.pop('interval')
            payload.pop('intervalUnit')
        elif self.stype == TaskScheduler.TYPE.DAY_AND_TIME_OF_THE_MONTH:  # @UndefinedVariable
            assert payload.dayOfTheMonthToRunOn >= 0
            assert payload.hourToRunOn >= 0
            assert payload.minuteToRunOn >= 0
            payload.pop('interval')
            payload.pop('intervalUnit')
        elif self.stype == TaskScheduler.TYPE.BASIC_WITH_REPEAT_COUNT:  # @UndefinedVariable
            assert payload.repeatCount
            if payload.intervalUnit != TaskScheduler.UNIT.MILLISECOND:  # @UndefinedVariable
                LOG.warning("Schedule intervalUnit was changed to milliseconds.")
                payload.intervalUnit = TaskScheduler.UNIT.MILLISECOND  # @UndefinedVariable

        # return payload
        # import json
        # print json.dumps(payload, sort_keys=True, indent=4, ensure_ascii=False)

        self.resp = self.api.post(TaskScheduler.URI, payload=payload)

        self.id = self.resp.id

        def for_state():
            self.resp = self.api.get(TaskScheduler.ITEM_URI % self.id)
            self.resp = self.api.get(TaskScheduler.ITEM_URI % self.id)
            if self.resp.status in ["STARTED", "FINISHED", "ENABLED"]:
                return True

        wait(for_state,
             progress_cb=lambda x: "Schedule Task Status Not Started Yet: [{0}]"
             .format(self.resp.status),
             timeout=10,
             timeout_message="Schedule Task is not Started after {0}s")

        return self.resp


wait_schedule_history = None
class WaitScheduleHistory(IcontrolRestCommand):  # @IgnorePep8
    """Scheduler wait for history.
    Check a Schedule History and State.

    It will expect an ENABLED state by default
    Can wait for (and expect) specific no history items.

    @param s_id:  The Schedule ID (guid) #mandatory
    @type s_id: string

    Optional params:
    @param no: expect this exact number of history items before exit (default 1)
    @type no: int

    @param expect: default "ENABLED", expected state of the schedule
    @type expect: string

    @param account_for_false_runs: Default False. Will count history missfires if True
    @type account_for_false_runs: Bool

    @param interval: wait function interval in s
    @type interval: int
    @param timeout: wait function timeout in s
    @type timeout: int

    """

    # FAILED_STATES = ["FAILED", "CANCELED"]

    def __init__(self, s_id, no=1, expect='ENABLED',
                 account_for_false_runs=False,
                 interval=2,
                 timeout=20,
                 *args, **kwargs):
        super(WaitScheduleHistory, self).__init__(*args, **kwargs)
        self.s_id = s_id
        self.no = no
        self.expect = expect
        self.account_for_false_runs = account_for_false_runs
        self.interval = interval
        self.timeout = timeout

    def setup(self):

        def is_task_history(no, expect, account_for_false_runs):
            self.goodhistory = []
            # Debug:
            # import f5test.commands.shell as SCMD
            # nowu = str(SCMD.ssh.generic('date -u +"%Y-%m-%dT%H:%M:%S.%3N%z"').stdout).rstrip()
            # nowl = str(SCMD.ssh.generic('date +"%Y-%m-%dT%H:%M:%S.%3N%z"').stdout).rstrip()
            # LOG.info("Date now: [{0} | {1}]".format(nowu, nowl))

            schedule_resp = self.api.get(TaskScheduler.ITEM_URI % self.s_id)
            # print json.dumps(schedule_resp, sort_keys=True, indent=4, ensure_ascii=False)
            historynow = schedule_resp.taskHistory
            if historynow:
                LOG.info("Total Tasks Detected Now: [{0}].".format(len(historynow)))
                if schedule_resp.status == expect:
                    if not account_for_false_runs:
                        for z in historynow:
                            if z.wasSuccesfulRun:
                                self.goodhistory.append(z)
                    else:
                        self.goodhistory = historynow
                    return self.goodhistory
        wait_args(is_task_history, [self.no, self.expect, self.account_for_false_runs],
                  condition=lambda goodhistory: len(goodhistory) == self.no,
                  progress_cb=lambda x: "History [count/status: [{0}] vs. "
                  "expected [{1}/{2}]...Retry.."
                  .format(len(x) if x else "?/Not {0}".format(self.expect), self.no, self.expect),
                  timeout=self.timeout, interval=self.interval,
                  timeout_message="History count received was not [%s] or status not [%s], after {0}s." % (str(self.no), self.expect))
