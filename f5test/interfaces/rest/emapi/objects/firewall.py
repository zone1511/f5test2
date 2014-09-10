'''
Created on Jan 9, 2014

/mgmt/cm/firewall workers

@author: jono
'''
from .....base import enum, AttrDict
from .....defaults import ADMIN_USERNAME, ADMIN_PASSWORD
from .base import Reference, ReferenceList, Task, TaskError, DEFAULT_TIMEOUT
from ...base import BaseApiObject
from ...core import RestInterface
from .....utils.wait import wait
import json


class Port(AttrDict):
    def __init__(self, *args, **kwargs):
        super(Port, self).__init__(*args, **kwargs)
        self.setdefault('port', '')
        self.setdefault('description', '')


class PortList(BaseApiObject):
    URI = '/mgmt/cm/firewall/working-config/port-lists'

    def __init__(self, *args, **kwargs):
        super(PortList, self).__init__(*args, **kwargs)
        self.setdefault('name', 'port-list')
        self.setdefault('description', '')
        self.setdefault('partition', 'Common')
        self.setdefault('ports', [])


class SecurityTaskV1(Task):

    def wait(self, rest, resource, loop=None, timeout=DEFAULT_TIMEOUT,
             timeout_message=None):
        def get_status():
            return rest.get(resource.selfLink)
        if loop is None:
            loop = get_status

        ret = wait(loop, timeout=timeout, interval=1,
                   timeout_message=timeout_message,
                   condition=lambda x: x.overallStatus not in ('NEW',),
                   progress_cb=lambda x: 'Status: {0}:{1}'.format(x.overallStatus,
                                           [y.status for y in x.subtasks or []]))

        if len(ret.subtasks) != sum(x.status in ('COMPLETE', 'COMPLETED') for x in ret.subtasks):
            msg = json.dumps(ret.subtasks, sort_keys=True, indent=4,
                             ensure_ascii=False)
            # msg = yaml.dump(ret.subtasks, default_flow_style=False,
            #                indent=4, width=999)
            raise TaskError("At least one subtask is not completed:\n%s" % msg)

        return ret


class SecurityTaskV2(Task):

    def wait(self, rstifc, resource, loop=None, timeout=DEFAULT_TIMEOUT,
             timeout_message=None):

        # Backwards compatibility
        rest = rstifc.api if isinstance(rstifc, RestInterface) else rstifc

        def get_status():
            return rest.get(resource.selfLink)
        if loop is None:
            loop = get_status

        # Backwards compatibility
        if isinstance(rstifc, RestInterface) and rstifc.version >= 'bigiq 4.4.0':
            wait(loop, timeout=timeout, interval=1,
                 timeout_message=timeout_message,
                 condition=lambda x: x.status not in ('CREATED',),
                 progress_cb=lambda x: 'Wait until out of CREATED state...')

            ret = wait(loop, timeout=timeout, interval=1,
                       timeout_message=timeout_message,
                       condition=lambda x: x.status not in ('STARTED',),
                       progress_cb=lambda x: 'Status: {0}'.format(x.currentStep))

            if ret.status != 'FINISHED' or ret.currentStep != 'DONE':
                msg = json.dumps(ret, sort_keys=True, indent=4,
                                 ensure_ascii=False)
                raise TaskError("Firewall Deploy failed:\n%s" % msg)

        else:
            ret = wait(loop, timeout=timeout, interval=1,
                       timeout_message=timeout_message,
                       condition=lambda x: x.overallStatus not in ('NEW',),
                       progress_cb=lambda x: 'Status: {0}:{1}'.format(x.overallStatus,
                                               [y.status for y in x.subtasks or []]))

            if len(ret.subtasks) != sum(x.status in ('COMPLETE', 'COMPLETED') for x in ret.subtasks):
                msg = json.dumps(ret.subtasks, sort_keys=True, indent=4,
                                 ensure_ascii=False)
                # msg = yaml.dump(ret.subtasks, default_flow_style=False,
                #                indent=4, width=999)
                raise TaskError("At least one subtask is not completed:\n%s" % msg)

        return ret


