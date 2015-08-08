'''
Created on Mar 18, 2015

@author: marepally
'''

from f5test.interfaces.rest.netx.objects.nsx import  ServiceInstances, LoadBalancer,\
    ServiceManagers, Pool, Virtualserver, ServiceInstanceTemplates,\
    Edges
import logging
from f5test.interfaces.rest.netx.resources import NetxResourceError
from f5test.utils.wait import wait_args, wait, StopWait
from f5test.commands.rest.base import NetxCommand
from f5test.commands.base import CommandError
import json
import copy

LOG = logging.getLogger(__name__)

uninstall_runtime=None
class UninstallRuntime(NetxCommand):
    
    """ Uninstall service runtime from NSX
    
    @param service_instance_id: Service instance Id #mandatory
    @type service_instance_id: string

    @param service_runtime_id: Service Runtime Id #mandatory 
    @type service_runtime_id: string
    
    @return: If service runtime is uninstalled?
    @type: Boolean    
    
    """
    
    def __init__(self,
                 service_instance_id,
                 service_runtime_id,
                 *args, **kwargs):
        super(UninstallRuntime, self).__init__(*args, **kwargs)
        self.nsx_rst_api = self.api
        self.service_instance_id = service_instance_id
        self.service_runtime_id = service_runtime_id
        
    def setup(self):
        
        def wait_on_uninstall(ret):
            if ret and ret.serviceInstanceRuntimeInfos and ret.serviceInstanceRuntimeInfos.serviceInstanceRuntimeInfo:
                if isinstance(ret.serviceInstanceRuntimeInfos.serviceInstanceRuntimeInfo, list):
                    for sir in ret.serviceInstanceRuntimeInfos.serviceInstanceRuntimeInfo:
                        if int(sir.id)==self.service_runtime_id:
                            return (sir.status == 'OUT_OF_SERVICE' and \
                                    sir.installState == 'NOT_INSTALLED')
                else:
                    return (ret.serviceInstanceRuntimeInfos.serviceInstanceRuntimeInfo.status == 'OUT_OF_SERVICE' and \
                                     ret.serviceInstanceRuntimeInfos.serviceInstanceRuntimeInfo.installState == 'NOT_INSTALLED')
            return True
                
        
        LOG.debug("Uninstalling runtime id = {0} on NSX".format(self.service_runtime_id))
        try:
            self.nsx_rst_api.post(ServiceInstances.RUNTIME_ITEM_URI % (self.service_instance_id, self.service_runtime_id), params_dict={'action': 'uninstall'})
        except NetxResourceError:
            pass    # ignore on error as on return we check for uninstall state else fail
        wait(lambda: self.nsx_rst_api.get(ServiceInstances.RUNTIME_URI % (self.service_instance_id)),
             condition=wait_on_uninstall,
             progress_cb=lambda x: "Waiting for runtime id={0} to uninstall".format(self.service_runtime_id),
             timeout=20, interval=4,
             timeout_message="runtime, id={0} could not be uninstalled".format(self.service_runtime_id))

remove_runtime=None
class RemoveRuntime(NetxCommand):
    
    """ Removes service runtime from NSX
    
    @param service_instance_id: Service instance Id #mandatory
    @type service_instance_id: string

    @param service_runtime_id: Service Runtime Id #mandatory 
    @type service_runtime_id: string
    
    @return: If service runtime is deleted?
    @type: Boolean    
    
    """
    
    def __init__(self,
                 service_instance_id,
                 service_runtime_id,
                 *args, **kwargs):
        super(RemoveRuntime, self).__init__(*args, **kwargs)
        self.nsx_rst_api = self.api
        self.service_instance_id = service_instance_id
        self.service_runtime_id = service_runtime_id

    def setup(self):
        LOG.debug("Deleting runtime id = {0} on NSX".format(self.service_runtime_id))
        try:
            self.nsx_rst_api.delete(ServiceInstances.RUNTIME_ITEM_DELETE_URI % (self.service_instance_id, self.service_runtime_id))
        except NetxResourceError:
            pass    # ignore on error as on return we check for delete state else fail
        wait(lambda: self.nsx_rst_api.get(ServiceInstances.RUNTIME_URI % (self.service_instance_id)),
             condition=lambda ret: ret.serviceInstanceRuntimeInfos is None,
             progress_cb=lambda x: "Waiting for runtime id={0} to be deleted".format(self.service_runtime_id),
             timeout=20, interval=4,
             timeout_message="runtime, id={0} could not be deleted".format(self.service_runtime_id))

remove_service_manager=None
class RemoveServiceManager(NetxCommand):
    
    """ Removes service manager from NSX
    
    @param manager_id: NSX Service Manager Id #mandatory
    @type manager_id: string
    
    @return: If service manager is removed/deleted?
    @type: Boolean
    
    """
    
    def __init__(self,
                 manager_id,
                 *args, **kwargs):
        super(RemoveServiceManager, self).__init__(*args, **kwargs)
        self.nsx_rst_api = self.api
        self.manager_id = manager_id
    
    def self(self):        
        LOG.debug("Delete NSX service manager id = {0}".format(self.manager_id))
        try:
            self.nsx_rst_api.delete(ServiceManagers.ITEM_URI % self.manager_id)
        except NetxResourceError:
            pass
        wait(lambda x: self.nsx_rst_api.get(ServiceManagers.URI),
             condition=lambda ret: self.manager_id in [sm.objectId for sm in ret.serviceManagers.serviceManager if sm.objectId==self.manager_id],
             progress_cb=lambda x: "Waiting on service manager deletion, id={0}".format(self.manager_id),
             timeout=20, interval=4,
             timeout_message="service manager, id={0} was not removed".format(self.manager_id))

