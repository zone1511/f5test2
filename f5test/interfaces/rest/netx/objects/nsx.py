'''
Created on May 23, 2014
@author: jwong

'''
from ...base import BaseApiObject
from .....base import AttrDict
from .....utils.wait import wait
import json


class TaskError(Exception):
    pass


class ServiceManagers(BaseApiObject):
    URI = 'api/2.0/si/servicemanagers'
    ITEM_URI = 'api/2.0/si/servicemanager/%s'

    def __init__(self, *args, **kwargs):
        super(ServiceManagers, self).__init__(*args, **kwargs)


class Services(BaseApiObject):
    URI = 'api/2.0/si/services'
    ITEM_URI = 'api/2.0/si/service/%s'

    def __init__(self, *args, **kwargs):
        super(Services, self).__init__(*args, **kwargs)


class DeploymentSpec(BaseApiObject):
    URI = Services.ITEM_URI + '/servicedeploymentspec'
    OVF_URI = Services.ITEM_URI + '/servicedeploymentspec/versioneddeploymentspec'

    def __init__(self, *args, **kwargs):
        super(DeploymentSpec, self).__init__(*args, **kwargs)
        self.setdefault('versionedDeploymentSpec', AttrDict())
        self.versionedDeploymentSpec.setdefault('hostVersion', '')
        self.versionedDeploymentSpec.setdefault('ovfUrl', '')
        self.versionedDeploymentSpec.setdefault('vmciEnabled', False)


class ServiceProfiles(BaseApiObject):
    URI = '/api/2.0/si/serviceprofiles'
    ITEM_URI = '/api/2.0/si/serviceprofile/%s'

    def __init__(self, *args, **kwargs):
        super(ServiceProfiles, self).__init__(*args, **kwargs)


class ServiceInstanceTemplates(BaseApiObject):
    URI = Services.ITEM_URI + '/serviceinstancetemplates'
    ITEM_URI = Services.ITEM_URI + '/serviceinstancetemplate'

    def __init__(self, *args, **kwargs):
        super(ServiceInstanceTemplates, self).__init__(*args, **kwargs)
        self.setdefault('serviceInstanceTemplate', AttrDict())
        self.serviceInstanceTemplate.setdefault('name', 'Service Instance')
        self.serviceInstanceTemplate.setdefault('instanceTemplateId', 'Service Instance')
        self.serviceInstanceTemplate.setdefault('requiredInstanceAttributes', '')
        self.serviceInstanceTemplate.setdefault('typedAttributes', '')


class ServiceInstances(BaseApiObject):
    URI = 'api/2.0/si/serviceinstances'
    ITEM_URI = 'api/2.0/si/serviceinstance'
    RUNTIME_URI = ITEM_URI + '/%s/runtimeinfos'
    RUNTIME_ITEM_URI = ITEM_URI + '/%s/runtimeinfo/%s/config'

    def __init__(self, *args, **kwargs):
        super(ServiceInstances, self).__init__(*args, **kwargs)

    def add_templtetypedattribute(self, value):
        self.serviceInstance.config.instanceTemplateTypedAttributes.typedAttribute.append(value)

    @staticmethod
    def wait(rest, name, timeout=60):
        if isinstance(rest.get(ServiceInstances.URI).serviceInstances.serviceInstance, list):
            ret = wait(lambda: rest.get(ServiceInstances.URI),
                       condition=lambda ret: name in [x.name for x in ret.serviceInstances.serviceInstance],
                       progress_cb=lambda ret: [x.name for x in ret.serviceInstances.serviceInstance],
                       timeout=30, interval=2)
            for item in ret.serviceInstances.serviceInstance:
                if item.name == name:
                    si = item

        else:
            ret = wait(lambda: rest.get(ServiceInstances.URI),
                       condition=lambda ret: name == ret.serviceInstances.serviceInstance.name,
                       progress_cb=lambda ret: name == ret.serviceInstances.serviceInstance.name,
                       timeout=30, interval=2)
            si = ret.serviceInstances.serviceInstance

        wait(lambda: rest.get(ServiceInstances.ITEM_URI + '/' + si.objectId),
             condition=lambda ret: ret.serviceInstance.runtimeInfos,
             progress_cb=lambda _: "Waiting for runtime infos...",
             timeout=30, interval=2)

        return rest.get(ServiceInstances.URI)


class Runtime(BaseApiObject):
    URI = ServiceInstances.ITEM_URI + '/%s/runtimeinfos'
    ITEM_URI = ServiceInstances.ITEM_URI + '/%s/runtimeinfo/%s'
    CONFIG_URI = ServiceInstances.ITEM_URI + '/%s/runtimeinfo/%s/config'
    OFF_STATE = ('OUT_OF_SERVICE')
    UNINSTALLED_STATE = ('NOT_INSTALLED')

    def __init__(self, *args, **kwargs):
        super(Runtime, self).__init__(*args, **kwargs)

    @staticmethod
    def wait(rest, service_instance, runtime_id, timeout=1200, interval=30):
        ret = wait(lambda: rest.get(Runtime.ITEM_URI % (service_instance, runtime_id)),
                   condition=lambda ret: not ret.serviceInstanceRuntimeInfo.installState in Runtime.UNINSTALLED_STATE,
                   progress_cb=lambda ret: "installState: %s" %
                               (ret.serviceInstanceRuntimeInfo.installState),
                   timeout=timeout, interval=interval)

        if ret.serviceInstanceRuntimeInfo.installState != 'ENABLED':
            msg = json.dumps(ret, sort_keys=True, indent=4, ensure_ascii=False)
            raise TaskError("Runtime failed.\n%s" % msg)

        return ret


class Edges(BaseApiObject):
    URI = 'api/4.0/edges'
    ITEM_URI = 'api/4.0/edges/%s'

    def __init__(self, *args, **kwargs):
        super(Edges, self).__init__(*args, **kwargs)


class LoadBalancer(BaseApiObject):
    URI = Edges.ITEM_URI + '/loadbalancer/config'

    def __init__(self, *args, **kwargs):
        super(LoadBalancer, self).__init__(*args, **kwargs)


class Virtualserver(BaseApiObject):
    URI = Edges.ITEM_URI + '/loadbalancer/config/virtualservers'
    ITEM_URI = Edges.ITEM_URI + '/loadbalancer/config/virtualservers/%s'

    def __init__(self, *args, **kwargs):
        super(Virtualserver, self).__init__(*args, **kwargs)


class Pool(BaseApiObject):
    URI = Edges.ITEM_URI + '/loadbalancer/config/pools'
    ITEM_URI = Edges.ITEM_URI + '/loadbalancer/config/pools/%s'

    def __init__(self, *args, **kwargs):
        super(Pool, self).__init__(*args, **kwargs)


class Nat(BaseApiObject):
    URI = Edges.ITEM_URI + '/nat/config'
    ITEM_URI = Edges.ITEM_URI + '/nat/config/rules/%s'

    def __init__(self, *args, **kwargs):
        super(Nat, self).__init__(*args, **kwargs)


class HeartBeat(BaseApiObject):
    URI = 'api/2.0/global/heartbeat'

    def __init__(self, *args, **kwargs):
        super(HeartBeat, self).__init__(*args, **kwargs)


class AddressPool(BaseApiObject):
    URI = '/api/2.0/services/ipam/pools/scope/globalroot-0'

    def __init__(self, *args, **kwargs):
        super(AddressPool, self).__init__(*args, **kwargs)
