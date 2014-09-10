'''
Created on Jan 9, 2014

/mgmt/[cm|tm|shared]/system

@author: jono
'''
from .....base import enum, AttrDict
from .base import Reference, Task, TaskError, DEFAULT_TIMEOUT, ReferenceList
from ...base import BaseApiObject
from .....utils.wait import wait
import json


class EasySetup(BaseApiObject):
    URI = '/mgmt/shared/system/easy-setup'

    def __init__(self, *args, **kwargs):
        super(EasySetup, self).__init__(*args, **kwargs)
        self.setdefault('hostname', '')
        self.setdefault('internalSelfIpAddresses', [])
        self.setdefault('selfIpAddresses', [])
        self.setdefault('ntpServerAddresses', [])
        self.setdefault('dnsServerAddresses', [])
        self.setdefault('dnsSearchDomains', [])


# Ref-https://peterpan.f5net.com/twiki/bin/view/Cloud/TM_Cloud_Interface_API
class NetworkInterface(BaseApiObject):
    URI = '/mgmt/tm/cloud/net/interface'
    ITEM_URI = '/mgmt/tm/cloud/net/interface/%s'

    def __init__(self, *args, **kwargs):
        super(NetworkInterface, self).__init__(*args, **kwargs)
        self.setdefault('name', '')
        self.setdefault('description', '')


# Ref-https://peterpan.f5net.com/twiki/bin/view/Cloud/SB_TM_Cloud_Vlan_API
class NetworkVlan(BaseApiObject):
    URI = '/mgmt/tm/cloud/net/vlan'
    ITEM_URI = '/mgmt/tm/cloud/net/vlan/%s'

    def __init__(self, *args, **kwargs):
        super(NetworkVlan, self).__init__(*args, **kwargs)
        self.setdefault('name', '')
        self.setdefault('interfacesReference')


# Ref- https://peterpan.f5net.com/twiki/bin/view/Cloud/SB_TM_Cloud_Self_API
class NetworkSelfip(BaseApiObject):
    URI = '/mgmt/tm/cloud/net/self'
    ITEM_URI = '/mgmt/tm/cloud/net/self/%s'

    def __init__(self, *args, **kwargs):
        super(NetworkSelfip, self).__init__(*args, **kwargs)
        self.setdefault('name', '')
        self.setdefault('address', '')
        self.setdefault('vlanReference', Reference())


# Ref - https://peterpan.f5net.com/twiki/bin/view/Cloud/BackupRestoreTaskWorker
class BackupRestoreTask(Task):
    URI = '/mgmt/cm/system/backup-restore'
    ITEM_URI = '%s/%%s' % URI
    STATUS = enum('BACKUP_GET_DEVICE', 'BACKUP_MAKE_BACKUP',
                  'BACKUP_DOWNLOAD_BACKUP', 'BACKUP_FINISHED', 'BACKUP_FAILED',

                  'RESTORE_REQUESTED', 'RESTORE_GET_DEVICE',
                  'RESTORE_UPLOAD_BACKUP', 'RESTORE_RESTORE_BACKUP',
                  'RESTORE_FINISHED', 'RESTORE_FAILED')

    def __init__(self, *args, **kwargs):
        super(BackupRestoreTask, self).__init__(*args, **kwargs)
        self.setdefault('deviceReference', Reference())
        self.setdefault('name', '')
        self.setdefault('description', '')

    @staticmethod
    def wait(rest, resource, timeout=60):

        # Wait for the task to get into a Pending state first
        # See BZ440336
        wait(lambda: rest.get(resource.selfLink),
             condition=lambda x: x.status in Task.PENDING_STATUSES,
             progress_cb=lambda x: 'State: {0}:{1}'.format(x.status,
                                                           x.backupRestoreStatus),
             timeout=timeout, interval=5)
        ret = wait(lambda: rest.get(resource.selfLink),
               condition=lambda x: x.status in Task.FINAL_STATUSES,
               progress_cb=lambda x: 'State: {0}:{1}'.format(x.status,
                                                             x.backupRestoreStatus),
               timeout=timeout, interval=5)
        if ret.status == Task.STATUS.FAILED:  # @UndefinedVariable
            msg = json.dumps(ret, sort_keys=True, indent=4, ensure_ascii=False)
            raise TaskError("Task failed:\n%s" % msg)

        return ret


