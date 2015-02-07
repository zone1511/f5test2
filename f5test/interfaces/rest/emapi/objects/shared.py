'''
Created on Jan 9, 2014

/mgmt/[cm|tm]/shared and /mgmt/shared workers

@author: jono
'''
from .....base import enum, AttrDict
from .....defaults import ADMIN_USERNAME, ADMIN_PASSWORD
from .base import Reference, ReferenceList, Task, TaskError, DEFAULT_TIMEOUT
from ...base import BaseApiObject
from .....utils.wait import wait
import json


class UserCredentialData(BaseApiObject):
    URI = '/mgmt/shared/authz/users'
    ITEM_URI = '/mgmt/shared/authz/users/%s'

    def __init__(self, *args, **kwargs):
        super(UserCredentialData, self).__init__(*args, **kwargs)
        self.setdefault('name', 'NewTenant')
        self.setdefault('password', '')


class License(AttrDict):
    ACTIVATION_URI = '/mgmt/tm/shared/licensing/activation'
    URI = '/mgmt/tm/shared/licensing/registration'
    WAITING_STATE = 'LICENSING_ACTIVATION_IN_PROGRESS'
    FAIL_STATE = 'LICENSING_FAILED'

    def __init__(self, *args, **kwargs):
        super(License, self).__init__(*args, **kwargs)
        self.setdefault('baseRegKey', '')
        self.setdefault('addOnKeys', [])
        self.setdefault('isAutomaticActivation', 'true')

    @staticmethod
    def wait(rest, timeout=DEFAULT_TIMEOUT):

        ret = wait(lambda: rest.get(License.ACTIVATION_URI), timeout=timeout, interval=1,
                   condition=lambda ret: not ret.status in License.WAITING_STATE,
                   progress_cb=lambda ret: 'Status: {0}'.format(ret.status))

        if ret.status in License.FAIL_STATE:
            msg = json.dumps(ret, sort_keys=True, indent=4, ensure_ascii=False)
            raise TaskError("Licensing failed.\n%s" % msg)

        return ret


# Ref-https://peterpan.f5net.com/twiki/bin/view/Cloud/DiscoveryConfigDesign
class NetworkDiscover(BaseApiObject):
    URI = '/mgmt/shared/identified-devices/config/discovery'

    def __init__(self, *args, **kwargs):
        super(NetworkDiscover, self).__init__(*args, **kwargs)
        self.setdefault('discoveryAddress', '')
        self.setdefault('validateOnly', False)


class UserRoles(BaseApiObject):
    URI = '/mgmt/shared/authz/roles/%s'  # keep for backwards compatible
    ITEM_URI = '/mgmt/shared/authz/roles/%s'
    ONLYURI = '/mgmt/shared/authz/roles'
    TYPES = enum(ADMIN='Administrator',
                 SECURITY='Security_Manager',
                 CLOUD='CloudTenantAdministrator_%s',
                 FIREWALL='Firewall_Manager')

    def __init__(self, *args, **kwargs):
        super(UserRoles, self).__init__(*args, **kwargs)
        self.setdefault('name', UserRoles.TYPES.ADMIN)
        self.setdefault('userReferences', ReferenceList())
        self.setdefault('resources', [])

# A wait method to check if the given role is removed on the user
    @staticmethod
    def wait_removed(restapi, userselflink, timeout=DEFAULT_TIMEOUT):  # @UndefinedVariable

        ret = wait(lambda: restapi.get(UserRoles.ONLYURI)['items'], timeout=timeout, interval=1,
                   condition=lambda ret: userselflink not in [x.link for x in ret],
                   progress_cb=lambda __: "Waiting until user role is deleted")

        return userselflink not in [x.link for x in ret]


# Ref: https://indexing.f5net.com/source/xref/management-adc/tm_daemon/msgbusd/java/src/com/f5/rest/workers/GossipWorkerState.java
class GossipWorkerState(BaseApiObject):
    URI = '/mgmt/shared/gossip'

    def __init__(self, *args, **kwargs):
        super(GossipWorkerState, self).__init__(*args, **kwargs)
        self.setdefault('pollingIntervalMicrosCount')
        self.setdefault('updateThresholdPerMicrosCount')
        self.setdefault('workerUpdateProcessingIntervalMicrosCount')
        self.setdefault('workerUpdateDelayMicrosCount')
        self.setdefault('workerStateInfoMap', {})
        self.setdefault('gossipPeerGroup')
        self.setdefault('isLocalUpdate', False)