check_service_manager=None
class CheckServiceManager(NetxCommand):
    
    """ Checks service manager on NSX
    
    @param manager_id: NSX Service Manager Id #mandatory
    @type manager_id: string
    
    @return: If service manager is available or not?
    @type: Boolean
    
    """
    
    def __init__(self,
                 manager_id,
                 *args, **kwargs):
        super(CheckServiceManager, self).__init__(*args, **kwargs)
        self.nsx_rst_api = self.api
        self.manager_id = manager_id
    
    def self(self):        
        LOG.debug("Checking NSX service manager id = {0}".format(self.manager_id))
        wait(lambda x: self.nsx_rst_api.get(ServiceManagers.URI),
             condition=lambda ret: self.manager_id in [sm.objectId for sm in ret.serviceManagers.serviceManager if sm.objectId==self.manager_id],
             progress_cb=lambda x: "Waiting on service manager deletion, id={0}".format(self.manager_id),
             timeout=20, interval=4,
             timeout_message="service manager, id={0} was not removed".format(self.manager_id))
        LOG.debug("NSX service manager id = {0} deleted on NSX".format(self.manager_id))

get_service_instance_template=None
class GetServiceInstanceTemplate(NetxCommand):
    
    """ Verifies service instance template on NSX Manager
    
    @param service_id: NSX service Id #mandatory
    @type service_id: String
    
    @param template_name: NSX service instance template name #mandatory
    @type service_id: String
    
    """
    NEW_VE_TYPED_ATTRIBUTES = ('F5-BIG-IP-MAKE-VE', 'F5-BIG-IP-VE-FQ-HOST-NAME', 'F5-BIG-IP-VE-ADMIN-PASSWORD', 'F5-BIG-IP-VE-OVF-URL',
                               'F5-BIG-IP-VE-OVF-NAME')
    EXISTING_TYPED_ATTRIBUTES = ()
    
    def __init__(self,
                 service_id,
                 template_name,
                 *args, **kwargs):
        super(GetServiceInstanceTemplate, self).__init__(*args, **kwargs)
        self.nsx_rst_api = self.api
        self.service_id = service_id
        self.template_name = template_name
    
    def setup(self):
        service = self.nsx_rst_api.get(ServiceInstanceTemplates.URI % self.service_id)
        template = service.serviceInstanceTemplates.serviceInstanceTemplate
        
        for currtemplate in template:
            if currtemplate.name == self.template_name:
                return (currtemplate.id, currtemplate.typedAttributes.typedAttribute)

create_service_instance_for_new=None
class CreateServiceInstanceForNew(NetxCommand):
    DEFAULT_DIRECTORY = "/project_data/api/xml/"
    
    """ Creates a service instance on NSX
    
    @param nsx_edge_id: NSX edge id #mandatory
    @type nsx_edge_id: String
    
    @param instance_name: Service instance name    #mandatory
    @type instance_name: String
    
    @param si_template_name: Service instance pay load template name    #mandatory only while creating service instance
    @type si_template_name: String
    
    @param vnics_template_name: Runtime vnic information pay load template name    #mandatory only while creating service instance
    @type vnics_template_name: String
    
    @param specs: Specification to successfully create a service instance    #mandatory
    @type specs: Attrdict
    
    @param template_format: A service instance pay load template format    # not mandatory and has a default value
    @type template_format: String
    
    """
    
    def __init__(self,
                 edge_id,
                 instance_name,
                 si_template_name,
                 vnics_template_name,
                 specs,
                 template_format='xml',
                 *args, **kwargs):
        super(CreateServiceInstanceForNew, self).__init__(*args, **kwargs)
        self.edge_id = edge_id
        self.nsx_rst_api = self.api
        self.instance_name = instance_name
        self.template_dir = specs.template_dir if specs.template_dir else self.DEFAULT_DIRECTORY 
        self.si_template_name = si_template_name
        self.vnics_template_name = vnics_template_name
        self.nsx = kwargs.pop('device') # Get the NSX device object 
        self.specs = specs
        self.template_format = template_format
    
    def setup(self):   
        LOG.debug("Creating NSX service instance on edge, id={0}".format(self.edge_id))
        payload = ServiceInstances().from_file(self.template_dir, self.si_template_name, fmt=self.template_format)
        vnic_payload = ServiceInstances().from_file(self.template_dir, self.vnics_template_name, fmt=self.template_format)

        # Change the name of the service instance runtime vm
        payload.serviceInstance.name = self.instance_name
        payload.serviceInstance.description = self.instance_name
        
        if self.specs.typed_attributes:
            payload.serviceInstance.config.instanceTemplateTypedAttributes.typedAttribute = self.specs.typed_attributes
        
        if self.specs.template_id:
            payload.serviceInstance.config.instanceTemplate.id = self.specs.template_id
            
        if self.specs.enable_ha:
            for attr in payload.serviceInstance.config.implementationAttributes.attribute:
                if attr.key == "haEnabled":
                    attr.value = True
                    break

        # replacing data store and resource pool corresponding to the NSX environment
        payload.serviceInstance.config.baseRuntimeConfig.deploymentScope.resourcePool = self.nsx.specs.resourcePool
        payload.serviceInstance.config.baseRuntimeConfig.deploymentScope.datastore = self.nsx.specs.datastore

        # associate the edge-id
        payload.serviceInstance.config.baseRuntimeConfig.runtimeInstanceId = self.edge_id
        payload.serviceInstance.config.baseRuntimeConfig.deploymentScope.nics.runtimeNicInfo = []    
        
        if self.specs.nic_interfaces:
            for ifc in self.specs.nic_interfaces:
                    vnic_payload.runtimeNicInfo.label = ifc.label
                    vnic_payload.runtimeNicInfo.index = ifc.index
                    vnic_payload.runtimeNicInfo.network.objectId = ifc.network.object_id
                    vnic_payload.runtimeNicInfo.connectivityType = ifc.connectivity_type
                    vnic_payload.runtimeNicInfo.ipAllocationType = ifc.ip_allocation_type
                    vnic_payload.runtimeNicInfo.ipPool.objectId = ifc.ippool.object_id
                    if ifc.connected:
                        vnic_payload.runtimeNicInfo.connected = ifc.connected
                    payload.serviceInstance.config.baseRuntimeConfig.deploymentScope.nics.runtimeNicInfo.append(copy.deepcopy(vnic_payload.runtimeNicInfo))

        if self.specs.service_id:
            payload.serviceInstance.service.objectId = self.specs.service_id
        
        return self.nsx_rst_api.post(ServiceInstances.ITEM_URI, payload)
    