class DistributeConfigTask(SecurityTaskV2):
    URI = '/mgmt/cm/firewall/tasks/distribute-config'

    def __init__(self, *args, **kwargs):
        super(DistributeConfigTask, self).__init__(*args, **kwargs)
        self.setdefault('description', '')
        config = AttrDict(deviceUriList=[],
                          addConfigUriList=[],
                          updateConfigUriList=[],
                          deleteConfigUriList=[])
        self.setdefault('configList', [config])


class DeployConfigTask(SecurityTaskV2):
    URI = '/mgmt/cm/firewall/tasks/deploy-configuration'

    def __init__(self, *args, **kwargs):
        super(DeployConfigTask, self).__init__(*args, **kwargs)
        self.setdefault('description', '')


class SnapshotConfigTask(SecurityTaskV2):
    URI = '/mgmt/cm/firewall/tasks/snapshot-config'
    PENDING_STATES = ('STARTED')

    def __init__(self, *args, **kwargs):
        super(SnapshotConfigTask, self).__init__(*args, **kwargs)
        self.setdefault('name', 'snapshot-config')
        self.setdefault('description', '')
        self.setdefault('subtasks', [])

    @staticmethod
    def wait(rest, snapshot, timeout=DEFAULT_TIMEOUT):
        selflink = snapshot.selfLink if isinstance(snapshot, dict) \
                    else snapshot

        ret = wait(lambda: rest.get(selflink),
                   condition=lambda ret: not ret.status in SnapshotConfigTask.PENDING_STATES,
                   progress_cb=lambda ret: 'Snapshot status: {0}'.format(ret.status),
                   timeout=timeout)

        if ret.status != 'FINISHED':
            msg = json.dumps(ret, sort_keys=True, indent=4, ensure_ascii=False)
            raise TaskError("SnapshotConfigTask failed.\n%s" % msg)

        return ret


class SnapshotSubtask(AttrDict):
    def __init__(self, snapshot):
        super(SnapshotSubtask, self).__init__(snapshot)
        self.setdefault('snapshot_reference', snapshot)


class Snapshot(AttrDict):
    URI = '/mgmt/cm/firewall/working-config/snapshots'

    def __init__(self, *args, **kwargs):
        super(Snapshot, self).__init__(*args, **kwargs)
        self.setdefault('name', 'snapshot')
        self.setdefault('description', '')


class Schedule(BaseApiObject):
    URI = '/mgmt/cm/firewall/working-config/schedules'

    def __init__(self, *args, **kwargs):
        super(Schedule, self).__init__(*args, **kwargs)
        self.setdefault('name', 'schedule')
        self.setdefault('description', '')
        self.setdefault('partition', 'Common')
        self.setdefault('dailyHourStart')
        self.setdefault('dailyHourEnd')
        self.setdefault('localDateValidStart')
        self.setdefault('localDateValidEnd')
        self.setdefault('daysOfWeek', [])


class Address(AttrDict):
    def __init__(self, *args, **kwargs):
        super(Address, self).__init__(*args, **kwargs)
        self.setdefault('address', '')
        self.setdefault('description', '')


class AddressList(BaseApiObject):
    URI = '/mgmt/cm/firewall/working-config/address-lists'

    def __init__(self, *args, **kwargs):
        super(AddressList, self).__init__(*args, **kwargs)
        self.setdefault('name', 'address-list')
        self.setdefault('description', '')
        self.setdefault('partition', 'Common')
        self.setdefault('addresses', [])


class RuleList(BaseApiObject):
    URI = '/mgmt/cm/firewall/working-config/rule-lists'

    def __init__(self, *args, **kwargs):
        super(RuleList, self).__init__(*args, **kwargs)
        self.setdefault('name', 'rule-list')
        self.setdefault('description', '')
        self.setdefault('partition', 'Common')