class DeviceResolver(BaseApiObject):
    URI = '/mgmt/shared/resolver/device-groups'
    ITEM_URI = '%s/%%s' % URI
    DEVICES_URI = '%s/%%s/devices' % URI
    DEVICE_URI = '%s/%%s' % DEVICES_URI
    STATS_URI = '%s/%%s/stats' % URI
    DEVICE_STATS_URI = '%s/stats' % DEVICE_URI
    PENDING_STATES = ('PENDING', 'PENDING_DELETE',
                      'FRAMEWORK_DEPLOYMENT_PENDING', 'TRUST_PENDING',
                      'CERTIFICATE_INSTALL')

    def __init__(self, *args, **kwargs):
        super(DeviceResolver, self).__init__(*args, **kwargs)
        self.setdefault('address', '')
        self.setdefault('userName', ADMIN_USERNAME)
        self.setdefault('password', ADMIN_PASSWORD)
        self.setdefault('properties', AttrDict())
        self.setdefault('deviceReference', Reference())
#         self.setdefault('parentGroupReference', Reference())  # BZ474699

    @staticmethod
    def wait(rest, group, timeout=120, count=None):

        def get_status():
            return rest.get(DeviceResolver.DEVICES_URI % group)

        def all_done(ret):
            return sum(x.state not in DeviceResolver.PENDING_STATES
                       for x in ret['items']) == (sum(1 for x in ret['items']) if count is None else count)

        ret = wait(get_status, timeout=timeout,
                   condition=all_done,
                   progress_cb=lambda ret: 'Status: {0}'.format(list(x.state for x in ret['items'])))

        if sum(1 for x in ret['items']) != \
           sum(x.state == 'ACTIVE' for x in ret['items']):
            msg = json.dumps(ret, sort_keys=True, indent=4, ensure_ascii=False)
            raise TaskError("At least one subtask is not completed:\n%s" % msg)
        return ret


class DeviceResolverGroup(BaseApiObject):
    URI = DeviceResolver.URI + '/%s'


class DeviceResolverDevice(BaseApiObject):
    URI = DeviceResolver.DEVICES_URI + '/%s'

    def __init__(self, *args, **kwargs):
        super(DeviceResolverDevice, self).__init__(*args, **kwargs)
        self.setdefault('userName', ADMIN_USERNAME)
        self.setdefault('password', ADMIN_PASSWORD)
        self.setdefault('uuid')
        self.setdefault('state', 'ACTIVE')


class DeviceGroup(BaseApiObject):
    URI = '/mgmt/shared/resolver/device-groups'
    ITEM_URI = '{0}/%s'.format(URI)
    DEVICES_URI = '{0}/%s/devices'.format(URI)

    def __init__(self, *args, **kwargs):
        super(DeviceGroup, self).__init__(*args, **kwargs)
        self.setdefault('kind', 'shared:resolver:device-groups:devicegroupstate')
        self.setdefault('infrastructure', False)
        self.setdefault('description', 'Just a Test Group')
        self.setdefault('isViewGroup', False)
        self.setdefault('groupName', 'test-group')
        self.setdefault('autoManageLocalhost', True)


class DeviceInfo(BaseApiObject):
    URI = '/mgmt/shared/identified-devices/config/device-info'

    def __init__(self, *args, **kwargs):
        super(DeviceInfo, self).__init__(*args, **kwargs)


class HAPeerRemover(BaseApiObject):
    URI = '/mgmt/cm/shared/ha-peer-remover'

    def __init__(self, *args, **kwargs):
        super(HAPeerRemover, self).__init__(*args, **kwargs)
        self.setdefault('peerReference', Reference())


class Echo(BaseApiObject):
    URI = '/mgmt/shared/echo'


class FailoverState(BaseApiObject):
    URI = '/mgmt/shared/failover-state'
    PENDING_STATES = ('UNKNOWN', 'UNINITIALIZED', 'SYNCHRONIZING')
    KNOWN_STATES = ('ACTIVE', 'STANDBY', 'DOWN')

    def __init__(self, *args, **kwargs):
        super(FailoverState, self).__init__(*args, **kwargs)
        self.setdefault('isPrimary', True)

    @staticmethod
    def wait(rest, timeout=DEFAULT_TIMEOUT):

        def get_status():
            return rest.get(FailoverState.URI)

        def all_done(ret):
            return not ret.failoverState in FailoverState.PENDING_STATES \
                and not ret.peerFailoverState in FailoverState.PENDING_STATES

        ret = wait(get_status, timeout=timeout, interval=1,
                   condition=all_done,
                   progress_cb=lambda _: 'Waiting until faioverState complete...')
        return ret


