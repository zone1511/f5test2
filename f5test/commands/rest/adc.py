'''
Created on May 26, 2015

@author: j.zhan@f5.com
'''

from .base import IcontrolRestCommand
from ...base import AttrDict
from ...interfaces.rest.emapi.objects.shared import ConfigDeploy, RefreshWorkingConfig, RefreshCurrentConfig
from ...interfaces.rest.emapi.objects.system import MachineIdResolver
import logging


LOG = logging.getLogger(__name__)

LTM_NODE             = 'ltm/node'
LTM_POOL             = 'ltm/pool'
LTM_VIRTUAL          = 'ltm/virtual'
LTM_VIRTUAL_ADDRESS  = 'ltm/virtual-address'
LTM_RULE             = 'ltm/rule'
LTM_PROFILE_HTTP     = 'ltm/profile/http'
LTM_MONITOR_HTTP     = 'ltm/monitor/http'

POOL_MEMBER_TRANS_URI = 'https://localhost/mgmt/cm/shared/config/transform/ltm/pool/members'
POOL_MEMBER_STATE_KIND = 'cm:shared:config:%s:ltm:pool:members:poolmemberstate'

deploy_adc_objects = None
class DeployAdcObjects(IcontrolRestCommand):  # @IgnorePep8
    """Deploy ADC objects to bigip.

    @param name: deploy task name
    @type name: string

    @description: description of the deploy task
    @type: string

    @device_id: the id of the target bigip device
    @type: string
    
    """
    def __init__(self, name, description, device_id, *args, **kwargs):
        super(DeployAdcObjects, self).__init__(*args, **kwargs)
        self.name = name
        self.description = description
        self.device_id = device_id

    def setup(self):
        LOG.info("Deploy adc object to machine %s ..." % self.device_id)
        payload = ConfigDeploy()
        payload.name = self.name
        payload.description = self.description
        payload.configPaths.append({'icrObjectPath':LTM_NODE})
        payload.configPaths.append({'icrObjectPath':LTM_POOL})
        payload.configPaths.append({'icrObjectPath':LTM_VIRTUAL})
        if self.ifc.version >= 'bigiq 4.6.0':
            LOG.info("For new object models after 4.6.0")
            payload.configPaths.append({'icrObjectPath':LTM_VIRTUAL_ADDRESS})
            payload.configPaths.append({'icrObjectPath':LTM_RULE})
            payload.configPaths.append({'icrObjectPath':LTM_PROFILE_HTTP})
            payload.configPaths.append({'icrObjectPath':LTM_MONITOR_HTTP})
        payload.kindTransformMappings.append(
                                      {
                                        'managementAuthorityKind':POOL_MEMBER_STATE_KIND % 'current',
                                        'transformUri':POOL_MEMBER_TRANS_URI
                                      }
                                    )
        payload.kindTransformMappings.append(
                                      {
                                        'managementAuthorityKind':POOL_MEMBER_STATE_KIND % 'working',
                                        'transformUri':POOL_MEMBER_TRANS_URI
                                      }
                                    )
        payload.deviceReference.set('https://localhost' + MachineIdResolver.ITEM_URI % self.device_id)
        task = self.api.post(ConfigDeploy.URI, payload)
        ConfigDeploy.wait(self.api, task, timeout=60)

   
sync_adc_objects = None
class SyncAdcObjects(IcontrolRestCommand):  # @IgnorePep8
    """Syn working config and current config from bigip ...

    @device_id: the id of the target bigip device
    @type: string

    """
    def __init__(self, device_id, *args, **kwargs):
        super(SyncAdcObjects, self).__init__(*args, **kwargs)
        self.device_id = device_id

    def setup(self):

        LOG.info("Syn working config and current config from bigip ...")
        LOG.debug('device_id is %s' % self.device_id)
        payload = RefreshCurrentConfig()
        payload.configPaths.append({'icrObjectPath':LTM_NODE})
        payload.configPaths.append({'icrObjectPath':LTM_POOL})
        payload.configPaths.append({'icrObjectPath':LTM_VIRTUAL})
        payload.configPaths.append({'icrObjectPath':LTM_RULE})
        if self.ifc.version >= 'bigiq 4.6.0':
            LOG.info("For new object models after 4.6.0")
            payload.configPaths.append({'icrObjectPath':LTM_VIRTUAL_ADDRESS})
            payload.configPaths.append({'icrObjectPath':LTM_PROFILE_HTTP})
            payload.configPaths.append({'icrObjectPath':LTM_MONITOR_HTTP})
        payload.deviceReference.set('https://localhost' + MachineIdResolver.ITEM_URI % self.device_id)
        task = self.api.post(RefreshCurrentConfig.URI, payload)
        RefreshCurrentConfig.wait(self.api, task)

        payload = RefreshWorkingConfig()
        payload.configPaths.append({'icrObjectPath':LTM_NODE})
        payload.configPaths.append({'icrObjectPath':LTM_POOL})
        payload.configPaths.append({'icrObjectPath':LTM_VIRTUAL})
        payload.configPaths.append({'icrObjectPath':LTM_RULE})
        if self.ifc.version >= 'bigiq 4.6.0':
            LOG.info("For new object models after 4.6.0")
            payload.configPaths.append({'icrObjectPath':LTM_VIRTUAL_ADDRESS})
            payload.configPaths.append({'icrObjectPath':LTM_PROFILE_HTTP})
            payload.configPaths.append({'icrObjectPath':LTM_MONITOR_HTTP})
        payload.deviceReference.set('https://localhost' + MachineIdResolver.ITEM_URI % self.device_id)
        task = self.api.post(RefreshWorkingConfig.URI, payload)
        RefreshWorkingConfig.wait(self.api, task)