create_service_instance_for_existing=None
class CreateServiceInstanceForExisting(NetxCommand):
    DEFAULT_DIRECTORY = "/project_data/api/xml/"
    
    """ Creates a service instance on NSX
    
    @param nsx_edge_id: NSX edge id #mandatory
    @type nsx_edge_id: String
    
    @param instance_name: Service instance name    #mandatory
    @type instance_name: String
    
    @param si_template_name: Service instance pay load template name    #mandatory only while creating service instance
    @type si_template_name: String
    
    @param vnics_template_name: Runtime vnic information pay load template name    #mandatory only while creating service instance
    @type vnics_template_name: String
    
    @param specs: Specification to successfully create a service instance    #mandatory
    @type specs: Attrdict
    
    @param template_format: A service instance pay load template format    # not mandatory and has a default value
    @type template_format: String
    
    """
    
    def __init__(self,
                 edge_id,
                 instance_name,
                 si_template_name,
                 vnics_template_name,
                 specs,
                 template_format='xml',
                 *args, **kwargs):
        super(CreateServiceInstanceForExisting, self).__init__(*args, **kwargs)
        self.edge_id = edge_id
        self.nsx_rst_api = self.api
        self.instance_name = instance_name
        self.template_dir = specs.template_dir if specs.template_dir else self.DEFAULT_DIRECTORY 
        self.si_template_name = si_template_name
        self.vnics_template_name = vnics_template_name
        self.nsx = kwargs.pop('device')
        self.specs = specs
        self.template_format = template_format
    
    def setup(self):   
        LOG.debug("Creating NSX service instance on edge, id={0}".format(self.edge_id))
        payload = ServiceInstances().from_file(self.template_dir, self.si_template_name, fmt=self.template_format)

        # Change the name of the service instance runtime vm
        payload.serviceInstance.name = self.instance_name
        payload.serviceInstance.description = self.instance_name
        
        if self.specs.typed_attributes:
            payload.serviceInstance.config.instanceTemplateTypedAttributes = self.specs.typed_attributes
        
        if self.specs.template_id:
            payload.serviceInstance.config.instanceTemplateTypedAttributes.id = self.specs.template_id

        # replacing data store and resource pool corresponding to the NSX environment
        payload.serviceInstance.config.baseRuntimeConfig.deploymentScope.resourcePool = self.nsx.specs.resourcePool
        payload.serviceInstance.config.baseRuntimeConfig.deploymentScope.datastore = self.nsx.specs.datastore

        # associate the edge-id
        payload.serviceInstance.config.baseRuntimeConfig.runtimeInstanceId = self.edge_id
        payload.serviceInstance.config.baseRuntimeConfig.deploymentScope.nics.runtimeNicInfo = []    
        
        if self.specs.nic_interfaces:
            for ifc in self.specs.nic_interfaces:
                    vnic_payload = ServiceInstances().from_file(self.template_dir, self.vnics_template_name, fmt=self.template_format)
                    vnic_payload.runtimeNicInfo.label = ifc.label
                    vnic_payload.runtimeNicInfo.index = ifc.index
                    vnic_payload.runtimeNicInfo.network.objectId = ifc.network.object_id
                    vnic_payload.runtimeNicInfo.connectivityType = ifc.connectivity_type
                    vnic_payload.runtimeNicInfo.ipAllocationType = ifc.ip_allocation_type
                    if ifc.ip_allocation_type == "IP_POOL":
                        vnic_payload.runtimeNicInfo.ipPool.objectId = ifc.ippool.object_id
                    elif ifc.ip_allocation_type == "DHCP":
                        vnic_payload.runtimeNicInfo.pop("ipPool")
                    payload.serviceInstance.config.baseRuntimeConfig.deploymentScope.nics.runtimeNicInfo.append(vnic_payload.runtimeNicInfo)

        if self.specs.service_id:
            payload.serviceInstance.service.objectId = self.specs.service_id
        
        return self.nsx_rst_api.post(ServiceInstances.ITEM_URI, payload)