class SnapshotClient(BaseApiObject):
    URI = '/mgmt/shared/storage/snapshot-client'
    SNAPSHOT_LOCATION = '/var/config/rest/active-storage.zip'

    def __init__(self, *args, **kwargs):
        super(SnapshotClient, self).__init__(*args, **kwargs)
        self.setdefault("snapshotFile", "")


# Ref- https://peterpan.f5net.com/twiki/bin/view/Cloud/CMLicensePoolAPI
class LicensePool(BaseApiObject):
    POOLS_URI = '/mgmt/cm/shared/licensing/pools'
    POOL_URI = '/mgmt/cm/shared/licensing/pools/%s'
    POOL_MEMBERS_URI = '/mgmt/cm/shared/licensing/pools/%s/members'
    POOL_MEMBER_URI = '/mgmt/cm/shared/licensing/pools/%s/members/%s'
    WAITING_STATE = 'WAITING_FOR_EULA_ACCEPTANCE'
    WAITING_STATE_MANUAL = 'WAITING_FOR_LICENSE_TEXT'
    FAIL_STATE = 'FAILED'
    LICENSE_STATE = 'LICENSED'

    def __init__(self, *args, **kwargs):
        super(LicensePool, self).__init__(*args, **kwargs)
        self.setdefault('name', '')
        self.setdefault('baseRegKey', '')
        self.setdefault('addOnKeys', [])
        self.setdefault('eulaText', '')
        self.setdefault('state', '')
        self.setdefault('licenseText', '')
        self.setdefault('method', '')
        self.setdefault("deviceReference", Reference())
        self.setdefault("deviceGroupReference", Reference())

    @staticmethod
    def wait(rest, pool, automatic, timeout=10):

        states = (LicensePool.WAITING_STATE, LicensePool.LICENSE_STATE) if automatic \
            else (LicensePool.WAITING_STATE_MANUAL, LicensePool.LICENSE_STATE)

        ret = wait(lambda: rest.get(pool.selfLink),
               condition=lambda x: x.state in states,
               progress_cb=lambda x: 'State: {0} '.format(x.state), timeout=timeout, interval=1)

        if ret.state in LicensePool.FAIL_STATE:
            msg = json.dumps(ret.state, sort_keys=True, indent=4, ensure_ascii=False)
            raise TaskError("Licensing failed.\n%s" % msg)

        return ret


# Ref- https://peterpan.f5net.com/twiki/bin/view/Cloud/DeviceInventoryWorker
class DeviceInventory(BaseApiObject):
    URI = '/mgmt/cm/shared/device-inventory'
    FINISH_STATE = 'FINISHED'
    FAIL_STATE = 'FAILED'

    def __init__(self, *args, **kwargs):
        super(DeviceInventory, self).__init__(*args, **kwargs)
        self.setdefault('devicesQueryUri', '')

    @staticmethod
    def wait(rest, identifier, timeout=10):

        ret = wait(lambda: rest.get(DeviceInventory.URI + '/' + identifier),
               condition=lambda x: x.status == DeviceInventory.FINISH_STATE,
               progress_cb=lambda x: 'State: {0} '.format(x.status), timeout=timeout, interval=1)
        if ret.status == DeviceInventory.FAIL_STATE:
            msg = json.dumps(ret.state, sort_keys=True, indent=4, ensure_ascii=False)
            raise TaskError("Post Failed to get Device ID\n%s" % msg)

        return ret


# Ref - https://peterpan.f5net.com/twiki/bin/view/Cloud/CMLicenseRegistrationKeysAPI
class LicenseRegistrationKey(BaseApiObject):
    URI = '/mgmt/cm/shared/licensing/registrations'
    ITEM_URI = '/mgmt/cm/shared/licensing/registrations/%s'

    def __init__(self, *args, **kwargs):
        super(LicenseRegistrationKey, self).__init__(*args, **kwargs)
        self.setdefault('registrationKey', '')


