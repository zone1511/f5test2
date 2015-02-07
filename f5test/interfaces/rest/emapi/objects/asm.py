'''
Created on Jan 13, 2014

/mgmt/cm/asm workers

@author: mshah
'''
from .....utils.wait import wait
from .base import Reference, ReferenceList, Task, TaskError, DEFAULT_TIMEOUT
from ...base import BaseApiObject
from f5test.base import AttrDict
import json

class AsmTask(Task):

    # This wait function is used in versions before Firestone.
    def wait(self, rest, resource, loop=None, timeout=DEFAULT_TIMEOUT, interval=1,
             timeout_message=None):
        def get_status():
            return rest.get(resource.selfLink)
        if loop is None:
            loop = get_status
        ret = wait(loop, timeout=timeout, interval=interval,
                   timeout_message=timeout_message,
                   condition=lambda x: x.overallStatus not in ('NEW',),
                   progress_cb=lambda x: 'Status: {0}'.format(x.overallStatus))
        assert ret.overallStatus == 'COMPLETED', "{0.overallStatus}:{0.error}".format(ret)
        return ret

    def wait_status(self, rest, resource, loop=None, timeout=DEFAULT_TIMEOUT, interval=1,
             timeout_message=None):
        def get_status():
            return rest.get(resource.selfLink)
        if loop is None:
            loop = get_status
        ret = wait(loop, timeout=timeout, interval=interval,
                   timeout_message=timeout_message,
                   condition=lambda x: x.status not in ('NEW', 'STARTED', 'PENDING_UPDATE_TASK'),
                   progress_cb=lambda x: 'Status: {0}'.format(x.status))
        msg = json.dumps(ret, sort_keys=True, indent=4, ensure_ascii=False)
        if "currentStep" in ret.keys():
            # Resolve 'PENDING_CONFLICTS' when the resolution to a conflict is 'NONE'.
            if ret.status == 'FINISHED' and ret.currentStep == 'PENDING_CONFLICTS':
#                for resolution in [x.resolution for x in ret.conflicts]:
                for conflict in ret.conflicts:
                    if conflict.resolution == 'NONE':
                        conflict.resolution = "USE_BIGIQ"
                        payload = AttrDict()
                        payload.conflicts = [conflict]
                        payload.status = "STARTED"
                        rest.patch(ret.selfLink, payload)
                    else:
                        raise TaskError("DMA has pending conflicts to resolve. Task failed:\n%s"
                                        % msg)

            elif ret.status != 'FINISHED' or ret.currentStep != 'DONE':
                raise TaskError("Either '%s' != 'FINISHED' or '%s' != 'DONE'. Task failed:\n%s"
                                % (ret.status, ret.currentStep, msg))
        else:
            if ret.status not in ('COMPLETED', 'FINISHED'):
                raise TaskError("'%s' not in ('COMPLETED', 'FINISHED'). Task failed:\n%s"
                                % (ret.status, msg))
        return ret

# Ref- https://peterpan.f5net.com/twiki/bin/view/MgmtProducts/ASMConfigurationDeployerWorkerAPI
class DeployConfigTask(Task):
    URI = '/mgmt/cm/asm/tasks/deploy-configuration'

    def __init__(self, *args, **kwargs):
        super(DeployConfigTask, self).__init__(*args, **kwargs)
        self.setdefault('description', '')


# Ref- https://peterpan.f5net.com/twiki/bin/view/MgmtProducts/ASMVirtualServerWorkerAPI
class VirtualServerBase(BaseApiObject):
    def __init__(self, *args, **kwargs):
        super(VirtualServerBase, self).__init__(*args, **kwargs)
        self.setdefault('name', '')
        self.setdefault('address', '')
        self.setdefault('fullPath', '')
        self.setdefault('isInactivePoliciesHolder', True)
        self.setdefault('deviceReference', Reference())
        self.setdefault('attachedPoliciesReferences', Reference())

# Used since Elysian(4.4.0); Abandoned starting from Firestone(4.5.0).
class VirtualServer(VirtualServerBase):
    URI = '/mgmt/cm/asm/virtual-servers'
    ITEM_URI = '/mgmt/cm/asm/virtual-servers/%s'

    def __init__(self, *args, **kwargs):
        super(VirtualServer, self).__init__(*args, **kwargs)

class VirtualServerV2(VirtualServerBase):
    URI = '/mgmt/cm/asm/working-config/virtual-servers'
    ITEM_URI = '/mgmt/cm/asm/working-config/virtual-servers/%s'

    def __init__(self, *args, **kwargs):
        super(VirtualServerV2, self).__init__(*args, **kwargs)