check_service_instance=None
class CheckServiceInstance(NetxCommand):
    """ Removes service instance on NSX
    
    @param service_intance_id: Service instance id    #mandatory
    @type service_intance_id: String
    
    """
    
    def __init__(self,
                 service_intance_id,
                 *args, **kwargs):
        super(CheckServiceInstance, self).__init__(*args, **kwargs)
        self.nsx_rst_api = self.api
        self.service_intance_id = service_intance_id
    
    def wait_on_remove(self):
        try:
            instances = self.nsx_rst_api.get(ServiceInstances.URI)
            if instances and instances.serviceInstances and instances.serviceInstances.serviceInstance:
                if isinstance(instances.serviceInstances.serviceInstance, list):
                    for si in instances.serviceInstances.serviceInstance:
                        if si.objectId == self.service_intance_id:
                            return False
                elif instances.serviceInstances.serviceInstance.objectId == self.service_intance_id:    # When there is only 1 instance on NSX
                    return False
            return True # When there are no service instances on NSX  
        except NetxResourceError:
            return False
    
    def setup(self):
        LOG.debug("Check for service instance id = {0} on NSX".format(self.service_intance_id))
        wait_args(self.wait_on_remove,
                  condition=lambda x: x,
                  progress_cb=lambda x: "checking for service instance id={0}".format(self.service_intance_id),
                  timeout=20, interval=4,
                  timeout_message="Service instance, id={0} was not removed on edge".format(self.service_intance_id))
        LOG.debug("service instance id = {0} deleted on NSX".format(self.service_intance_id))

create_load_balancer_for_new=None
class CreateLoadBalancerForNew(NetxCommand):
    DEFAULT_DIRECTORY = "/project_data/api/xml/"
    
    """ Creates load balancer service on NSX edge
    
    @param edge_id: NSX edge id #mandatory
    @type edge_id: String
    
    @param instance_name: Load balancer service name    #mandatory
    @type instance_name: String
    
    @param lb_template_name: A load balancer pay load template name    #mandatory only while inserting load balancer
    @type lb_template_name: String
    
    @param vnics_template_name: Runtime vnic information pay load template name    #mandatory only while creating service instance
    @type vnics_template_name: String
    
    @param specs: Specification to successfully insert a load balancer service on NSX edge    #mandatory
    @type specs: Attrdict
    
    @param template_format: A load balancer service pay load template format    # not mandatory and has a default value
    @type template_format: String
    
    """
    
    def __init__(self,
                 edge_id,
                 instance_name,
                 lb_template_name,
                 vnics_template_name,
                 specs,
                 template_format='xml',
                 *args, **kwargs):
        super(CreateLoadBalancerForNew, self).__init__(*args, **kwargs)
        self.edge_id = edge_id
        self.nsx_rst_api = self.api
        self.instance_name = instance_name
        self.template_dir = specs.template_dir if specs.template_dir else self.DEFAULT_DIRECTORY
        self.lb_template_name = lb_template_name
        self.vnics_template_name = vnics_template_name
        self.template_format = template_format
        self.specs = specs

    def setup(self):   
        LOG.debug("Inserting load balancer service on nsx edge, id={0}".format(self.edge_id))
        template = LoadBalancer().from_file(self.template_dir, self.lb_template_name, fmt=self.template_format)
        vnic_payload = ServiceInstances().from_file(self.template_dir, self.vnics_template_name, fmt=self.template_format)
        gsi = template.loadBalancer.globalServiceInstance
        
        if self.specs.service_instance_id:
            gsi.serviceInstanceId = self.specs.service_instance_id
        
        gsi.name = self.instance_name
        
        if self.specs.service_id:
            gsi.serviceId = self.specs.service_id
        
        if self.specs.service_name:
            gsi.serviceName = self.specs.service_name
            
        if self.specs.template_id:
            gsi.instanceTemplateId = self.specs.template_id
            gsi.instanceTemplateUniqueId = self.specs.template_id
        
        if self.specs.typed_attributes:
            gsi.instanceTemplateTypedAttributes.typedAttribute = self.specs.typed_attributes
        
        if self.specs.deployment_spec_id:
            gsi.versionedDeploymentSpecId = self.specs.deployment_spec_id 
        
        gsi.runtimeNicInfo = []
        if self.specs.nic_interfaces:
            for ifc in self.specs.nic_interfaces:
                vnic_payload.runtimeNicInfo.label = ifc.label
                vnic_payload.runtimeNicInfo.index = ifc.index
                vnic_payload.runtimeNicInfo.network.objectId = ifc.network.object_id
                vnic_payload.runtimeNicInfo.connectivityType = ifc.connectivity_type
                vnic_payload.runtimeNicInfo.ipAllocationType = ifc.ip_allocation_type
                vnic_payload.runtimeNicInfo.ipPool.objectId = ifc.ippool.object_id
                gsi.runtimeNicInfo.append(copy.deepcopy(vnic_payload.runtimeNicInfo))

        wait_args(self.retry_insert_lb, func_args=[template], condition=lambda state: state,
                  progress_cb=lambda state: "Waiting to PUT global service instance",
                  timeout=60, interval=5,
                  timeout_message="Failed to insert loadbalancer service after {0}s")

        return True
    
    def retry_insert_lb(self, payload):
        """ Check whether previous PUT succeeded """
        lb = self.nsx_rst_api.get(LoadBalancer.URI % self.edge_id)
        if not lb.loadBalancer.globalServiceInstance:    # if previous PUT failed, retry
            lb.loadBalancer.update(payload.loadBalancer)
            try:
                self.nsx_rst_api.put(LoadBalancer.URI % self.edge_id, payload=lb)
            except NetxResourceError:
                return False
        elif lb.loadBalancer.globalServiceInstance and lb.loadBalancer.globalServiceInstance.serviceInstanceId == self.specs.service_instance_id:
            return True
        elif lb.loadBalancer.globalServiceInstance and lb.loadBalancer.globalServiceInstance.serviceInstanceId != self.specs.service_instance_id:
            msg = json.dumps(lb, sort_keys=True, indent=4, ensure_ascii=False)
            raise StopWait("{0} has an existing global service instance that's not removed. Edge cannot be used \n {1}".format(self.edge_id, msg))

