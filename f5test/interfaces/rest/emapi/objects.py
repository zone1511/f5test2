'''
Created on Jan 30, 2013

@author: jono
'''
from ....base import enum, AttrDict
from ....utils.wait import wait
# import yaml
import json
import os

DEFAULT_TIMEOUT = 30


class TaskError(Exception):
    pass


class SharedObject(AttrDict):

    def from_file(self, directory, name=None, fmt='json'):
        if name is None:
            name = "%s.%s" % (self.get('name', 'default'), fmt)

        if fmt is 'json':
            with file(os.path.join(directory, name)) as f:
                self.update(json.load(f))
        else:
            raise NotImplementedError('Unknown format: %s' % fmt)

        return self


class Reference(AttrDict):

    def __init__(self, other):
        self.id = other.id
        self.kind = other.kind
        self.link = self.selfLink = other.selfLink
        self.name = other.name
        self.partition = other.partition


class ReferenceList(list):

    def append(self, other):
        if not isinstance(other, Reference):
            other = Reference(other)
        super(ReferenceList, self).append(other)


class Port(AttrDict):
    def __init__(self, *args, **kwargs):
        super(Port, self).__init__(*args, **kwargs)
        self.setdefault('port', '')
        self.setdefault('description', '')


class PortList(SharedObject):
    URI = '/mgmt/cm/firewall/working-config/port-lists'

    def __init__(self, *args, **kwargs):
        super(PortList, self).__init__(*args, **kwargs)
        self.setdefault('name', 'port-list')
        self.setdefault('description', '')
        self.setdefault('partition', '/Common')
        self.setdefault('ports', [])


class Task(AttrDict):

    def wait(self, rest, resource, loop=None, timeout=DEFAULT_TIMEOUT):
        def get_status():
            return rest.get(resource.selfLink)
        if loop is None:
            loop = get_status
        ret = wait(loop, timeout=timeout, interval=1,
                   condition=lambda x: x.overallStatus not in ('NEW',),
                   progress_cb=lambda x: 'Status: {0}:{1}'.format(x.overallStatus,
                                                [y.status for y in x.subtasks]))

        if len(ret.subtasks) != sum(x.status in ('COMPLETE', 'COMPLETED') for x in ret.subtasks):
            msg = json.dumps(ret.subtasks, sort_keys=True, indent=4,
                             ensure_ascii=False)
            # msg = yaml.dump(ret.subtasks, default_flow_style=False,
            #                indent=4, width=999)
            raise TaskError("At least one subtask is not completed:\n%s" % msg)
        return ret


class DistributeConfigTask(Task):
    URI = '/mgmt/cm/firewall/tasks/distribute-config'

    def __init__(self, *args, **kwargs):
        super(DistributeConfigTask, self).__init__(*args, **kwargs)
        self.setdefault('description', '')
        config = AttrDict(deviceUriList=[],
                          addConfigUriList=[],
                          updateConfigUriList=[],
                          deleteConfigUriList=[])
        self.setdefault('configList', [config])


class DeployConfigTask(Task):
    URI = '/mgmt/cm/firewall/tasks/deploy-configuration'

    def __init__(self, *args, **kwargs):
        super(DeployConfigTask, self).__init__(*args, **kwargs)
        self.setdefault('description', '')
        self.setdefault('fromSnapshot')
        self.setdefault('deviceFilter', [])


class SnapshotConfigTask(Task):
    URI = '/mgmt/cm/firewall/tasks/snapshot-config'

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
    URI = '/mgmt/cm/firewall/working-config/snapshots'

    def __init__(self, *args, **kwargs):
        super(Snapshot, self).__init__(*args, **kwargs)
        self.setdefault('name', 'snapshot')
        self.setdefault('description', '')


class Schedule(SharedObject):
    URI = '/mgmt/cm/firewall/working-config/schedules'

    def __init__(self, *args, **kwargs):
        super(Schedule, self).__init__(*args, **kwargs)
        self.setdefault('name', 'schedule')
        self.setdefault('description', '')
        self.setdefault('partition', '/Common')
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
    URI = '/mgmt/cm/firewall/working-config/address-lists'

    def __init__(self, *args, **kwargs):
        super(AddressList, self).__init__(*args, **kwargs)
        self.setdefault('name', 'address-list')
        self.setdefault('description', '')
        self.setdefault('partition', '/Common')
        self.setdefault('addresses', [])


class RuleList(SharedObject):
    URI = '/mgmt/cm/firewall/working-config/rule-lists'

    def __init__(self, *args, **kwargs):
        super(RuleList, self).__init__(*args, **kwargs)
        self.setdefault('name', 'rule-list')
        self.setdefault('description', '')
        self.setdefault('partition', '/Common')


