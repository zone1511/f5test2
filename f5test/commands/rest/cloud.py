'''
Created on Feb 11, 2014

@author: a.dobre@f5.com
'''
from .base import IcontrolRestCommand
from ..base import CommandError
from ...base import Options, enum
from ...utils.wait import wait
from ...interfaces.rest.emapi.objects.cloud import Tenant, Connector, IappTemplate, \
    IappTemplateProperties, ConnectorProperty
from ...interfaces.testcase import ContextHelper
from ...interfaces.rest.emapi.objects.base import Link, Reference, ReferenceList
from ...interfaces.rest.emapi.objects.shared import DeviceResolver
from .device import DEFAULT_ALLBIGIQS_GROUP, DEFAULT_CLOUD_GROUP, \
                    ASM_ALL_GROUP, FIREWALL_ALL_GROUP, DEFAULT_AUTODEPLOY_GROUP, \
                    SECURITY_SHARED_GROUP, Discover
from .system import WaitRestjavad
from netaddr import IPAddress, ipv6_full
import logging

LOG = logging.getLogger(__name__)
PROPERTY_AA = {'highAvailabilityMode': 'active-active'}

# list of accepted connector types
CTYPES = enum(local='local',
              vsm='vmware',
              ec2='ec2',
              openstack='openstack',
              nsx='vmware-nsx',
              vcmp='vcmp',
              )

add_tenant = None
class AddTenant(IcontrolRestCommand):  # @IgnorePep8
    """Adds a tenant (tenant post)

    @param name: name #mandatory
    @type name: string

    @return: the tenant's api resp
    @rtype: attr dict json
    """
    def __init__(self, name,
                 # role=None,
                 description=None,
                 connectors=None,  # =[Reference(connector_payload)]
                 address=None,
                 phone=None,
                 email=None,
                 *args, **kwargs):
        super(AddTenant, self).__init__(*args, **kwargs)
        self.name = name
        # self.role = role  # Reference
        self.description = description
        self.connectors = connectors  # Reference List: EG: =[Reference(connector_payload)]
        self.address = address
        self.phone = phone
        self.email = email

    def setup(self):

        LOG.debug('Verify cloud tenants rest api...')
        x = self.api.get(Tenant.URI)
        LOG.debug("Tenants State Now: {0}".format(x))

        # Adding a Tenant
        LOG.info("Creating Tenant '{0}' ...".format(self.name))

        payload = Tenant(name=self.name)
        if self.description:
            payload['description'] = self.description
        if self.address:
            payload['addressContact'] = self.address
        if self.phone:
            payload['phone'] = self.phone
        if self.email:
            payload['email'] = self.email
        if self.connectors:
            payload['cloudConnectorReferences'] = self.connectors

        # This will also create the cloud user role "CloudTenantAdministrator_"
        resp = self.api.post(Tenant.URI, payload=payload)
        LOG.info("Created Tenant '{0}'. Further results in debug.".format(self.name))
        return resp


assign_connector_to_tenant_by_name = None
class AssignConnectorToTenantByName(IcontrolRestCommand):  # @IgnorePep8
    """Assigns a connector(by name) to tenant(by name) (tenant put)

    @param ctype: connector type #mandatory;
            Example: local/vmware/ec2/openstack/vmware-nsx/etc.
    @type ctype: string
    @param cname: connector name #mandatory
    @type cname: string
    @param tname: tenantname #mandatory
    @type tname: string

    @return: the tenant's api resp
    @rtype: attr dict json
    """
    def __init__(self, ctype, cname, tname,
                 *args, **kwargs):
        super(AssignConnectorToTenantByName, self).__init__(*args, **kwargs)
        self.ctype = ctype
        self.cname = cname
        self.tname = tname

    def setup(self):

        LOG.info("Assigning Connector '{0}' to Tenant '{1}.'"
                 .format(self.ctype, self.tname))
        connectorid = next(x.connectorId for x in \
                           self.api.get(Connector.URI % (self.ctype))['items'] \
                           if x.name == self.cname)
        payload = self.api.get(Tenant.ITEM_URI % (self.tname))
        payload['generation'] = payload.generation
        connector_payload = self.api \
                     .get(Connector.ITEM_URI % (self.ctype, connectorid))
        payload['cloudConnectorReferences'] = ReferenceList()
        payload.cloudConnectorReferences.append(Reference(connector_payload))

        resp = self.api.put(payload.selfLink, payload=payload)
        LOG.info("Assigned Connector '{0}' to Tenant '{1}'. Further results in debug."
                 .format(self.ctype, self.tname))

        return resp