# Ref - https://peterpan.f5net.com/twiki/bin/view/Cloud/AnalyticsDesign
# Ref - https://peterpan.f5net.com/twiki/bin/view/Cloud/EventAnalyticsAPI
class EventAggregationTasks(BaseApiObject):
    """To be used on each BQ to create a listening task"""
    URI = '/mgmt/shared/analytics/event-aggregation-tasks'
    ITEM_URI = '/mgmt/shared/analytics/event-aggregation-tasks/%s'
    STATS_ITEM_URI = '/mgmt/shared/analytics/event-aggregation-tasks/%s/worker/stats'
    PORT = 9010  # some default test port

    def __init__(self, *args, **kwargs):
        super(EventAggregationTasks, self).__init__(*args, **kwargs)
        self.setdefault('sysLogConfig',
                        AttrDict(tcpListenEndpoint='http://localhost:{0}'.format(self.PORT),
                                 isRfc5424=False,  # not to use rfc5424
                                 # rfc5424MsgParserConfig=AttrDict(sessionId='^.*:',
                                 #                                deviceId='\\\\[.*\\\\]'),
                                 # startPrefix='ASM:',
                                 # multiValueFieldNames=["violations",
                                 #                      "ip_list",
                                 #                      "sub_violations",
                                 #                      "url_list",
                                 #                      "attack_type",
                                 #                      "sig_ids"]
                                 ))
        self.setdefault('eventSourcePollingIntervalMillis', 1000)
        self.setdefault('itemCountCommitThreshold', 100)
        self.setdefault('isIndexingRequired', True)
        self.setdefault('name', 'test-aggregation-task01')
        self.setdefault('kind', 'shared:analytics:event-aggregation-tasks:eventaggregationstate')
        self.setdefault('description', 'Test.EAT')
        # self.setdefault('generation', 0)
        # self.setdefault('lastUpdateMicros', 0)
        # self.setdefault('expirationMicros', 1400194354500748)


# Ref - https://peterpan.f5net.com/twiki/bin/view/Cloud/AnalyticsDesign
# Ref - https://peterpan.f5net.com/twiki/bin/view/Cloud/EventAnalyticsAPI
class EventAnalysisTasks(BaseApiObject):
    """To be used on default (main) BQ to create an analysis task"""
    URI = '/mgmt/shared/analytics/event-analysis-tasks'
    ITEM_URI = '/mgmt/shared/analytics/event-analysis-tasks/%s'

    def __init__(self, *args, **kwargs):
        super(EventAnalysisTasks, self).__init__(*args, **kwargs)

        self.setdefault('collectFilteredEvents', False)
#         multitier = False
#         if not multitier:
#             self.setdefault('eventAggregationReference', Link())
#         else:
#             self.setdefault('multiTierConfig',
#                             AttrDict(deviceGroupReference=Link(),
#                                      eventAggregationTaskFilter="description eq '*'",
#                                      completionCheckIntervalSeconds=2))
        self.setdefault('histograms',
                        [
                        AttrDict(# sourceEventProperty='hostname',  # MANDATORY
                                 sourceEventProperty='unit_hostname',  # MANDATORY
                                 # durationTimeUnit='MINUTES',  # MANDATORY
                                 durationTimeUnit='SECONDS',  # MANDATORY
                                 # durationTimeUnit='HOURS',  # MANDATORY
                                 durationLength=240,  # MANDATORY
                                 nBins=1,  # MANDATORY
                                 # mode='SUM',
                                 selectionQueryType='ODATA',  # MANDATORY
                                 orderByEventProperty="management_ip_address",
                                 # eventFilter="hostname eq 'x.f5net.com'",
                                 # eventFilter="management_ip_address eq '172.27.91.0'",
                                 eventFilter="unit_hostname eq '*'",
                                 # eventFilter="hostname eq '*'",
                                 timestampEventProperty='eventConversionDateTime',
                                 # description='0c46b474-ab36-4b50-8cf0-710609af734f',
                                 timeUpperBoundMicrosUtc=1400181224388389,  # MANDATORY if isRelativeToNow is False
                                 isRelativeToNow=False,  # if False, strictly tight to timeUpperBoundMicrosUtc
                                 # sourceEventProperty="aCounter",
                                 # totalEventCount=0,
                                 )
                        ]
                        )
    # RETURN SHOULD HAVE A BIN:
    # {'status': 'FINISHED',
    # 'collectFilteredEvents': False,
    # 'kind': 'shared:analytics:event-analysis-tasks:eventanalysistaskstate',
    # 'userReference': {'link': 'https://localhost/mgmt/shared/authz/users/admin'},
    # 'generation': 2,
    # 'histograms': [
    #                {'nBins': 1,
    #                 'selectionQueryType': 'ODATA',
    #                 'eventFilter': "hostname eq 'spinner9mgmt.lab.fp.f5net.com'",
    #                 'isRelativeToNow': False,
    #                 'generation': 0,
    #                 'sourceEventProperty': 'hostname',
    #                 'durationLength': 240,
    #                 'timestampEventProperty': 'eventConversionDateTime',
    #                 'durationTimeUnit': 'SECONDS',
    #                 'mode': 'SUM',
    #                 'totalEventCount': 0,
    #                 'timeUpperBoundMicrosUtc': 1400181224388389,
    #                 'lastUpdateMicros': 0,
    #                 'id': '45ce284d-5d45-470e-99cc-6671b5a0f5a5',
    #                 'bins': [{'upperBoundMicrosUtc': 1400181359999999, 'currentValue': 0.0, 'lastUpdateTimeMicrosUtc': 0, 'lowerBoundMicrosUtc': 1400181120000000, 'updateCount': 0, 'totalValue': 0.0}], 'description': '0c46b474-ab36-4b50-8cf0-710609af734f'}],
    #                 'eventAggregationReference': {'link': 'https://localhost/mgmt/shared/analytics/event-aggregation-tasks/03ed222d-1207-4429-a450-dcfa2beec701/worker'},
    #                 'lastUpdateMicros': 1400181900656919,
    #                 'id': '1b2833a9-05a4-4ab8-989a-d8b6ce626db8',
    #                 'selfLink': 'https://localhost/mgmt/shared/analytics/event-analysis-tasks/1b2833a9-05a4-4ab8-989a-d8b6ce626db8'}


