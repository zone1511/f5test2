'''
Created on Oct 15, 2014

DMA (Declare Management Authority) workers

@author: i.turturica@f5.com
'''
from .....utils.wait import wait
from .base import Reference, ReferenceList, Task, DEFAULT_TIMEOUT
from ...base import BaseApiObject


class LtmCommons(type):
    def __new__(cls, name, bases, attrs):
        # Create the class so that we can call its __init__ in the stub()
        klass = super(LtmCommons, cls).__new__(cls, name, bases, attrs)

        # Adds the basic URIs to all Ltm* classes
        klass.STATS_URI = '%s/stats' % klass.URI
        klass.ITEM_URI = '%s/%%s' % klass.URI
        klass.STATS_ITEM_URI = '%s/stats' % klass.ITEM_URI

        return klass


class LtmNode(BaseApiObject):
    __metaclass__ = LtmCommons
    URI = '/mgmt/cm/shared/config/current/ltm/node'

    def __init__(self, *args, **kwargs):
        super(LtmNode, self).__init__(*args, **kwargs)


class LtmPool(BaseApiObject):
    __metaclass__ = LtmCommons
    URI = '/mgmt/cm/shared/config/current/ltm/pool'

    def __init__(self, *args, **kwargs):
        super(LtmPool, self).__init__(*args, **kwargs)


class LtmPoolMembers(BaseApiObject):
    __metaclass__ = LtmCommons
    URI = '/mgmt/cm/shared/config/current/ltm/pool/%s/members'

    def __init__(self, *args, **kwargs):
        super(LtmPoolMembers, self).__init__(*args, **kwargs)


class LtmVirtual(BaseApiObject):
    __metaclass__ = LtmCommons
    URI = '/mgmt/cm/shared/config/current/ltm/virtual'

    def __init__(self, *args, **kwargs):
        super(LtmVirtual, self).__init__(*args, **kwargs)


class LtmRule(BaseApiObject):
    __metaclass__ = LtmCommons
    URI = '/mgmt/cm/shared/config/current/ltm/rule'

    def __init__(self, *args, **kwargs):
        super(LtmRule, self).__init__(*args, **kwargs)


class LtmProfile(BaseApiObject):
    __metaclass__ = LtmCommons
    URI = '/mgmt/cm/shared/config/current/ltm/profile'

    def __init__(self, *args, **kwargs):
        super(LtmProfile, self).__init__(*args, **kwargs)


class LtmMonitor(BaseApiObject):
    __metaclass__ = LtmCommons
    URI = '/mgmt/cm/shared/config/current/ltm/monitor'

    def __init__(self, *args, **kwargs):
        super(LtmProfile, self).__init__(*args, **kwargs)