# Ref- https://peterpan.f5net.com/twiki/bin/view/Cloud/InboundSnmpAccessAPI
class SnmpInbound(BaseApiObject):
    URI = '/mgmt/shared/system/snmp-inbound-access'

    def __init__(self, *args, **kwargs):
        super(SnmpInbound, self).__init__(*args, **kwargs)
        self.setdefault('contactInformation', '')
        self.setdefault('machineLocation', '')
        self.setdefault('clientAllowList', [])


# Ref- https://peterpan.f5net.com/twiki/bin/view/Cloud/SnmpV1V2cAccessRecordsAPI
class SnmpV1V2cAccessRecords(BaseApiObject):
    URI = '/mgmt/shared/system/snmp-v1v2c-access-records'

    def __init__(self, *args, **kwargs):
        super(SnmpV1V2cAccessRecords, self).__init__(*args, **kwargs)
        self.setdefault('community', '')
        self.setdefault('oid', '')
        self.setdefault('readOnlyAccess', True)
        self.setdefault('addressType', '')
        self.setdefault('sourceAddress', '')
        self.setdefault('id', '')


# Ref- https://peterpan.f5net.com/twiki/bin/view/Cloud/SnmpV3AccessRecordsAPI
class SnmpV3AccessRecords(BaseApiObject):
    URI = '/mgmt/shared/system/snmp-v3-access-records'
    AUTHNP = enum(MD5='MD5',
                  SHA='SHA')
    PRIPRO = enum(AES='AES',
                  DES='DES')

    def __init__(self, *args, **kwargs):
        super(SnmpV3AccessRecords, self).__init__(*args, **kwargs)
        self.setdefault('username', '')
        self.setdefault('oid', '')
        self.setdefault('readOnlyAccess', True)
        self.setdefault('useAuthPasswordForPrivacy', False)
        self.setdefault('authProtocol', SnmpV3AccessRecords.AUTHNP.MD5)
        self.setdefault('authnPassword', '')
        self.setdefault('privacyProtocol', SnmpV3AccessRecords.PRIPRO.AES)
        self.setdefault('privacyPassword', '')
        self.setdefault('id', '')


# Ref- https://peterpan.f5net.com/twiki/bin/view/Cloud/SnmpTrapDestinationsAPI
class SnmpTrap(BaseApiObject):
    URI = '/mgmt/shared/system/snmp-trap-destinations'
    AUTHNP = enum(MD5='MD5',
                  SHA='SHA',
                  NONE='NONE')
    PRIPRO = enum(AES='AES',
                  DES='DES',
                  NONE='NONE')
    SLEVEL = enum(ANP='authNoPriv',
                  AP='authPriv')
    VERSION = enum(V1='V1',
                  V2C='V2C',
                  V3='V3')

    def __init__(self, *args, **kwargs):
        super(SnmpTrap, self).__init__(*args, **kwargs)
        self.setdefault('version', SnmpTrap.VERSION.V2C)
        self.setdefault('host', '')
        self.setdefault('port', '162')
        self.setdefault('securityLevel', SnmpTrap.SLEVEL.ANP)
        self.setdefault('name', '')
        self.setdefault('authProtocol', SnmpTrap.AUTHNP.MD5)
        self.setdefault('securityName', '')
        self.setdefault('engineId', '')
        self.setdefault('community', '')
        self.setdefault('authPassword', '')
        self.setdefault('privacyProtocol', SnmpTrap.PRIPRO.NONE)
        self.setdefault('privacyPassword', '')
        self.setdefault('id', '')


# Doc: https://peterpan.f5net.com/twiki/bin/view/Cloud/CertificatesWorkerDesign
class Certificates(AttrDict):
    URI = '/mgmt/cm/system/certificates'
    ITEM_URI = '%s/%%s' % URI

    def __init__(self, *args, **kwargs):
        super(Certificates, self).__init__(*args, **kwargs)


# Doc: https://peterpan.f5net.com/twiki/bin/view/Cloud/SmtpDestinationsAPI
class SnmpDestination(AttrDict):
    URI = '/mgmt/shared/system/smtp-destinations'
    ENCRYPTION_TYPE = enum('NO_ENCRYPTION', 'SSL', 'TLS')

    def __init__(self, *args, **kwargs):
        super(SnmpDestination, self).__init__(*args, **kwargs)

        self.setdefault('name', '')
        self.setdefault('host', '')