create_load_balancer_for_existing=None
class CreateLoadBalancerForExisting(NetxCommand):
    DEFAULT_DIRECTORY = "/project_data/api/xml/"
    
    """ Creates load balancer service on NSX edge
    
    @param edge_id: NSX edge id #mandatory
    @type edge_id: String
    
    @param instance_name: Load balancer service name    #mandatory
    @type instance_name: String
    
    @param lb_template_name: A load balancer pay load template name    #mandatory only while inserting load balancer
    @type lb_template_name: String
    
    @param vnics_template_name: Runtime vnic information pay load template name    #mandatory only while creating service instance
    @type vnics_template_name: String
    
    @param specs: Specification to successfully insert a load balancer service on NSX edge    #mandatory
    @type specs: Attrdict
    
    @param template_format: A load balancer service pay load template format    # not mandatory and has a default value
    @type template_format: String
    
    """
    
    def __init__(self,
                 edge_id,
                 instance_name,
                 lb_template_name,
                 vnics_template_name,
                 specs,
                 template_format='xml',
                 *args, **kwargs):
        super(CreateLoadBalancerForExisting, self).__init__(*args, **kwargs)
        self.edge_id = edge_id
        self.nsx_rst_api = self.api
        self.instance_name = instance_name
        self.template_dir = specs.template_dir if specs.template_dir else self.DEFAULT_DIRECTORY
        self.lb_template_name = lb_template_name
        self.vnics_template_name = vnics_template_name
        self.template_format = template_format
        self.specs = specs

    def setup(self):   
        LOG.debug("Inserting load balancer service on nsx edge, id={0}".format(self.edge_id))
        template = LoadBalancer().from_file(self.template_dir, self.lb_template_name, fmt=self.template_format)
        gsi = template.loadBalancer.globalServiceInstance
        
        if self.specs.service_instance_id:
            gsi.serviceInstanceId = self.specs.service_instance_id
        
        gsi.name = self.instance_name
        
        if self.specs.service_id:
            gsi.serviceId = self.specs.service_id
        
        if self.specs.service_name:
            gsi.serviceName = self.specs.service_name
            
        if self.specs.template_id:
            gsi.instanceTemplateId = self.specs.template_id
            gsi.instanceTemplateUniqueId = self.specs.template_id
        
        if self.specs.typed_attributes:
            gsi.instanceTemplateTypedAttributes = self.specs.typed_attributes
        
        gsi.runtimeNicInfo = []
        if self.specs.nic_interfaces:
            for ifc in self.specs.nic_interfaces:
                vnic_payload = ServiceInstances().from_file(self.template_dir, self.vnics_template_name, fmt=self.template_format)
                vnic_payload.runtimeNicInfo.label = ifc.label
                vnic_payload.runtimeNicInfo.index = ifc.index
                vnic_payload.runtimeNicInfo.network.objectId = ifc.network.object_id
                vnic_payload.runtimeNicInfo.connectivityType = ifc.connectivity_type
                vnic_payload.runtimeNicInfo.ipAllocationType = ifc.ip_allocation_type
                if ifc.ip_allocation_type == "IP_POOL":
                    vnic_payload.runtimeNicInfo.ipPool.objectId = ifc.ippool.object_id
                elif ifc.ip_allocation_type == "DHCP":
                    vnic_payload.runtimeNicInfo.pop("ipPool")
                gsi.runtimeNicInfo.append(vnic_payload.runtimeNicInfo)

        wait_args(self.retry_insert_lb, func_args=[template], condition=lambda state: state,
                  progress_cb=lambda state: "Waiting to PUT global service instance",
                  timeout=60, interval=5,
                  timeout_message="Failed to insert loadbalancer service after {0}s")
            
        return True
    
    def retry_insert_lb(self, payload):
        """ Check whether previous PUT succeeded """
        lb = self.nsx_rst_api.get(LoadBalancer.URI % self.edge_id)
        if not lb.loadBalancer.globalServiceInstance:    # if previous PUT failed, retry
            lb.loadBalancer.update(payload.loadBalancer)
            try:
                self.nsx_rst_api.put(LoadBalancer.URI % self.edge_id, payload=lb)
            except NetxResourceError:
                return False
        elif lb.loadBalancer.globalServiceInstance and lb.loadBalancer.globalServiceInstance.serviceInstanceId == self.specs.service_instance_id:
            return True
        elif lb.loadBalancer.globalServiceInstance and lb.loadBalancer.globalServiceInstance.serviceInstanceId != self.specs.service_instance_id:
            msg = json.dumps(lb, sort_keys=True, indent=4, ensure_ascii=False)
            raise StopWait("{0} has an existing global service instance. Edge cannot be used \n {1}".format(self.edge_id, msg))
    