class Rule(SharedObject):
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


class Firewall(SharedObject):
    URI = '/mgmt/cm/firewall/working-config/firewalls'
    TYPES = enum(GLOBAL='global',
                 MANAGEMENT_IP='management-ip',
                 ROUTE_DOMAIN='route-domain',
                 VIP='vip',
                 SELF_IP='self-ip')

    def __init__(self, *args, **kwargs):
        super(Firewall, self).__init__(*args, **kwargs)
        self.setdefault('name', 'firewall')
        self.setdefault('deviceReference', AttrDict(link='/foo/bar'))
        self.setdefault('firewallType', Firewall.TYPES.GLOBAL)
        self.setdefault('parentRouteDomain')
        self.setdefault('vlan')
        self.setdefault('rulesCollectionUri', '')
        self.setdefault('partition', '/Common')


class ManagedDevice(SharedObject):
    URI = '/mgmt/cm/firewall/managed-devices'

    def __init__(self, *args, **kwargs):
        super(ManagedDevice, self).__init__(*args, **kwargs)
        self.setdefault('deviceAddress')
        self.setdefault('username')
        self.setdefault('password')


class DeclareMgmtAuthorityTask(Task):
    URI = '/mgmt/cm/firewall/tasks/declare-mgmt-authority'

    def __init__(self, *args, **kwargs):
        super(DeclareMgmtAuthorityTask, self).__init__(*args, **kwargs)
        self.setdefault('subtasks', [])


class RemoveMgmtAuthorityTask(Task):
    URI = '/mgmt/cm/firewall/tasks/remove-mgmt-authority'

    def __init__(self, *args, **kwargs):
        super(RemoveMgmtAuthorityTask, self).__init__(*args, **kwargs)
        self.setdefault('devicelink')


# Cloud objects

class Account(AttrDict):
    def __init__(self, *args, **kwargs):
        super(Account, self).__init__(*args, **kwargs)
        self.setdefault('userName', '')
        self.setdefault('roleName', '')


class ManagedDeviceCloud(ManagedDevice):
    URI = '/mgmt/cm/cloud/managed-devices'


class Connector(SharedObject):

    localURI = '/mgmt/cm/cloud/connectors/local'
    vmwareURI = '/mgmt/cm/cloud/connectors/vmware'
    ec2URI = '/mgmt/cm/cloud/connectors/ec2'

    def __init__(self, *args, **kwargs):
            super(Connector, self).__init__(*args, **kwargs)
            self.setdefault('name', 'test')
            self.setdefault('description', '')
            self.setdefault('cloudConnectorReference', AttrDict(link=''))
            self.setdefault('connectorId', '')
            self.setdefault('deviceReferences', [])
            self.setdefault('parameters', [])

class Tenant(SharedObject):
    URI = '/mgmt/cm/cloud/tenants'
    userReferenceURI = '/mgmt/shared/authz/users'

    def __init__(self, *args, **kwargs):
        super(Tenant, self).__init__(*args, **kwargs)
        self.setdefault('name', 'tenant')
        self.setdefault('description', 'Tenant description.')
#        self.setdefault('username', 'admin')
        self.setdefault('classType', 'enterprise')
        self.setdefault('addressContact', '123 Foo Bar Ave.')
        self.setdefault('phone', '(234)-900-1009')
        self.setdefault('email', 'tenant@enterprise.net')
        self.setdefault('userReference', ReferenceList())
        self.setdefault('cloudConnectorReferences', [])

class JimmyTenant(SharedObject):
    URI = '/mgmt/cm/cloud/tenants'

    def __init__(self, *args, **kwargs):
        super(JimmyTenant, self).__init__(*args, **kwargs)
        self.setdefault('name', 'tenant')
        self.setdefault('description', 'Tenant description.')
        self.setdefault('userReference', AttrDict(link=''))
        self.setdefault('classType', 'enterprise')
        self.setdefault('addressContact', '123 Foo Bar Ave.')
        self.setdefault('phone', '(234)-900-1009')
        self.setdefault('email', 'tenant@enterprise.net')
        self.setdefault('cloudConnectorReferences', [])


class TenantPlacement(SharedObject):
    URI = '/mgmt/cm/cloud/tenants/services/placement'

    def __init__(self, *args, **kwargs):
        super(TenantPlacement, self).__init__(*args, **kwargs)
        self.setdefault('tenant', 'tenant')
        self.setdefault('iAppTemplate', '')


class TenantServiceProperties(AttrDict):
    def __init__(self, *args, **kwargs):
        super(TenantServiceProperties, self).__init__(*args, **kwargs)
        self.setdefault('id', 'cloudConnectorReference')
        self.setdefault('value', '')

