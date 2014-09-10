# This is ONLY for backward compatibility!
# DO NOT add anything else below.
from .autodeploy import AutodeployJob, Image, PhysicalDevice, RebootDevice, \
    StoredConfig, VirtualDevice

from .cloud import Account, ManagedDeviceCloud, Connector, Tenant, \
    TenantPlacement, TenantServiceProperties, TenantServiceVarItem, \
    TenantServiceTableItem, TenantService, TenantServiceServerTiersInfoItem, \
    PolicyThresholdsItem, TenantServiceServerTiersPoliciesItem, \
    TenantServiceWithPolicy, TenantActivities, TenantVirtualServers, \
    EventAnalyzerHistogramsItem, EventAnalyzer, IappTemplateProperties, IappTemplate, \
    ConnectorProperty as ConnectorObjects, CloudNode, CloudNodeBIGIP, CloudNodeProperty, \
    ConfigureDeviceNode, AutoDeployDevice, ProviderActivities

from .firewall import Port, PortList, Task, DistributeConfigTask, \
    DeployConfigTask, SnapshotConfigTask, SnapshotSubtask, Snapshot, Schedule, \
    Address, AddressList, RuleList, PolicyList, Rule, Firewall, ManagedDevice, \
    DeclareMgmtAuthorityTask, RemoveMgmtAuthorityTask, RemoveMgmtAuthorityTaskV2

from .shared import UserCredentialData, License, NetworkDiscover, UserRoles, \
    GossipWorkerState, DeviceResolver, DeviceResolverGroup, DeviceResolverDevice, \
    DeviceInfo, HAPeerRemover, Echo, FailoverState, SnapshotClient, LicensePool, \
    DeviceInventory, LicenseRegistrationKey

from .system import EasySetup, BackupRestoreTask, SnmpInbound, \
    SnmpV1V2cAccessRecords, SnmpV3AccessRecords, SnmpTrap, Certificates, \
    NetworkInterface, NetworkVlan, NetworkSelfip

from .base import TaskError, Reference, ReferenceList, Link

from ...base import BaseApiObject as SharedObject