# Ref- https://peterpan.f5net.com/twiki/bin/view/MgmtProducts/ASMPolicyWorkerAPI
class PolicyBase(BaseApiObject):

    def __init__(self, *args, **kwargs):
        super(PolicyBase, self).__init__(*args, **kwargs)
        self.setdefault('name', '')
        self.setdefault('id', '')
        self.setdefault('fullPath', '')
        self.setdefault('fileReference', Reference())
        self.setdefault('versionPolicyName', '')
        self.setdefault('versionDeviceName', '')
        self.setdefault('kind', '')
        self.setdefault('description', '')

class Policy(PolicyBase):
    URI = '/mgmt/cm/asm/policies'

    def __init__(self, *args, **kwargs):
        super(Policy, self).__init__(*args, **kwargs)

class PolicyV2(PolicyBase):
    URI = '/mgmt/cm/asm/working-config/policies'

    def __init__(self, *args, **kwargs):
        super(PolicyV2, self).__init__(*args, **kwargs)


# Ref- https://peterpan.f5net.com/twiki/bin/view/MgmtProducts/ASMMultipartPolicyFileWorkerAPI
class PolicyUpload(BaseApiObject):
    URI = '/mgmt/cm/asm/policy-files/upload/%s'

    def __init__(self, *args, **kwargs):
        super(PolicyUpload, self).__init__(*args, **kwargs)
        self.setdefault('name', '')
        self.setdefault('id', '')
        self.setdefault('fullPath', '')
        self.setdefault('fileReference', Reference())
        self.setdefault('versionPolicyName', '')
        self.setdefault('versionDeviceName', '')
        self.setdefault('kind', '')
        self.setdefault('description', '')
        self.setdefault('srcType', '')


# Ref- https://peterpan.f5net.com/twiki/bin/view/MgmtProducts/ASMPolicyDownloaderWorkerAPI
class PolicyDownload(BaseApiObject):
    URI = '/mgmt/cm/asm/policy-files/download/%s'

    def __init__(self, *args, **kwargs):
        super(PolicyDownload, self).__init__(*args, **kwargs)


# Used since Elysian(4.4.0); Abandoned starting from Firestone(4.5.0).
# Ref- https://peterpan.f5net.com/twiki/bin/view/MgmtProducts/ASMPolicyAssignmentTaskWorkerAPI
class VirtualPolicy(BaseApiObject):
    URI = '/mgmt/cm/asm/tasks/virtual-server-policy'

    def __init__(self, *args, **kwargs):
        super(VirtualPolicy, self).__init__(*args, **kwargs)
        self.setdefault('virtualServerId', '')
        self.setdefault('policyReference', Reference())
        self.setdefault('status', '')
        self.setdefault('overallStatus', '')
        self.setdefault('isResume', '')
        self.setdefault('isReset', '')


class GetDevice(BaseApiObject):
    URI = '/mgmt/shared/resolver/device-groups/cm-asm-allAsmDevices/devices'

    def __init__(self, *args, **kwargs):
        super(GetDevice, self).__init__(*args, **kwargs)
        self.setdefault('address', '')
        self.setdefault('state', '')
        self.setdefault('hostname', '')
        self.setdefault('version', '')
        self.setdefault('product', '')
        self.setdefault('build', '')


# Ref- https://peterpan.f5net.com/twiki/bin/view/MgmtProducts/ASMManagementAuthorityRemoverWorkerAPI
class RemoveMgmtAuthority(AsmTask):
    URI = '/mgmt/cm/asm/tasks/remove-mgmt-authority'

    def __init__(self, *args, **kwargs):
        super(RemoveMgmtAuthority, self).__init__(*args, **kwargs)
        self.setdefault('deviceReference', Reference())


class GetRemoveMgmtAuthority(BaseApiObject):
    URI = '/mgmt/cm/asm/tasks/remove-mgmt-authority/%s'

    def __init__(self, *args, **kwargs):
        super(RemoveMgmtAuthority, self).__init__(*args, **kwargs)
        self.setdefault('status', '')
        self.setdefault('deviceID', '')
        self.setdefault('deviceReference', Reference())


# Ref- https://peterpan.f5net.com/twiki/bin/view/MgmtProducts/ASMDeclareMgmtAuthorityWorkerAPI
# Ref- https://confluence.pdsea.f5net.com/display/PDBIGIQASMTEAM/Policy+Edit+-+Phase+I#PolicyEdit-PhaseI-RESTAPIchanges
class DeclareMgmtAuthorityBase(AsmTask):
    URI = '/mgmt/cm/asm/tasks/declare-mgmt-authority'

    def __init__(self, *args, **kwargs):
        super(DeclareMgmtAuthorityBase, self).__init__(*args, **kwargs)
        self.setdefault('address', '')
        self.setdefault('overrideExistingPoliciesSrc', False)
        self.setdefault('automaticallyUpdateFramework', True)
        self.setdefault('rootUser', 'root')
        self.setdefault('rootPassword', 'default')

