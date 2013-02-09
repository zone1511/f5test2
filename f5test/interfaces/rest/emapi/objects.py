'''
Created on Jan 30, 2013

@author: jono
'''
from ....base import AttrDict
from ....utils.wait import wait
import yaml


class TaskError(Exception):
    pass


class SharedObject(AttrDict):
    pass


class Port(AttrDict):
    def __init__(self, *args, **kwargs):
        super(Port, self).__init__(*args, **kwargs)
        self.setdefault('port', '')
        self.setdefault('description', '')


class PortList(SharedObject):
    URI = '/rest/config/working/firewall/port-lists'

    def __init__(self, *args, **kwargs):
        super(PortList, self).__init__(*args, **kwargs)
        self.setdefault('name', 'port-list')
        self.setdefault('description', '')
        self.setdefault('partition', '/Common')
        self.setdefault('ports', [])


class Task(AttrDict):

    def wait(self, rest, resource):
        def get_status():
            return rest.get(resource.selfLink)
        ret = wait(get_status,
                   condition=lambda x: x.overallStatus not in ('NEW',),
                   progress_cb=lambda x: 'Status: ' + x.overallStatus)

        if len(ret.subtasks) != sum(x.status == 'COMPLETED' for x in ret.subtasks):
            raise TaskError("At least one subtask is not completed:\n%s" %
                            yaml.dump(ret.subtasks, default_flow_style=False,
                                      indent=4, width=999))
        return ret


class DistributeConfigTask(Task):
    URI = '/cm/firewall/tasks/distribute-config'

    def __init__(self, *args, **kwargs):
        super(DistributeConfigTask, self).__init__(*args, **kwargs)
        self.setdefault('description', '')
        config = AttrDict(deviceUriList=[],
                          addConfigUriList=[],
                          updateConfigUriList=[],
                          deleteConfigUriList=[])
        self.setdefault('configList', [config])


class DeployConfigTask(Task):
    URI = '/cm/firewall/tasks/deploy-configuration'

    def __init__(self, *args, **kwargs):
        super(DeployConfigTask, self).__init__(*args, **kwargs)
        self.setdefault('description', '')
        self.setdefault('fromSnapshot', '')
        self.setdefault('deviceFilter', [])


class SnapshotConfigTask(Task):
    URI = '/cm/firewall/tasks/snapshot-config'

    def __init__(self, *args, **kwargs):
        super(SnapshotConfigTask, self).__init__(*args, **kwargs)
        self.setdefault('name', 'snapshot-config')
        self.setdefault('description', '')
        self.setdefault('subtasks', [])


class SnapshotSubtask(AttrDict):
    def __init__(self, snapshot):
        super(SnapshotSubtask, self).__init__(snapshot)
        self.setdefault('snapshot_reference', snapshot)


class Snapshot(AttrDict):
    URI = '/rest/config/working/firewall/snapshots'

    def __init__(self, *args, **kwargs):
        super(Snapshot, self).__init__(*args, **kwargs)
        self.setdefault('name', 'snapshot')
        self.setdefault('description', '')

#    def wait(self, rest, resource):
#        def get_status():
#            return rest.get(resource.selfLink)
#        ret = wait(get_status,
#                   condition=lambda x: x.status not in ('NEW',),
#                   progress_cb=lambda x: 'Status: %s' % x)
#        if ret.status != 'COMPLETED':
#            raise TaskError("Snapshot failed:\n%s" %
#                            yaml.dump(ret, default_flow_style=False,
#                                      indent=4, width=999))
#        return ret


class Schedule(SharedObject):
    URI = '/rest/config/working/firewall/schedules'

    def __init__(self, *args, **kwargs):
        super(Schedule, self).__init__(*args, **kwargs)
        self.setdefault('name', 'schedule')
        self.setdefault('description', '')
        self.setdefault('partition', '/Common')
        self.setdefault('generation', 1)
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


class AddressList(SharedObject):
    URI = '/rest/config/working/firewall/address-lists'

    def __init__(self, *args, **kwargs):
        super(AddressList, self).__init__(*args, **kwargs)
        self.setdefault('name', 'address-list')
        self.setdefault('description', '')
        self.setdefault('partition', '/Common')
        self.setdefault('addresses', [])


class RuleList(SharedObject):
    URI = '/rest/config/working/firewall/rule-lists'

    def __init__(self, *args, **kwargs):
        super(RuleList, self).__init__(*args, **kwargs)
        self.setdefault('name', 'rule-list')
        self.setdefault('description', '')
        self.setdefault('partition', '/Common')


class Rule(SharedObject):
    URI = '/rest/config/working/firewall/rule-lists/%s/rules'

    def __init__(self, *args, **kwargs):
        super(Rule, self).__init__(*args, **kwargs)
        self.setdefault('name', 'rule')
        self.setdefault('description', '')
        self.setdefault('action', 'ACCEPT')
        self.setdefault('evalOrder', 10)
        self.setdefault('log', True)
        self.setdefault('protocol', 'tcp')
        self.setdefault('schedule')
        self.setdefault('state', 'ENABLED')
        self.setdefault('destination', AttrDict(addresses=[],
                                                addressLists=[],
                                                ports=[],
                                                portLists=[]))
        self.setdefault('source', AttrDict(addresses=[],
                                           addressLists=[],
                                           ports=[],
                                           portLists=[],
                                           vlans=[]))