#         self.setdefault('port', 25)
        self.setdefault('fromAddress', '')
        self.setdefault('encryptedConnection',
                        SnmpDestination.ENCRYPTION_TYPE.NO_ENCRYPTION)
#         self.setdefault('userName', '')
#         self.setdefault('password', '')


# Doc: https://peterpan.f5net.com/twiki/bin/view/Cloud/ContactsCollectionWorkerAPI
class Contact(AttrDict):
    URI = '/mgmt/cm/system/contacts'
    ITEM_URI = '%s/%%s' % URI

    def __init__(self, *args, **kwargs):
        super(Contact, self).__init__(*args, **kwargs)
        self.setdefault('name', '')
        self.setdefault('emailAddress', '')


# Doc: ?
class EventConfiguration(AttrDict):
    URI = '/mgmt/shared/system/event-configuration'
    ITEM_URI = '%s/%%s' % URI

    def __init__(self, *args, **kwargs):
        super(Contact, self).__init__(*args, **kwargs)
        self.setdefault('enabled', True)
        self.setdefault('name', '')


# Doc: ?
class SmtpEmail(AttrDict):
    URI = '/mgmt/shared/smtp-email'

    def __init__(self, *args, **kwargs):
        super(SmtpEmail, self).__init__(*args, **kwargs)
        self.setdefault('body', 'Hello world!')
        self.setdefault('subject', 'Test')
        self.setdefault('toAddresses', [])
        self.setdefault('destination', AttrDict(authentication='no',
                                                fromAddress='nobody@foo.com',
                                                host='',
                                                name='test',
                                                #password='',
                                                #userName='',
                                                port=25))


# Ref- https://peterpan.f5net.com/twiki/bin/view/Cloud/BulkDiscoveryTaskCollectionWorkerAPI
class BulkDiscovery(BaseApiObject):
    URI = '/mgmt/shared/device-discovery'
    ITEM_URI = '/mgmt/shared/device-discovery/%s'
    FINISH_STATE = 'FINISHED'
    CANCEL_STATE = 'CANCELED'
    START_STATE = 'STARTED'

    def __init__(self, *args, **kwargs):
        super(BulkDiscovery, self).__init__(*args, **kwargs)
        self.setdefault('filePath', '')
        self.setdefault('groupReference', Reference())
        self.setdefault('status', '')

    @staticmethod
    def wait(rest, timeout=DEFAULT_TIMEOUT):

        def all_done(ret):
            return sum(1 for x in ret['items'] if (x.status == BulkDiscovery.FINISH_STATE or \
                    x.status == BulkDiscovery.CANCEL_STATE)) == sum(1 for x in ret['items'])

        ret = wait(lambda: rest.get(BulkDiscovery.URI), timeout=timeout, interval=1,
                   condition=all_done,
                   progress_cb=lambda ret: 'Status: {0}'.format(list(x.status for x in ret['items'])))

        return ret

    @staticmethod
    def cancel_wait(rest, timeout=DEFAULT_TIMEOUT):

        def all_done(ret):
            return sum(1 for x in ret['items'] if (x.status == BulkDiscovery.START_STATE or x.status == BulkDiscovery.FINISH_STATE or \
                    x.status == BulkDiscovery.CANCEL_STATE)) == sum(1 for x in ret['items'])

        ret = wait(lambda: rest.get(BulkDiscovery.URI), timeout=timeout, interval=1,
                   condition=all_done,
                   progress_cb=lambda ret: 'Status: {0}'.format(list(x.status for x in ret['items'])))

        return ret

    @staticmethod
    def start_wait(rest, link, timeout=DEFAULT_TIMEOUT):

        def all_done(ret):
            return len(ret['items']) == 2

        ret = wait(lambda: rest.get(link), timeout=timeout, interval=1,
                   condition=all_done,
                   progress_cb=lambda ret: len(ret['items']))
        return ret

# Ref- https://confluence.pdsea.f5net.com/display/BIGIQDEVICETEAM/Radius+Authentication+Providers
class RadiusProvider(AttrDict):
    URI = '/mgmt/cm/system/authn/providers/radius'
    ITEM_URI = '%s/%%s' % URI

    def __init__(self, *args, **kwargs):
        super(RadiusProvider, self).__init__(*args, **kwargs)
        self.setdefault('name', '')
        self.setdefault('host', '')
        self.setdefault('port', 1812)
        self.setdefault('secret', '')