add_iapp_template = None
class AddIappTemplate(IcontrolRestCommand):  # @IgnorePep8
    """Adds an iapp template to the Bigiq
        - will check for availability before posting
        Usage example 1 (use default HTTP iapp from cloud example):
        add_iapp_template(name='BVT_cat_HTTP0_')
        Usage example 2 (from file):
        add_iapp_template(name='BVT_cat_HTTP0_',
                          template_path=self.ih.get_data('PROJECTJSONDATAFOLDER'),
                          file_name='template115.json')


    @param name: name #mandatory
    @type name: string
    @param itype: Defaults to "http" #optional
    @type itype: string
    @param template_path: the relative path in depo #optional
    @type template_path: string
    @param file_name: file name of the template file #optional
    @type file_name: string

    @param specs: other optional specs. Calling this spec for now in case it grows in the future.
                  Right now there are 'connector' and 'template_uri'
                  'connector':<the post response> or selfLink of connector
                  'template_uri':'/mgmt/cm/cloud/templates/iapp/f5.http'
    @type specs: dict or AttrDict

    @return: iapp template rest resp
    @rtype: attr dict json
    """
    def __init__(self, name,
                 template_path=None,
                 file_name=None,
                 specs=None,
                 itype="f5.http",
                 *args, **kwargs):
        super(AddIappTemplate, self).__init__(*args, **kwargs)
        specs = Options(specs)
        self.name = name
        self.connector = specs.get('connector', '')

        content = None
        if template_path and file_name:
            content = IappTemplate().from_file(template_path, file_name)
        else:
            content = IappTemplate()
            content.update(self.api.get(IappTemplate.EXAMPLE_URI % itype))
        self.itype = itype
        self.fn = template_path + "/" + file_name if template_path else None
        self.template_uri = specs.template_uri if specs.template_uri else content.parentReference.link
        self.payload = content

    def setup(self):
        LOG.info("Creating catalog '{0}' from [{1}]...".format(self.name,
                                                               self.fn or self.itype))

        self.payload.update(templateName=self.name)

        if self.connector:
            provider = self.connector.selfLink if isinstance(self.connector, dict) \
                        and self.connector.get('selfLink') else self.connector
            self.payload.properties.append(IappTemplateProperties(provider=provider))
        else:
            self.payload.properties.append(IappTemplateProperties())

        LOG.debug("Waiting for template to be available...")

        def is_iapp_template_available():
            return self.api.get(self.template_uri)

        wait(is_iapp_template_available,
             progress_cb=lambda x: '...retry template uri - not available yet ...',
             timeout=50, interval=1,
             timeout_message="Template uri is not available after {0}s")

        LOG.debug("Verified that template is available...")
        LOG.debug("Waiting for iapp template to be assosicated with device...")

        def is_templated_associated_with_bigip():
            template_resp = self.api.get(self.template_uri)
            device_references = template_resp['deviceReferences']
            if len(device_references) > 0:
                return True

        wait(is_templated_associated_with_bigip,
             progress_cb=lambda x: '...retry - iapp template not associated with device yet ...',
             timeout=120, interval=1,
             timeout_message="Template is not associated with device after {0}s")
        LOG.debug("Verified iapp is assosicated with a bigip device...")

        LOG.debug("Creating Catalog...Posting...")
        resp = self.api.post(IappTemplate.URI, payload=self.payload)
        LOG.info("Created iappTemplate (Catalog) '{0}'. Further results in debug."
                 .format(self.name))
        return resp