remove_load_balancer=None
class RemoveLoadBalancer(NetxCommand):
    
    """
    
    @param edge_id: NSX edge id #mandatory
    @type edge_id: String
    
    @param pay_load: pay load to remove load balancer service    #mandatory
    @type pay_load: Attrdict
    
    """
    
    def __init__(self,
                 edge_id,
                 pay_load,
                 *args, **kwargs):
        super(RemoveLoadBalancer, self).__init__(*args, **kwargs)
        self.edge_id = edge_id
        self.nsx_rst_api = self.api
        self.pay_load = pay_load
    
    def setup(self):
        LOG.debug('Removing the load balancer service on NSX edge id = {0}'.format(self.edge_id))
        wait_args(lambda: self.nsx_rst_api.put(LoadBalancer.URI % self.edge_id, payload=self.pay_load),
                  condition=lambda _: self.check_lb_state,
                  progress_cb=lambda x: "Waiting to remove load balancer on nsx edge, id={0}".format(self.edge_id),
                  timeout=20, interval=4,
                  timeout_message="load balancer was not removed on edge, id={0}".format(self.edge_id))
    
    def check_lb_state(self, _):
        lb = self.nsx_rst_api.get(LoadBalancer.URI % self.edge_id)
        if not lb.loadBalancer.globalServiceInstance:
            return True
        return False

create_pool=None
class CreatePool(NetxCommand):
    DEFAULT_DIRECTORY = "/project_data/api/xml/"
    
    """
    
    @param nsx_edge_id: NSX edge id #mandatory
    @type nsx_edge_id: String
    
    @param pool_name: pool name    #mandatory
    @type pool_name: String
    
    @param algorithm: load balancing algorithm for application delivery    #mandatory
    @type algorithm: String
    
    @param specs: Specification to successfully insert a pool with pool members on NSX edge    #mandatory
    @type specs: Attrdict
    
    @param pool_template_name: A pool pay load template name    #mandatory only while creating a pool on NSX edge
    @type pool_template_name: String
    
    @param member_template_name: A pool member pay load template name    #mandatory only while creating a pool member on NSX edge in a given pool
    @type member_template_name: String
    
    @param template_format: referenced template format    # not mandatory and has a default value
    @type template_format: String
    
    """
    
    def __init__(self,
                 edge_id,
                 pool_name,
                 algorithm,
                 specs,
                 pool_template_name,
                 member_template_name,
                 template_format='xml',
                 *args, **kwargs):
        super(CreatePool, self).__init__(*args, **kwargs)
        self.edge_id = edge_id
        self.nsx_rst_api = self.api
        self.pool_name = pool_name
        self.algorithm = algorithm
        self.template_dir = specs.template_dir if specs.template_dir else self.DEFAULT_DIRECTORY
        self.pool_template_name = pool_template_name
        self.member_template_name = member_template_name
        self.template_format = template_format
        self.specs = specs

    def setup(self):
        pload = Pool().from_file(self.template_dir, self.pool_template_name, self.template_format)
        mload = Pool().from_file(self.template_dir, self.member_template_name, self.template_format)
        pload.pool.name = self.pool_name
        pload.pool.algorithm = self.algorithm
        pload.pool.member = []
        if self.specs and self.specs.members:
            for item in self.specs.members:
                mload.member.update(item)
                pload.pool.member.append(copy.deepcopy(mload.member))
                
        self.nsx_rst_api.post(Pool().URI % self.edge_id, payload=pload)
        return True
    
get_pool=None
class GetPool(NetxCommand):
    """
    
    @param nsx_edge_id: NSX edge id #mandatory
    @type nsx_edge_id: String
    
    @param pool_name: pool name    #mandatory
    @type pool_name: String
    
    """
    
    def __init__(self,
                 edge_id,
                 pool_name,
                 *args, **kwargs):
        super(GetPool, self).__init__(*args, **kwargs)
        self.nsx_rst_api = self.api
        self.edge_id = edge_id
        self.pool_name=pool_name
    
    def setup(self):
        lb = self.nsx_rst_api.get(LoadBalancer.URI % self.edge_id)
        if isinstance(lb.loadBalancer.pool, list):
            for pool in lb.loadBalancer.pool:
                if pool.name==self.pool_name:
                    return pool.poolId
        else:
            return lb.loadBalancer.pool.poolId
        return None
    
remove_pool=None
class RemovePool(NetxCommand):
    """
    
    @param nsx_edge_id: NSX edge id #mandatory
    @type nsx_edge_id: String
    
    @param pool_name: pool name    #mandatory
    @type pool_name: String
    
    @param payload: pay load to remove pool from load balancer service    #mandatory
    @type payload: Attrdict
    
    """
    
    def __init__(self,
                 edge_id,
                 pool_name,
                 pay_load,
                 *args, **kwargs):
        super(RemovePool, self).__init__(*args, **kwargs)
        self.nsx_rst_api = self.api
        self.edge_id = edge_id
        self.pool_name = pool_name
        self.pay_load = pay_load
  
    def setup(self):
        
        def wait_on_remove(lb_resp):
            return lb_resp.loadBalancer.pool == None

        LOG.debug('Removing the pool = {0} from NSX'.format(self.pool_name))
        try:
            self.nsx_rst_api.put(LoadBalancer.URI % self.edge_id, payload=self.pay_load)
        except NetxResourceError:
            pass
        wait(lambda: self.nsx_rst_api.get(LoadBalancer.URI % self.edge_id),
             condition=lambda ret: ret.loadBalancer.pool is None,
             progress_cb=lambda x: "Waiting to remove pool nsx edge, id={0}".format(self.edge_id),
             timeout=20, interval=4,
             timeout_message="Pool was not removed on edge, id={0}".format(self.edge_id))