# Ref- https://peterpan.f5net.com/twiki/bin/view/Cloud/CMAPICLPv2Collection
class UtilityLicense(BaseApiObject):
    URI = '/mgmt/cm/system/licensing/utility-licenses'
    ITEM_URI = '/mgmt/cm/system/licensing/utility-licenses/%s'

    AUTOMATIC_ACTIVATION_STATES = enum('ACTIVATING_AUTOMATIC', 'ACTIVATING_AUTOMATIC_EULA_ACCEPTED')

    MANUAL_ACTIVATION_STATES = enum('ACTIVATING_MANUAL', 'ACTIVATING_MANUAL_LICENSE_TEXT_PROVIDED',
                                    'ACTIVATING_MANUAL_OFFERINGS_LICENSE_TEXT_PROVIDED')

    WAITING_STATES = ['ACTIVATING_AUTOMATIC_NEED_EULA_ACCEPT', 'ACTIVATING_AUTOMATIC_OFFERINGS',
                      'ACTIVATING_MANUAL_NEED_LICENSE_TEXT', 'ACTIVATING_MANUAL_OFFERINGS_NEED_LICENSE_TEXT']

    FAILED_STATES = ['ACTIVATION_FAILED_OFFERING', 'ACTIVATION_FAILED']

    SUCCESS_STATE = ['READY']

    def __init__(self, *args, **kwargs):
        super(UtilityLicense, self).__init__(*args, **kwargs)
        self.setdefault('regKey', '')
        self.setdefault('addOnKeys', [])
        self.setdefault('name', '')
        self.setdefault('status', '')
        self.setdefault('licenseText', '')
        self.setdefault('eulaText', '')
        self.setdefault('dossier', '')

    @staticmethod
    def wait(rest, uri, wait_for_status, timeout=30, interval=1):

        resp = wait(lambda: rest.get(uri), condition=lambda temp: temp.status in wait_for_status,
                    progress_cb=lambda temp: 'Status: {0}, Message: {1}' .format(temp.status, temp.message), timeout=timeout, interval=interval)

        return resp


# Ref- https://peterpan.f5net.com/twiki/bin/view/Cloud/CMAPICLPv2OfferingsCollection
class OfferingsCollection(BaseApiObject):
    URI = '/mgmt/cm/system/licensing/utility-licenses/%s/offerings'
    OFFERING_URI = '/mgmt/cm/system/licensing/utility-licenses/%s/offerings/%s'

    def __init__(self, *args, **kwargs):
        super(OfferingsCollection, self).__init__(*args, **kwargs)
        self.setdefault('status', '')
        self.setdefault('licenseText', '')