add_connector = None
class AddConnector(IcontrolRestCommand):  # @IgnorePep8
    """Adds a cloud connector to bigiq

    @param name: name #mandatory 
    @type name: string
    @param ctype: type of connector #mandatory
                Accepted: local/vmware/ec2/openstack/vmware-nsx
    @type ctype: string

    @param description: connector description #not mandatory
    @type description: string
    @param device_references: device references #not mandatory
                        example: # [Link(link=x) for x in self.get_data('device_uris)]
    @type device_references: ReferenceList()
    @param remote_address # all mandatory params for non 'local' connectors
           remote_user
           remote_password
    @type string

    @param specs: connector specific parameters in dict format #not mandatory
                  - each dict key is the exact "id" parameter value of the payload
                  - notice that for ec2, no need to add the networks "name" subdict item.
                  Examples:
                  nsx: nsxresp = add_connector(name=nsxalias,
                                            ctype=CTYPES.nsx,
                                            description="NSX Automated Test Connector",
                                            remote_address=nsxi.get("ip"),
                                            remote_user=nsxi.get("user"),
                                            remote_password=nsxi.get("pw"),
                                            specs={'bigIQCallbackUser': self.bigiq.get("user"),
                                           'bigIQCallbackPassword': self.bigiq.get("pw")})
                  ec2: resp = add_connector(name=ec2alias,
                                           ctype=CTYPES.ec2,
                                           description="EC2 Automated test",
                                           remote_address=ec2x.get('ip'),
                                           remote_user=ec2x.get('user'),
                                           remote_password=ec2x.get('pw'),
                         specs={'availabilityZone': ec2x.get('zone'),
                                'ntpServers': ec2x.get('ntps'),
                                'timezone': ec2x.get('tzs'),
                                'vpcId': ec2x.get('vpc'),
                        'tenantInternalNetworks': [{'subnetAddress': ec2x.get('sint'),
                                                    'gatewayAddress': ec2x.get('int_gw')}],
                        'managementNetworks': [{'subnetAddress': ec2x.get('smgmt'),
                                                'gatewayAddress': ec2x.get('mgmt_gw')}],
                        'tenantExternalNetworks': [{'subnetAddress': ec2x.get('sext'),
                                                    'gatewayAddress': ec2x.get('ext_gw')}],
                                        })
    @type specs: Dict

    @return: connector rest resp
    @rtype: attr dict json
    """
    def __init__(self, name, ctype,
                 description=None,
                 device_references=None,  # [Link(link=x) for x in self.get_data('device_uris)]
                 remote_address=None,
                 remote_user=None,
                 remote_password=None,
                 specs=None,
                 *args, **kwargs):
        super(AddConnector, self).__init__(*args, **kwargs)

        self.name = name
        self.description = description
        self.device_references = device_references
        # common required parameters:
        if ctype != CTYPES.local:
            if not remote_address or not remote_user or not remote_password:
                raise CommandError("Invalid required parameters for connector: {0}"
                                   .format(self.name))
        if ctype == CTYPES.nsx:
            if not 'bigIQCallbackUser' in specs or \
                not 'bigIQCallbackPassword' in specs:
                if not specs['bigIQCallbackUser'] or \
                    not  specs['bigIQCallbackPassword']:
                    raise CommandError("Invalid specific parameters for connector: {0}"
                                       .format(self.name))
        elif ctype == CTYPES.ec2:
            if not 'availabilityZone' in specs:
                if not specs['availabilityZone']:
                    raise CommandError("Invalid specific parameters for connector: {0}"
                                       .format(self.name))
        elif ctype == CTYPES.local:
            pass
        elif ctype == CTYPES.vsm:
            pass
        elif ctype == CTYPES.openstack:
            pass
        elif ctype == CTYPES.vcmp:
            pass
        else:
            raise CommandError("Wrong Connector Type was passed...")
        self.ctype = ctype

        self.remote_address = remote_address
        self.remote_user = remote_user
        self.remote_password = remote_password

        self.specs = specs

    def setup(self):

        LOG.debug("Adding {1} Connector '{0}'..."
                 .format(self.name, self.ctype))
        # Creating from scratch
        # Required Parameters for all:
        payload = Connector()
        # Required
        payload['cloudConnectorReference'] = Link(link=Connector.URI % self.ctype)
        # Required
        payload['name'] = self.name

        # Not Required parameters for all:
        if self.description:
            payload['description'] = self.description
        if self.device_references:
            # payload['deviceReferences'] = ReferenceList()
            # example: [(Link(link=x) for x in urideviceList)]
            payload['deviceReferences'] = self.device_references

        # Specific Objects abd Parameters to each connector:
        if self.ctype == CTYPES.ec2:
            ####OBJECTS
            # Not Required Objects
            if 'ntpServers' in self.specs:
                if self.specs['ntpServers']:
                    payload['ntpServers'] = self.specs['ntpServers']
            if 'timezone' in self.specs:
                if self.specs['timezone']:
                    payload['timezone'] = self.specs['timezone']
            if 'tenantInternalNetworks' in self.specs:
                if self.specs['tenantInternalNetworks']:
                    payload['tenantInternalNetworks'] = []
                    for network in self.specs['tenantInternalNetworks']:
                        payload.tenantInternalNetworks.append(
                            {'subnetAddress': network['subnetAddress'],
                             'name': 'internal',
                             'gatewayAddress': network['gatewayAddress']})
            if 'managementNetworks' in self.specs:
                if self.specs['managementNetworks']:
                    payload['managementNetworks'] = []
                    for network in self.specs['managementNetworks']:
                        payload.managementNetworks.append(
                            {'subnetAddress': network['subnetAddress'],
                             'name': 'mgmt',
                             'gatewayAddress': network['gatewayAddress']})
            if 'tenantExternalNetworks' in self.specs:
                if self.specs['tenantExternalNetworks']:
                    payload['tenantExternalNetworks'] = []
                    for network in self.specs['tenantExternalNetworks']:
                        payload.tenantExternalNetworks.append(
                            {'subnetAddress': network['subnetAddress'],
                             'name': 'external',
                             'gatewayAddress': network['gatewayAddress']})
            if 'dnsServerAddresses' in self.specs:
                if self.specs['dnsServerAddresses']:
                    payload['dnsServerAddresses'] = []
                    for dns in self.specs['dnsServerAddresses']:
                        payload.dnsServerAddresses.append(dns)
            if 'dnsSuffixes' in self.specs:
                if self.specs['dnsSuffixes']:
                    payload['dnsSuffixes'] = []
                    for dns in self.specs['dnsSuffixes']:
                        payload.dnsSuffixes.append(dns)

            # Not Scoped Yet, left default as they come back from POST:

            # supportsServerProvisioning
            # supportsDeviceProvisioning
            # licensepools

            ####PARAMETERS
            # Required Parameters
            regionEndpoint = ConnectorProperty(id='regionEndpoint',
                                              displayName='Region Endpoint',
                                              value=self.remote_address)
            keyId = ConnectorProperty(id='awsAccessKeyID',
                                     displayName='Key ID',
                                     value=self.remote_user)
            secretKey = ConnectorProperty(id='secretAccessKey',
                                         displayName='SecretKey',
                                         value=self.remote_password)
            availZone = ConnectorProperty(id='availabilityZone',
                                         displayName='Availability Zone',
                                         value=self.specs['availabilityZone'])
            payload.parameters.extend([regionEndpoint,
                                       keyId,
                                       secretKey,
                                       availZone])
            # Not Required Parameters:
            if 'vpcId' in self.specs:
                if self.specs['vpcId']:
                    vpc = ConnectorProperty(id='vpcId',
                                           isRequired=False,
                                           displayName='Virtual Private Cloud ID',
                                           value=self.specs['vpcId'])
                    payload.parameters.extend([vpc])
            if 'autoDeployDevices' in self.specs:
                if self.specs['autoDeployDevices']:
                    deploy = ConnectorProperty(id='autoDeployDevices',
                                              isRequired=False,
                                              displayName='Auto-deploy Devices',
                                              provider=self.specs['autoDeployDevices'])
                    deploy.pop('value')
                    payload.parameters.extend([deploy])

            if 'licenseReference' in self.specs:
                payload.licenseReference = self.specs.licenseReference

            # Not Scoped Yet, left default as they come back from POST:
            # autoDeployServers

        if self.ctype == CTYPES.nsx:
            LOG.debug('Creating Specific NSX parameters (from yaml)...')
            # PARAMETERS:
            # Required Parameters:
            nsx_address_obj = ConnectorProperty(id='nsxAddress',
                                               # displayName='nsxAddress',
                                               value=self.remote_address)
            # Required
            nsx_user_obj = ConnectorProperty(id='nsxUsername',
                                            # displayName='nsxUser',
                                            value=self.remote_user)
            # Required
            nsx_password_obj = ConnectorProperty(id='nsxPassword',
                                                # displayName='SecretKey',
                                                value=self.remote_password)
            # Required
            vcen_address_obj = ConnectorProperty(id='vCenterServerAddress',
                                               # displayName='nsxAddress',
                                               value=self.specs['vCenterServerAddress'])
            # Required
            vcen_user_obj = ConnectorProperty(id='vCenterServerUsername',
                                            # displayName='nsxUser',
                                            value=self.specs['vCenterServerUsername'])
            # Required
            vcen_password_obj = ConnectorProperty(id='vCenterServerPassword',
                                                # displayName='SecretKey',
                                                value=self.specs['vCenterServerPassword'])
            # Required
            user_obj = ConnectorProperty(id='bigIQCallbackUser',
                                        # displayName='bigiq user',
                                        value=self.specs['bigIQCallbackUser'])
            # Required
            password_obj = ConnectorProperty(id='bigIQCallbackPassword',
                                            # displayName='bigiq password',
                                            value=self.specs['bigIQCallbackPassword'])
            payload.parameters.extend([nsx_address_obj,
                                       nsx_user_obj,
                                       nsx_password_obj,
                                       user_obj,
                                       password_obj,
                                       vcen_address_obj,
                                       vcen_user_obj,
                                       vcen_password_obj
                                       ])
            # Not Required Parameters:
            if 'machineId' in self.specs and 'ipAddress' in self.specs:
                # machineId and ipAddress are required to form the call back cluster map
                payload.callbackClusterAddresses = [{'machineId': self.specs['machineId'], 'ipAddress': self.specs['ipAddress']}]

            if 'licenseReference' in self.specs:
                payload.licenseReference = self.specs.licenseReference
            if 'ntpServers' in self.specs:
                payload.ntpServers = self.specs.ntpServers
            if 'dnsServerAddresses' in self.specs:
                payload.dnsServerAddresses = self.specs.dnsServerAddresses
            if 'timezone' in self.specs:
                payload.timezone = self.specs.timezone
            if 'deviceReference' in self.specs:
                payload.deviceReferences = [Link(link=self.specs.deviceReference)]

            # adding VCMP connector
        if self.ctype == CTYPES.vcmp:
            LOG.debug('Creating Specific VCMP parameters (from yaml)...')
            vcmp_host_obj = ConnectorProperty(id='VcmpHost',
                                              isRequired=True,
                                              value=self.specs['VcmpHost'])
            vcmp_hostusername_obj = ConnectorProperty(id='VcmpHostUserName',
                                                      isRequired=True,
                                                      value=self.specs['VcmpHostUserName'])
            vcmp_hostpassword_obj = ConnectorProperty(id='VcmpHostPassword',
                                                      isRequired=True,
                                                      value=self.specs['VcmpHostPassword'])
            payload.parameters.extend([vcmp_host_obj, vcmp_hostusername_obj,
                                       vcmp_hostpassword_obj])
            # to be updated

        LOG.debug("Creating Connector: Using payload:\n{0}".format(payload))
        resp = self.api.post(Connector.URI % self.ctype, payload=payload)
        LOG.info("Created Connector |{0}| '{1}'. Further results in debug."
                 .format(self.ctype, self.name))

        return resp