create_virtual_server=None
class CreateVirtualServer(NetxCommand):
    DEFAULT_DIRECTORY = "/project_data/api/xml/"
    
    """
    
    @param nsx_edge_id: NSX edge id #mandatory
    @type nsx_edge_id: String
    
    @param virtual_server_name: virtual server name    #mandatory
    @type virtual_server_name: String
    
    @param pool_id: existing pool id on NSX edge. This will be the default pool on the virtual server being created.    #mandatory
    @type pool_id: String
    
    @param vendor: vendor template on NSX edge. Corresponds to catalog on Big-IQ.    #mandatory
    @type vendor: String
    
    @param pay_load: pay load to create virtual server from load balancer service    #mandatory
    @type pay_load: Attrdict
    
    @param template_name: A virtual server pay load template name    #mandatory only while creating a virtual server NSX edge
    @type template_name: String
    
    @param template_format: referenced template format    # not mandatory and has a default value
    @type template_format: String
    
    """
    
    def __init__(self,
                 edge_id,
                 virtual_server_name,
                 pool_id,
                 vendor,
                 specs,
                 template_name,
                 template_format='xml',
                 *args, **kwargs):
        super(CreateVirtualServer, self).__init__(*args, **kwargs)
        self.edge_id = edge_id
        self.nsx_rst_api = self.api
        self.virtual_server_name = virtual_server_name
        self.pool_id = pool_id
        self.vendor = vendor
        self.nsx = kwargs.pop('device')
        self.template_dir = specs.template_dir if specs.template_dir else self.DEFAULT_DIRECTORY
        self.template_name = template_name
        self.template_format = template_format
        self.specs = specs

    def setup(self):
        LOG.debug("Creating Virtual Server: {0}".format(self.virtual_server_name))
        payload = Virtualserver().from_file(self.template_dir, self.template_name, fmt=self.template_format)
        payload.virtualServer.name = self.virtual_server_name

        payload.virtualServer.defaultPoolId = self.pool_id
        
        payload.virtualServer.vendorProfile.vendorTemplateName = self.vendor.name
        payload.virtualServer.vendorProfile.vendorTemplateId = self.vendor.id
        payload.virtualServer.ipPoolId = self.nsx.specs.ext_nic.ip_pool_id
        payload.virtualServer.ipPoolName = self.nsx.specs.ext_nic.ip_pool_name
        
        if self.specs.ssl_cert and self.specs.ssl_key:  # used only when deploying ssl-offload iapp
            for attr in payload.virtualServer.vendorProfile.vendorTypedAttributes.typedAttribute:
                if attr.key in "ssl__cert":
                    attr.value=self.specs.ssl_cert
                elif attr.key in "ssl__key":
                    attr.value=self.specs.ssl_key

        self.nsx_rst_api.post(Virtualserver.URI % self.edge_id, payload=payload)

        vs = self.nsx_rst_api.get(Virtualserver.URI % self.edge_id).loadBalancer.virtualServer
        return vs.virtualServerId

remove_virtual_server=None
class RemoveVirtualServer(NetxCommand):
    
    """
    
    @param nsx_edge_id: NSX edge id #mandatory
    @type nsx_edge_id: String
    
    @param virtual_server_id: virtual server name    #mandatory
    @type virtual_server_id: String
    
    @param pay_load: pay load to remove virtual server from load balancer service    #mandatory
    @type pay_load: Attrdict
    
    """
    
    def __init__(self,
                 edge_id,
                 virtual_server_id,
                 pay_load,
                 *args, **kwargs):
        super(RemoveVirtualServer, self).__init__(*args, **kwargs)
        self.edge_id = edge_id
        self.nsx_rst_api = self.api
        self.virtual_server_id = virtual_server_id
        self.pay_load = pay_load
        
    def setup(self):
        LOG.debug('Removing the virtual server = {0} from NSX'.format(self.virtual_server_id))
        try:
            self.nsx_rst_api.put(LoadBalancer.URI % self.edge_id, payload=self.pay_load)
        except NetxResourceError:
            pass
        wait(lambda: self.nsx_rst_api.get(LoadBalancer.URI % self.edge_id),
             condition=lambda ret: ret.loadBalancer.virtualServer is None,
             progress_cb=lambda x: "Waiting to remove virtual server on nsx edge, id={0}".format(self.edge_id),
             timeout=20, interval=4,
             timeout_message="Virtual Server was not removed on edge, id={0}".format(self.edge_id))
        LOG.debug('Removed the virtual server = {0} from NSX'.format(self.virtual_server_id))

check_virtual_server=None
class CheckVirtualServer(NetxCommand):
    
    """
    
    @param nsx_edge_id: NSX edge id #mandatory
    @type nsx_edge_id: String
    
    @param virtual_server_id: virtual server name    #mandatory
    @type virtual_server_id: String
    
    """
    
    def __init__(self,
                 edge_id,
                 virtual_server_id,
                 *args, **kwargs):
        super(CheckVirtualServer, self).__init__(*args, **kwargs)
        self.edge_id = edge_id
        self.nsx_rst_api = self.api
        self.virtual_server_id = virtual_server_id
        
    def setup(self):
        LOG.debug('Checking for the virtual server = {0} from NSX'.format(self.virtual_server_id))
        wait(lambda: self.nsx_rst_api.get(LoadBalancer.URI % self.edge_id),
             condition=lambda ret: ret.loadBalancer.virtualServer is None,
             progress_cb=lambda x: "Waiting to remove virtual server on edge, id={0}".format(self.edge_id),
             timeout=20, interval=4,
             timeout_message="Virtual Server was not removed on edge, id={0}".format(self.edge_id))
        LOG.debug('Removed the virtual server, id = {0} from NSX'.format(self.virtual_server_id))