# Ref- https://peterpan.f5net.com/twiki/bin/view/Cloud/CMAPICLPv2OfferingsMembersCollection
class MembersCollection(BaseApiObject):
    URI = '/mgmt/cm/system/licensing/utility-licenses/%s/offerings/%s/members'
    MEMBER_URI = '/mgmt/cm/system/licensing/utility-licenses/%s/offerings/%s/members/%s'

    UNIT_OF_MEASURE = enum('hourly', 'daily', 'monthly', 'yearly')

    WAITING_STATE = 'INSTALLING'
    FAILED_STATE = 'INSTALLATION_FAILED'
    SUCCESS_STATE = 'LICENSED'

    def __init__(self, *args, **kwargs):
        super(MembersCollection, self).__init__(*args, **kwargs)
        self.setdefault('unitOfMeasure', '')
        self.setdefault('deviceMachineId', '')

    @staticmethod
    def wait(rest, uri, wait_for_status, timeout=30, interval=1):

        resp = wait(lambda: rest.get(uri), condition=lambda temp: temp.status == wait_for_status,
                    progress_cb=lambda temp: 'Status: {0}, Message: {1}' .format(temp.status, temp.message), timeout=timeout, interval=interval)

        return resp


# Ref - https://peterpan.f5net.com/twiki/bin/view/Cloud/CMAPICLPv2LicenseReportWorker
class ReportWorker(BaseApiObject):
    URI = '/mgmt/cm/system/licensing/utility-license-reports'
    ITEM_URI = '/mgmt/cm/system/licensing/utility-license-reports/%s'

    REPORT_TYPE = enum('JSON', 'CSV')

    WAITING_STATE = 'STARTED'
    SUCCESS_STATE = 'FINISHED'

    def __init__(self, *args, **kwargs):
        super(ReportWorker, self).__init__(*args, **kwargs)
        self.setdefault('regKey', '')
        self.setdefault('offering', '')
        self.setdefault('reportStartDateTime', '')
        self.setdefault('reportEndDateTime', '')
        self.setdefault('reportType', ReportWorker.REPORT_TYPE.JSON)

    @staticmethod
    def wait(rest, uri, timeout=30):

        resp = wait(lambda: rest.get(uri), condition=lambda temp: temp.status == ReportWorker.SUCCESS_STATE,
                    progress_cb=lambda temp: 'Status: {0}' .format(temp.status), timeout=timeout)

        return resp


# Ref - https://peterpan.f5net.com/twiki/bin/view/Cloud/CMAPICLPv2LicenseAuditWorker
class AuditWorker(BaseApiObject):
    URI = '/mgmt/cm/system/licensing/audit'
    ITEM_URI = '/mgmt/cm/system/licensing/audit/%s'

    STATUS = enum('GRANTED', 'REVOKED')


# Ref - https://peterpan.f5net.com/twiki/bin/view/Cloud/AuthZRolesResourceGroupsAPI
class ResourceGroup(BaseApiObject):
    URI = '/mgmt/shared/authz/resource-groups'
    ITEM_URI = '%s/%%s' % URI

    def __init__(self, *args, **kwargs):
        super(ResourceGroup, self).__init__(*args, **kwargs)
        self.setdefault('name', '')
        self.setdefault('resources', [])


# Ref - https://peterpan.f5net.com/twiki/bin/view/Cloud/RemoteResourcesAPI
class RemoteResource(BaseApiObject):
    URI = '/mgmt/shared/authz/remote-resources'
    ITEM_URI = '%s/%%s' % URI

    def __init__(self, *args, **kwargs):
        super(RemoteResource, self).__init__(*args, **kwargs)
        self.setdefault('roleReference', Reference())
        self.setdefault('deviceGroupReferences', ReferenceList())
        self.setdefault('resourceGroupReferences', ReferenceList())


# Ref - https://peterpan.f5net.com/twiki/bin/view/MgmtProducts/Device3175
class RbacHelper(BaseApiObject):
    URI = '/mgmt/cm/system/rbac-helper'
    ROLE_TYPE = enum('READONLY', 'EDITOR')

    def __init__(self, *args, **kwargs):
        super(RbacHelper, self).__init__(*args, **kwargs)
        self.setdefault('name', '')
        self.setdefault('description', '')
        self.setdefault('roleType', RbacHelper.ROLE_TYPE.READONLY)
        self.setdefault('deviceGroupReference', Reference())


