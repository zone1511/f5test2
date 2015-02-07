'''
Created on Apr 13, 2011

@author: jono
'''
from .base import Kind


ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin'
ROOT_USERNAME = 'root'
ROOT_PASSWORD = 'default'
EM_MYSQL_USERNAME = 'root'
EM_MYSQL_PASSWORD = '4Dm1n'
F5EM_DB = 'f5em'
F5EM_EXTERN_DB = 'f5em_extern'

DEFAULT_PORTS = {
    'ssh': 22,
    'http': 80,
    'https': 443,
    'snmp': 161
}

# Kinds of devices that can be part of the test bed.
KIND_ANY = Kind()
KIND_TMOS = Kind('tmos')
KIND_TMOS_EM = Kind('tmos:em')
KIND_TMOS_BIGIQ = Kind('tmos:bigiq')
KIND_TMOS_BIGIP = Kind('tmos:bigip')
KIND_LINUX = Kind('linux')
KIND_LINUX_LOGIQ = Kind('linux:logiq')
KIND_CLOUD = Kind('cloud')
KIND_CLOUD_NSX = Kind('cloud:nsx')
KIND_CLOUD_NSX_BIGIP = Kind('cloud:nsx-bigip')
KIND_CLOUD_NSX_EDGE_TAGGED = Kind('cloud:nsx-edge:tagged')
KIND_CLOUD_NSX_EDGE_UNTAGGED = Kind('cloud:nsx-edge:untagged')
KIND_COULD_NSX_EDGE_WONG = Kind('cloud:nsx-edge-wong')
KIND_CLOUD_VSM = Kind('cloud:vsm')
KIND_CLOUD_VCD = Kind('cloud:vcd')
KIND_CLOUD_EC2 = Kind('cloud:ec2')
KIND_CLOUD_EC2AMI = Kind('cloud:ec2-ami')
KIND_CLOUD_NSXVM = Kind('cloud:nsx-vm')
KIND_CLOUD_OPENSTACK = Kind('cloud:openstack')
KIND_CLOUD_OPENSTACK_AMI = Kind('cloud:openstack-ami')
KIND_CLOUD_VCMP = Kind('cloud:vcmp')
KIND_CLOUD_VCMP_BP = Kind('cloud:vcmp-bigip')
KIND_OTHER = Kind('other')