create_undeployed_edge=None
class CreateUndeployedEdge(NetxCommand):
    DEFAULT_DIRECTORY = "/project_data/api/xml/"
    
    """ Creates edge in undeployed mode on NSX
    
    @param nsx_edge_id: NSX edge id #mandatory
    @type nsx_edge_id: String
    
    @param edge_name: Name of the edge to be created #mandatory
    @type edge_name: String
    
    @param template_name: Edge pay load template name    #mandatory only while creating NSX edge
    @type template_name: String
    
    @param template_format: referenced template format    # not mandatory and has a default value
    @type template_format: String
    
    """
    
    def __init__(self,
                 edge_name,
                 specs,
                 template_name,
                 template_format='xml',
                 *args, **kwargs):
        super(CreateUndeployedEdge, self).__init__(*args, **kwargs)
        self.nsx_rst_api = self.api
        self.edge_name = edge_name
        self.nsx = kwargs.pop('device')
        self.template_dir = specs.template_dir if specs.template_dir else self.DEFAULT_DIRECTORY
        self.template_name = template_name
        self.template_format = template_format
        self.specs = specs
        
    def setup(self):
            payload = Edges().from_file(self.template_dir, self.template_name, fmt=self.template_format)
            payload.edge.appliances.appliance.datastoreId = self.nsx.specs.datastore
            payload.edge.appliances.appliance.hostId = self.nsx.specs.hostId
            payload.edge.appliances.appliance.resourcePoolId = self.nsx.specs.resourcePool
            payload.edge.datacenterMoid = self.nsx.specs.datacenterMoid
            payload.edge.name = self.edge_name
            if self.specs.enable_ha:
                payload.edge.features.highAvailability.enabled = self.specs.enable_ha 
            try:
                self.nsx_rst_api.post(Edges.URI, payload=payload)
                LOG.debug("created NSX {0} in undeployed mode".format(self.edge_name))
            except NetxResourceError:
                raise CommandError("failed to create a nsx edge in undeployed mode")

get_edge_id=None
class GetEdgeId(NetxCommand):
    
    """ Get's an edge on NSX
    
    @param edge_name: Name of the edge #mandatory
    @type edge_name: String
    
    @return edge_id: NSX edge id corresponding to edge_name
    @type: String
    
    """
    
    def __init__(self,
                 edge_name,
                 *args, **kwargs):
        super(GetEdgeId, self).__init__(*args, **kwargs)
        self.nsx_rst_api = self.api
        self.edge_name = edge_name
    
    def setup(self):
        edges = self.nsx_rst_api.get(Edges.URI)
        if edges.pagedEdgeList and edges.pagedEdgeList.edgePage and edges.pagedEdgeList.edgePage.edgeSummary:
            if isinstance(edges.pagedEdgeList.edgePage.edgeSummary, list):
                for es in edges.pagedEdgeList.edgePage.edgeSummary:
                    if es.name == self.edge_name:
                        return es.objectId
            else:
                es = edges.pagedEdgeList.edgePage.edgeSummary
                if es.name == self.edge_name:
                    return es.objectId
        else:
            raise AssertionError ("The edge {0} was not found NSX.".format(self.edge_name))

check_edge=None
class CheckEdge(NetxCommand):
    
    """ Checks for an edge on NSX
    
    @param edge_id: edge Id on NSX #mandatory
    @type edge_id: String
    
    @return : True if edge is available on NSX
    @type: Boolean
    
    """
    
    def __init__(self,
                 edge_id,
                 *args, **kwargs):
        super(CheckEdge, self).__init__(*args, **kwargs)
        self.edge_id = edge_id
        self.nsx_rst_api = self.api
    
    def setup(self):
        edges = self.nsx_rst_api.get(Edges.URI)
        if edges.pagedEdgeList and edges.pagedEdgeList.edgePage and edges.pagedEdgeList.edgePage.edgeSummary:
            if isinstance(edges.pagedEdgeList.edgePage.edgeSummary, list):
                for es in edges.pagedEdgeList.edgePage.edgeSummary:
                    if es.objectId == self.edge_id:
                        return True
            else:
                es = edges.pagedEdgeList.edgePage.edgeSummary
                if es.objectId == self.edge_id:
                    return True
        else:
            return False

delete_edge=None
class DeleteEdge(NetxCommand):
    
    """ Deletes an edge on NSX
    
    @return edge_id: NSX edge id
    @type: String
    
    """
    
    def __init__(self,
                 edge_id,
                 *args, **kwargs):
        super(DeleteEdge, self).__init__(*args, **kwargs)
        self.nsx_rst_api = self.api
        self.edge_id = edge_id
        
    def check(self, edges):
        if edges and edges.pagedEdgeList and edges.pagedEdgeList.edgePage and edges.pagedEdgeList.edgePage.edgeSummary:
            if isinstance(edges.pagedEdgeList.edgePage.edgeSummary, list):
                for es in edges.pagedEdgeList.edgePage.edgeSummary:
                    if es.objectId == self.edge_id:
                        return False
            else:
                es = edges.pagedEdgeList.edgePage.edgeSummary
                if es.objectId == self.edge_id:
                    return False
        return True
    
    def setup(self):
        try:
            self.nsx_rst_api.delete(Edges.ITEM_URI % self.edge_id)
        except NetxResourceError:
            pass
        wait_args(self.check, func_args=[self.nsx_rst_api.get(Edges.URI)],
                  condition=lambda x: x,
                  progress_cb=lambda x: "Waiting for edge, id={0} to be deleted".format(self.edge_id),
                  timeout=20, interval=4,
                  timeout_message="edge, id={0} could not be deleted".format(self.edge_id))