class AuthnLocalGroups(BaseApiObject):
    URI = '/mgmt/shared/authn/providers/local/groups'

    def __init__(self, *args, **kwargs):
        super(AuthnLocalGroups, self).__init__(*args, **kwargs)
        self.setdefault('name', '')


# Ref - https://confluence.pdsea.f5net.com/display/PDCLOUD/RestDiagnosticsWorkerAPI
class DiagnosticsRuntime(BaseApiObject):
    URI = '/mgmt/shared/diagnostics/runtime'


# Ref - https://confluence.pdsea.f5net.com/display/PDBIGIQPLATFORM/Task+Scheduler#
# Ref - https://confluence.pdsea.f5net.com/display/PDCLOUD/TaskSchedulerAPI
class TaskScheduler(BaseApiObject):
    """defauults on the Task Schedule Payload"""
    URI = '/mgmt/shared/task-scheduler/scheduler'
    ITEM_URI = '/mgmt/shared/task-scheduler/scheduler/%s'

    TYPE = enum('BASIC_WITH_INTERVAL',
                'DAYS_OF_THE_WEEK',
                'DAY_AND_TIME_OF_THE_MONTH',
                'BASIC_WITH_REPEAT_COUNT')
    UNIT = enum('MILLISECOND', 'SECOND', 'MINUTE', 'HOUR',
                'DAY', 'WEEK', 'MONTH', 'YEAR')

    def __init__(self, *args, **kwargs):
        super(TaskScheduler, self).__init__(*args, **kwargs)

        # "kind": "shared:task-scheduler:scheduler:schedulerworkerstate",
        # "selfLink": "http://localhost:36160/shared/task-scheduler/scheduler/8e2095e9-ffee-4b8e-9de4-d7be0c85154f/worker"

        # Good Optionals:
        self.setdefault('name', "test-schedule-01")
        self.setdefault('description', "description for this task - test")
        # Type BASIC
        self.setdefault('scheduleType', TaskScheduler.TYPE.BASIC_WITH_INTERVAL)
        self.setdefault('interval', 30)
        self.setdefault('intervalUnit', TaskScheduler.UNIT.SECOND)

        # Type Weekly
        # self.setdefault('scheduleType', TaskScheduler.TYPE.DAYS_OF_THE_WEEK)
        # self.setdefault('daysOfTheWeekToRun', (1, 2, 3, 4, 5))  # 1-7 (type {} set)
        # self.setdefault('timeToStartOn', "2014-09-18T11:30:00-07:00")

        # Type Monthly
        # self.setdefault('scheduleType', TaskScheduler.TYPE.DAY_AND_TIME_OF_THE_MONTH)
        # self.setdefault('dayOfTheMonthToRun', 25)
        # self.setdefault('hourToRunOn', 15)
        # self.setdefault('minuteToRunOn', 30)

        # Type Basic with repeat
        # self.setdefault('scheduleType', TaskScheduler.TYPE.BASIC_WITH_REPEAT_COUNT)
        # self.setdefault('repeatCount', 0)  # run only once

        # Other Required
        self.setdefault('deviceGroupName', 'cm-shared-all-big-iqs')
        self.setdefault('taskReferenceToRun', '')  # URI to be run on this S
        self.setdefault('taskBodyToRun', {})  # State Object (Eg: EventAnalyticsTaskState)
        self.setdefault('taskRestMethodToRun', 'GET')

        # Optionals
        self.setdefault('endDate', None)  # date
        self.setdefault('timeoutInMillis', 60000)  # wait for completion of task; Default from api is 60s
        # self.setdefault('whenScheduleMisfiresTryAndRerun', False)  # default True

        # Returns:
        # self.setdefault('taskHistory', ReferenceList())
        # self.setdefault('nextRunTime', '')


class AvrTask(Task):

    def wait_analysis(self, rest, resource, loop=None, timeout=30, interval=1,
             timeout_message=None):
        def get_status():
            return rest.get(resource.selfLink)
        if loop is None:
            loop = get_status
        ret = wait(loop, timeout=timeout, interval=interval,
                   timeout_message=timeout_message,
                   condition=lambda x: x.status not in ('STARTED',),
                   progress_cb=lambda x: 'Status: {0}'.format(x.status))
        assert ret.status == 'FINISHED', "{0.status}:{0.error}".format(ret)
        return ret


