'''
Created on Apr 13, 2011

@author: jono
'''

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
    'https': 443
}

# Kinds of devices that can be part of the test bed.
KIND_ANY = ''
KIND_TMOS = 'tmos'
KIND_TMOS_EM = 'tmos:em'
KIND_TMOS_BIGIQ = 'tmos:bigiq'
KIND_TMOS_BIGIP = 'tmos:bigip'
KIND_LINUX = 'linux'
KIND_LINUX_LOGIQ = 'linux:logiq'
KIND_CLOUD = 'cloud'
KIND_CLOUD_VSM = 'cloud:vsm'
KIND_CLOUD_VCD = 'cloud:vcd'
KIND_CLOUD_EC2 = 'cloud:ec2'
KIND_CLOUD_EC2AMI = 'cloud:ec2-ami'
KIND_OTHER = 'other'

KIND_SEP = ':'