class TenantServiceBasicAddr113(AttrDict):
    def __init__(self, *args, **kwargs):
        super(TenantServiceBasicAddr113, self).__init__(*args, **kwargs)
        self.setdefault('name', 'basic__addr')
        self.setdefault('value', '')

class TenantServiceSrvPoolSrv113(AttrDict):
    def __init__(self, *args, **kwargs):
        super(TenantServiceSrvPoolSrv113, self).__init__(*args, **kwargs)
        self.setdefault('name', 'server_pools__servers')
        self.setdefault('columns', [])
        self.setdefault('rows', [])


class TenantService(SharedObject):
    URI = Tenant.URI + '/%s/services/iapp'
    TenantTemplateReferenceURI = '/mgmt/cm/cloud/tenant/templates/iapp'

    def __init__(self, *args, **kwargs):
        super(TenantService, self).__init__(*args, **kwargs)
        self.setdefault('name', 'tenant-service')
        self.setdefault('tenantTemplateReference', AttrDict(link=''))
        self.setdefault('tenantReference', ReferenceList())
        self.setdefault('properties', [])
        self.setdefault('vars', [])
        self.setdefault('tables', [])

class JimmyTenantService(SharedObject):
    URI = Tenant.URI + '/%s/services/iapp'

    def __init__(self, *args, **kwargs):
        super(JimmyTenantService, self).__init__(*args, **kwargs)
        self.setdefault('name', 'tenant-service')
        self.setdefault('tenantTemplateReference', AttrDict(link=''))
        self.setdefault('properties', [])
        self.setdefault('vars', [])
        self.setdefault('tables', [])


class IappTemplateProperties(AttrDict):
    def __init__(self, *args, **kwargs):
        super(IappTemplateProperties, self).__init__(*args, **kwargs)
        self.setdefault('id', 'cloudConnectorReference')
        self.setdefault('displayName', 'Cloud Connector')
        self.setdefault('isRequired', True)
        self.setdefault('provider', '')


class IappTemplate(SharedObject):
    URI = '/mgmt/cm/cloud/provider/templates/iapp'

    class Variable(AttrDict):
        def __init__(self, *args, **kwargs):
            super(IappTemplate.Variable, self).__init__(*args, **kwargs)
            self.setdefault('name', 'foo')
            self.setdefault('provider', 'bar')
            self.setdefault('providerType', None)
            self.setdefault('isRequired', True)

    class Table(AttrDict):
        def __init__(self, *args, **kwargs):
            super(IappTemplate.Table, self).__init__(*args, **kwargs)
            self.setdefault('name', 'iapp_table')
            self.setdefault('columns', [])

    def __init__(self, *args, **kwargs):
        super(IappTemplate, self).__init__(*args, **kwargs)
        self.setdefault('templateName', 'template')
        self.setdefault('parentReference', AttrDict(link=''))
        self.setdefault('overrides', AttrDict(vars=[], tables=[]))
        self.setdefault('properties', [])


class ConnectorObjects(AttrDict):
    def __init__(self, *args, **kwargs):
        super(ConnectorObjects, self).__init__(*args, **kwargs)
        self.setdefault('id', '')
        self.setdefault('displayName', '')
        self.setdefault('isRequired', 'true')
        self.setdefault('value', '')

class Link(AttrDict):
    def __init__(self, *args, **kwargs):
        super(Link, self).__init__(*args, **kwargs)
        self.setdefault('link', '')


class UserCredentialData(SharedObject):
    URI = '/mgmt/shared/authz/users'
    ITEM_URI = '/mgmt/shared/authz/users/%s'

    def __init__(self, *args, **kwargs):
        super(UserCredentialData, self).__init__(*args, **kwargs)
        self.setdefault('name', 'NewTenant')
        self.setdefault('password', 'f5site02')

class License(AttrDict):
    LICENSE_KEY_URI = '/mgmt/cm/shared/activate-license'
    URI = '/mgmt/cm/shared/license'

    def __init__(self, *args, **kwargs):
        super(License, self).__init__(*args, **kwargs)
        self.setdefault('baseRegKey', '')
        self.setdefault('addOnKeys', [])
        self.setdefault('automaticActivation', 'true')
        
class EasySetup(SharedObject):
    URI = '/mgmt/shared/system/easy-setup'
    def __init__(self, *args, **kwargs):
        super(EasySetup, self).__init__(*args, **kwargs)
        self.setdefault('hostname', '')
        self.setdefault('internalSelfIpAddresses', [])
        self.setdefault('ntpServerAddresses', [])
        self.setdefault('dnsServerAddresses', [])
        self.setdefault('dnsSearchDomains', [])