# Used since Elysian(4.4.0); Abandoned starting from Firestone(4.5.0).
class DeclareMgmtAuthority(DeclareMgmtAuthorityBase):
    def __init__(self, *args, **kwargs):
        super(DeclareMgmtAuthority, self).__init__(*args, **kwargs)
        self.setdefault('username', 'admin')
        self.setdefault('password', 'admin')
        self.setdefault('discoverSharedSecurity', False)

class DeclareMgmtAuthorityV2(DeclareMgmtAuthorityBase):
    def __init__(self, *args, **kwargs):
        super(DeclareMgmtAuthorityV2, self).__init__(*args, **kwargs)
        self.setdefault('deviceUsername', 'admin')
        self.setdefault('devicePassword', 'admin')
        self.setdefault('createChildTasks', True)
        self.setdefault('discoverSharedSecurity', True)

# Used since Elysian(4.4.0); Abandoned starting from Firestone(4.5.0).
# Ref- ??
class InactiveVirtualServerPolicy(AsmTask):
    URI = '/mgmt/cm/asm/tasks/inactive-virtual-server-policy'

    def __init__(self, *args, **kwargs):
        super(InactiveVirtualServerPolicy, self).__init__(*args, **kwargs)
        self.setdefault('policyReferences', ReferenceList())
        self.setdefault('virtualServerId', '')


# Ref- https://peterpan.f5net.com/twiki/bin/view/MgmtProducts/BIGIQASMSignatureFilesMetadataAPI
class SignatureFileMetadata(BaseApiObject):
    URI = '/mgmt/cm/asm/signatures/repository/signature-files-metadata'
    ITEM_URI = '/mgmt/cm/asm/signatures/repository/signature-files-metadata/%s'

    def __init__(self, *args, **kwargs):
        super(SignatureFileMetadata, self).__init__(*args, **kwargs)
        self.setdefault('id', '')


# Ref- https://peterpan.f5net.com/twiki/bin/view/MgmtProducts/BIGIQASMSignatureFilesUpdateSchedulerAPI
class ScheduleUpdate(BaseApiObject):
    URI = '/mgmt/cm/asm/signatures/schedule-update'

    def __init__(self, *args, **kwargs):
        super(ScheduleUpdate, self).__init__(*args, **kwargs)
        self.setdefault('frequency', '')


# Ref- https://peterpan.f5net.com/twiki/bin/view/MgmtProducts/BIGIQUpdateAndPushSignatureFilesTaskAPI
class UpdatePushSignature(AsmTask):
    URI = '/mgmt/cm/asm/tasks/signatures/update-push-signatures'

    def __init__(self, *args, **kwargs):
        super(UpdatePushSignature, self).__init__(*args, **kwargs)


# Ref- https://peterpan.f5net.com/twiki/bin/view/MgmtProducts/BIGIQASMAuditLogsAPI
class Logging(BaseApiObject):
    URI = '/mgmt/cm/asm/logging'

    def __init__(self, *args, **kwargs):
        super(Logging, self).__init__(*args, **kwargs)
        self.setdefault('id','')
        self.setdefault('isSuccessfull','')


# Ref- https://confluence.pdsea.f5net.com/display/PDBIGIQASMTEAM/DoS+Profile+APIs
class DosProfile(BaseApiObject):
    URI = '/mgmt/cm/security-shared/working-config/dos-profiles'
    ITEM_URI = '/mgmt/cm/security-shared/working-config/dos-profiles/%s'

    def __init__(self, *args, **kwargs):
        super(DosProfile, self).__init__(*args, **kwargs)
	self.setdefault('name', '')
	self.setdefault('partition', '')
	self.setdefault('fullPath', '')


# Ref- https://confluence.pdsea.f5net.com/display/PDBIGIQASMTEAM/DoS+Device+Configuration+API
class DosDeviceConfiguration(BaseApiObject):
    URI = '/mgmt/cm/security-shared/working-config/dos-device-config'

    def __init__(self, *args, **kwargs):
        super(DosDeviceConfiguration, self).__init__(*args, **kwargs)


#Ref- https://confluence.pdsea.f5net.com/display/PDBIGIQASMTEAM/DoS+Device+IP+WhiteList+API
class DosNetworkWhitelist(BaseApiObject):
    URI = '/mgmt/cm/security-shared/working-config/dos-network-whitelist'

    def __init__(self, *args, **kwargs):
        super(DosNetworkWhitelist, self).__init__(*args, **kwargs)
