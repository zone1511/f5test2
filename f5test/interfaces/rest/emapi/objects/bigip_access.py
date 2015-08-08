'''
Created on May 21, 2015

@author: ivanitskiy
'''

from f5test.interfaces.rest.base import BaseApiObject
from f5test.base import AttrDict


class ApmAaaLdap(BaseApiObject):
    URI = "/mgmt/tm/apm/aaa/ldap"
    URI_ITEM = URI + "/%s"

    def __init__(self, *args, **kwargs):
        super(ApmAaaLdap, self).__init__(*args, **kwargs)
        self.setdefault('name', "ldap_5")
        self.setdefault('address', "1.1.1.1")
        self.setdefault('cleanupCache', "none")
        self.setdefault('adminDn', "admin")
        self.setdefault('adminEncryptedPassword', "admin")
        self.setdefault('groupCacheTtl', 30)
        self.setdefault('isLdaps', False)
        self.setdefault('locationSpecific', True)
        self.setdefault('port', 389)
        self.setdefault('timeout', 15)
        self.setdefault('usePool', "disabled")
        self.setdefault("schemaAttr", AttrDict())
        self.schemaAttr.groupMember = "member"
        self.schemaAttr.groupMemberValue = "dn"
        self.schemaAttr.groupMemberof = "memberOf"
        self.schemaAttr.groupObjectClass = "group"
        self.schemaAttr.userMemberof = "memberOf"
        self.schemaAttr.userObjectClass = "user"


class ApmAaaActiveDirectory(BaseApiObject):
    URI = "/mgmt/tm/apm/aaa/active-directory"
    URI_ITEM = URI + "/%s"

    def __init__(self, *args, **kwargs):
        super(ApmAaaActiveDirectory, self).__init__(*args, **kwargs)
        self.setdefault('name', "ad_name")
        self.setdefault('adminEncryptedPassword', "password")
        self.setdefault('adminName', "admin")
        self.setdefault('cleanupCache', None)
        self.setdefault('domain', "domain.local")
        self.setdefault('domainController', "dc.domain.local")
        self.setdefault('groupCacheTtl', 30)
        self.setdefault('kdcLockoutDuration', 0)
        self.setdefault('locationSpecific', True)
        self.setdefault('psoCacheTtl', 30)
        self.setdefault('timeout', 15)
        self.setdefault('usePool', "disabled")


class ApmResourceNetworkAccess(BaseApiObject):
    URI = "/mgmt/tm/apm/resource/network-access"
    URI_ITEM = URI + "/%s"

    def __init__(self, *args, **kwargs):
        super(ApmResourceNetworkAccess, self).__init__(*args, **kwargs)
        self.setdefault('name', "na_name")


class ApmResourcePortalAccess(BaseApiObject):
    URI = "/mgmt/tm/apm/resource/portal-access"
    URI_ITEM = URI + "/%s"
    URI_ITEMS = URI + "/%s/items"

    def __init__(self, *args, **kwargs):
        super(ApmResourcePortalAccess, self).__init__(*args, **kwargs)
        self.setdefault('name', "pa_name")


class ApmResourceLeasepool(BaseApiObject):
    URI = "/mgmt/tm/apm/resource/leasepool"

    def __init__(self, *args, **kwargs):
        super(ApmResourceLeasepool, self).__init__(*args, **kwargs)
        self.setdefault('name', "ipv4-leasepool")
        self.setdefault('members', [])
        self.members.append({"name": "1.1.1.1-1.1.1.10"})


class ApmResourceIpv6Leasepool(BaseApiObject):
    URI = "/mgmt/tm/apm/resource/ipv6-leasepool"

    def __init__(self, *args, **kwargs):
        super(ApmResourceIpv6Leasepool, self).__init__(*args, **kwargs)
        self.setdefault('name', "ipv6-leasepool")
        self.setdefault('members', [])
        self.members.append({"name": "2001:db8:85a3::8a2e:370:7334-2001:db8:85a3::8a2e:370:7336"})