class RadiusProviderLogin(AttrDict):
    URI = '%s/login' % RadiusProvider.ITEM_URI

    def __init__(self, *args, **kwargs):
        super(RadiusProviderLogin, self).__init__(*args, **kwargs)
        self.setdefault('username', '')
        self.setdefault('password', '')


class RadiusProviderUserGroups(AttrDict):
    URI = '%s/user-groups' % RadiusProvider.ITEM_URI

    def __init__(self, *args, **kwargs):
        super(RadiusProviderUserGroups, self).__init__(*args, **kwargs)
        self.setdefault('propertyMap', {})
        self.setdefault('name', '')


# Ref- https://confluence.pdsea.f5net.com/pages/viewpage.action?pageId=21650529
class LdapProvider(AttrDict):
    URI = '/mgmt/cm/system/authn/providers/ldap'
    ITEM_URI = '%s/%%s' % URI

    def __init__(self, *args, **kwargs):
        super(LdapProvider, self).__init__(*args, **kwargs)
        self.setdefault('name', '')
        self.setdefault('host', '')
        self.setdefault('port', 389)
        self.setdefault('rootDn', '')
        self.setdefault('authMethod', 'none')


class LdapProviderUserGroups(AttrDict):
    URI = '%s/user-groups' % LdapProvider.ITEM_URI

    def __init__(self, *args, **kwargs):
        super(LdapProviderUserGroups, self).__init__(*args, **kwargs)
        self.setdefault('groupDn', '')
        self.setdefault('name', '')


class LdapProviderLogin(AttrDict):
    URI = '%s/login' % LdapProvider.ITEM_URI

    def __init__(self, *args, **kwargs):
        super(LdapProviderLogin, self).__init__(*args, **kwargs)
        self.setdefault('username', '')
        self.setdefault('password', '')


class AuthnLogin(AttrDict):
    URI = '/mgmt/shared/authn/login'

    def __init__(self, *args, **kwargs):
        super(AuthnLogin, self).__init__(*args, **kwargs)
        self.setdefault('username', '')
        self.setdefault('password', '')
        self.setdefault('loginReference', Reference())


# Ref- https://confluence.pdsea.f5net.com/display/BIGIQDEVICETEAM/Service+Cluster+Functional+Design
class ServiceCluster(BaseApiObject):
    URI = '/mgmt/cm/system/dma'
    RMA_URI = '/mgmt/cm/system/rma'
    NET_VLAN = '/mgmt/cm/current/cloud/net/vlan'
    DEVGRP_URI = '/mgmt/cm/current/cloud/cm/device-group'
    FINISH_STATE = 'FINISHED'
    FAILED_STATE = 'FAILED'

    def __init__(self, *args, **kwargs):
        super(ServiceCluster, self).__init__(*args, **kwargs)
        self.setdefault('devicesReference', Reference())

    @staticmethod
    def dma_wait(rest, link, timeout=90):

        def all_done(ret):
            return ret.status in ServiceCluster.FINISH_STATE

        ret = wait(lambda: rest.get(link), timeout=timeout, interval=1,
                   condition=all_done, progress_cb=lambda x: 'Status: {0} '.format(x.status))
        return ret

    @staticmethod
    def wait(rest, group_name, timeout=120):

        def all_done(ret):
            return group_name in list(x.name for x in ret['items'])

        ret = wait(lambda: rest.get(ServiceCluster.DEVGRP_URI), timeout=timeout, interval=1,
                   condition=all_done, progress_cb=lambda ret: 'Status: {0}'.format(list(x.name for x in ret['items'])))
        return ret

    @staticmethod
    def wait_twice(rest, group_name, timeout=120):

        def all_done(ret):
            num = sum(1 for x in ret['items'] if x.name == group_name)
            return num == 2 or num == 3

        ret = wait(lambda: rest.get(ServiceCluster.DEVGRP_URI), timeout=timeout, interval=1,
                   condition=all_done, progress_cb=lambda ret: 'Status: {0}'.format(list(x.name for x in ret['items'])))
        return ret

    @staticmethod
    def wait_thrice(rest, group_name, timeout=120):

        def all_done(ret):
            num = sum(1 for x in ret['items'] if x.name == group_name)
            return num == 3

        ret = wait(lambda: rest.get(ServiceCluster.DEVGRP_URI), timeout=timeout, interval=1,
                   condition=all_done, progress_cb=lambda ret: 'Status: {0}'.format(list(x.name for x in ret['items'])))
        return ret