# Ref - https://confluence.pdsea.f5net.com/display/PDCLOUD/AnalyticsDesign
class AvrAggregationTasks(BaseApiObject):
# avrAggregationTask is a singleton created by restjavad. It's created at startup and no need to delete it
    URI = "/mgmt/shared/analytics/avr-aggregation-tasks"
    ITEM_URI = "/mgmt/shared/analytics/avr-aggregation-tasks/%s"

    def __init__(self, *args, **kwargs):
        super(AvrAggregationTasks, self).__init__(*args, **kwargs)


class GroupTask(Task):
    URI = "/mgmt/shared/group-task"

    def __init__(self, *args, **kwargs):
        super(GroupTask, self).__init__(*args, **kwargs)
        self.setdefault('devicesReference', Reference())
        self.setdefault('taskReference', Reference())
        self.setdefault('taskBody', {})

class WorkingLtmNode(BaseApiObject):
    URI = '/mgmt/cm/shared/config/working/ltm/node'

    def __init__(self, *args, **kwargs):
        super(WorkingLtmNode, self).__init__(*args, **kwargs)
        self.setdefault('name', '')
        self.setdefault('address', '')
        self.setdefault('fullPath', '')
        self.setdefault('partition', '')
        self.setdefault('deviceReference', Reference())
        self.setdefault('monitor', '/Common/icmp')

class WorkingLtmPool(BaseApiObject):
    URI = '/mgmt/cm/shared/config/working/ltm/pool'

    def __init__(self, *args, **kwargs):
        super(WorkingLtmPool, self).__init__(*args, **kwargs)
        self.setdefault('name', '')
        self.setdefault('fullPath', '')
        self.setdefault('partition', '')
        self.setdefault('deviceReference', Reference())
        self.setdefault('monitor', '/Common/http')

class WorkingLtmPoolMember(BaseApiObject):
    URI = '/mgmt/cm/shared/config/working/ltm/pool/%s/members'

    def __init__(self, *args, **kwargs):
        super(WorkingLtmPoolMember, self).__init__(*args, **kwargs)
        self.setdefault('name', '')
        self.setdefault('address', '')
        self.setdefault('fullPath', '')
        self.setdefault('partition', '')
        self.setdefault('deviceReference', Reference())
        self.setdefault('nodeReference', Reference())
        self.setdefault('monitor', 'default')

class SourceAddressTranslation(AttrDict):
    def __init__(self, *args, **kwargs):
        super(SourceAddressTranslation, self).__init__(*args, **kwargs)
        self.setdefault('type', 'automap')

class WorkingLtmVip(BaseApiObject):
    URI = '/mgmt/cm/shared/config/working/ltm/virtual'

    def __init__(self, *args, **kwargs):
        super(WorkingLtmVip, self).__init__(*args, **kwargs)
        self.setdefault('name', '')
        self.setdefault('destination', '')
        self.setdefault('fullPath', '')
        self.setdefault('partition', '')
        self.setdefault('deviceReference', Reference())
        self.setdefault('poolReference', Reference())
        self.setdefault('pool', '')
        self.setdefault('disabled', False)
        self.setdefault('enabled', True)
        self.setdefault('translateAddress', 'enabled')
        self.setdefault('translatePort', 'enabled')
        self.setdefault('sourceAddressTranslation', SourceAddressTranslation())

class SnapshotTask(Task):
    URI = "/mgmt/shared/snapshot-task"

    def __init__(self, *args, **kwargs):
        super(SnapshotTask, self).__init__(*args, **kwargs)
        self.setdefault('name', '')
        self.setdefault('collectionReferences', ReferenceList())

class ConfigDeploy(Task):
    """ This can be used to do ADC deployment """
    URI = '/mgmt/cm/shared/config/deploy'

    def __init__(self, *args, **kwargs):
        super(ConfigDeploy, self).__init__(*args, **kwargs)
        self.setdefault('name', 'Deployment')
        self.setdefault('description', 'Deployment')
        self.setdefault('configPaths', [])
        self.setdefault('kindTransformMappings', [])
        self.setdefault('deviceReference', Reference())

class RefreshWorkingConfig(Task):
    URI = '/mgmt/cm/shared/config/refresh-working-config'

    def __init__(self, *args, **kwargs):
        super(RefreshWorkingConfig, self).__init__(*args, **kwargs)
        self.setdefault('configPaths', [])
        self.setdefault('deviceReference', Reference())