setup_ha = None
class SetupHa(IcontrolRestCommand):  # @IgnorePep8
    DEVICE_GROUPS = [SECURITY_SHARED_GROUP, DEFAULT_AUTODEPLOY_GROUP,
                     ASM_ALL_GROUP, FIREWALL_ALL_GROUP, SECURITY_SHARED_GROUP,
                     DEFAULT_CLOUD_GROUP, 'cm-asm-logging-nodes-trust-group',
                     'cm-websafe-logging-nodes-trust-group']

    def __init__(self, peers, *args, **kwargs):
        super(SetupHa, self).__init__(*args, **kwargs)
        self.peers = peers

    def prep(self):
        WaitRestjavad(self.peers).run()

    def setup(self):
        LOG.info("Setting up Clustered HA with %s...", self.peers)
        peer_ips = set(IPAddress(x.get_discover_address()).format(ipv6_full) for x in self.peers)
        options = Options()
        options.properties = PROPERTY_AA
        options.automaticallyUpdateFramework = False

        Discover(self.peers, group=DEFAULT_ALLBIGIQS_GROUP,
                 options=options).run()

        # Wait until until peer BIG-IQs are added to the device groups.
        for device_group in SetupHa.DEVICE_GROUPS:
            if self.ifc.version < 'bigiq 4.5.0' and device_group == 'cm-websafe-logging-nodes-trust-group':
                continue
            wait(lambda: self.api.get(DeviceResolver.DEVICES_URI % device_group),
                 condition=lambda ret: len(peer_ips) == len(peer_ips.intersection(set(x.address for x in ret['items']))),
                 progress_cb=lambda ret: 'Waiting until {0} appears in {1}'.format(peer_ips, device_group),
                 interval=10, timeout=600)