class PolicyList(BaseApiObject):
    URI = '/mgmt/cm/firewall/working-config/policies'

    def __init__(self, *args, **kwargs):
        super(PolicyList, self).__init__(*args, **kwargs)
        self.setdefault('name', 'policy-list')
        self.setdefault('description', '')
        self.setdefault('partition', 'Common')


class Rule(BaseApiObject):
    URI = RuleList.URI + '/%s/rules'
    STATES = enum(ENABLED='enabled',
                  DISABLED='disabled',
                  SCHEDULED='scheduled')
    ACTIONS = enum(ACCEPT='accept',
                   ACCEPT_DECISIVELY='accept-decisively',
                   REJECT='reject',
                   DROP='drop')

    def __init__(self, *args, **kwargs):
        super(Rule, self).__init__(*args, **kwargs)
        self.setdefault('name', 'rule')
        self.setdefault('description', '')
        self.setdefault('action', Rule.ACTIONS.ACCEPT)
        self.setdefault('evalOrder', 0)
        self.setdefault('log', False)
        self.setdefault('protocol', 'tcp')
        self.setdefault('scheduleReference')
        self.setdefault('state', Rule.STATES.ENABLED)
        self.setdefault('destination', AttrDict(addresses=[],
                                                addressListReferences=ReferenceList(),
                                                ports=[],
                                                portListReferences=ReferenceList()))
        self.setdefault('source', AttrDict(addresses=[],
                                           addressListReferences=ReferenceList(),
                                           ports=[],
                                           portListReferences=ReferenceList(),
                                           vlans=[]))
        self.setdefault('ruleListReference')
#         self.setdefault('icmpTypeCodes')


class Firewall(BaseApiObject):
    URI = '/mgmt/cm/firewall/working-config/firewalls'
    TYPES = enum(GLOBAL='global',
                 MANAGEMENT_IP='management-ip',
                 ROUTE_DOMAIN='route-domain',
                 VIP='vip',
                 SELF_IP='self-ip')

    def __init__(self, *args, **kwargs):
        super(Firewall, self).__init__(*args, **kwargs)
        self.setdefault('name', 'firewall')
        self.setdefault('deviceReference', Reference())
        self.setdefault('firewallType', Firewall.TYPES.GLOBAL)
        self.setdefault('parentRouteDomain')
        self.setdefault('vlan')
        self.setdefault('rulesCollectionUri', '')
        self.setdefault('partition', 'Common')


class ManagedDevice(BaseApiObject):
    URI = '/mgmt/cm/firewall/managed-devices'

    def __init__(self, *args, **kwargs):
        super(ManagedDevice, self).__init__(*args, **kwargs)
        self.setdefault('deviceAddress', '')
        self.setdefault('username', ADMIN_USERNAME)
        self.setdefault('password', ADMIN_PASSWORD)


class DeclareMgmtAuthorityTask(SecurityTaskV1):
    URI = '/mgmt/cm/firewall/tasks/declare-mgmt-authority'

    def __init__(self, *args, **kwargs):
        super(DeclareMgmtAuthorityTask, self).__init__(*args, **kwargs)
        self.setdefault('subtasks', [])


class RemoveMgmtAuthorityTask(SecurityTaskV1):
    URI = '/mgmt/cm/firewall/tasks/remove-mgmt-authority'

    def __init__(self, *args, **kwargs):
        super(RemoveMgmtAuthorityTask, self).__init__(*args, **kwargs)
        self.setdefault('devicelink')


# Introduced in Bigtime
class RemoveMgmtAuthorityTaskV2(SecurityTaskV1):
    URI = '/mgmt/cm/firewall/tasks/remove-mgmt-authority'

    def __init__(self, *args, **kwargs):
        super(RemoveMgmtAuthorityTaskV2, self).__init__(*args, **kwargs)
        self.setdefault('deviceReference', Reference())