i_apps = None
class iApps(IcontrolRestCommand):  # @IgnorePep8
    """
    class to return the applications running on the big ip's
    @param devices: bigip device list from harness #mandatory
    @type connector: big-iq UI element connector #optional
    """
    TM_APP_URI = '/mgmt/tm/cloud/services/iapp'

    def __init__(self, devices, connector=None, *args, **kwargs):
        super(iApps, self).__init__(*args, **kwargs)
        self.devices = devices
        self.connector = connector
        self.app_list = {}

    def prep(self):
        self.context = ContextHelper(__file__)

    def cleanup(self):
        self.context.teardown()

    def setup(self):
        devices_to_verify_on = []
        check_all_bigips = False
        if self.connector:
            for device_uri in self.connector.deviceReferences:
                resp = self.api.get(device_uri['link'])
                if 'address' in resp:
                    devices_to_verify_on.append(resp['address'])
        else:
            check_all_bigips = True

        for device in self.devices:
            if not check_all_bigips:
                device_address = device.get_discover_address()
                LOG.debug("Getting iapps on Bigip {0}".format(device_address))
                if device_address in devices_to_verify_on:
                    LOG.debug("Bigip {0} is associated with Connector".format(device_address))
                    self.return_app_list(device)
            else:
                self.return_app_list(device)
        return self.app_list

    def return_app_list(self, device):
        bigip_device_api = self.context.get_icontrol_rest(device=device).api
        self.app_list[device] = bigip_device_api.get(self.TM_APP_URI)['items']
        LOG.debug("iapp {0} found on Bigip {1}".format(self.app_list[device], device))
