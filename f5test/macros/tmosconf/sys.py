'''
Created on Apr 12, 2013

@author: jono
'''
from .scaffolding import Stamp, Literal
import logging
from ...base import enum
from ...utils.parsers import tmsh
from ...utils.parsers.tmsh import RawEOL

LOG = logging.getLogger(__name__)


class Provision(Stamp):
    TMSH = """
        sys provision %(name)s {
           level none
        }
    """
    BIGPIPE = """
        provision %(name)s {
           level none
        }
    """
    states = enum(MINIMAL='minimum',
                  NOMINAL='nominal',
                  DEDICATED='dedicated')

    def __init__(self, name, level=states.NOMINAL):
        self.name = name
        self.level = level
        super(Provision, self).__init__()

    def tmsh(self, obj):
        value = obj.rename_key('sys provision %(name)s', name=self.name)
        value['level'] = self.level
        return None, obj

    def bigpipe(self, obj):
        v = self.folder.context.version
        if v.product.is_bigip and v >= 'bigip 10.0.0':
            value = obj.rename_key('provision %(name)s', name=self.name)
            value['level'] = self.level
            return None, obj
        return None, None


class Defaults(Literal):
    TMSH = """
        sys httpd {
            auth-pam-idle-timeout 21600
        }
        net self-allow {
            defaults {
                ospf:any
                tcp:161
                tcp:22
                tcp:4353
                tcp:443
                tcp:53
                udp:1026
                udp:161
                udp:4353
                udp:520
                udp:53
            }
        }
    """
    BIGPIPE = """
        stp {
        # config name none
        }
        self allow {
        #   default tcp domain udp 1026 tcp ssh tcp snmp proto ospf tcp 4353 udp domain tcp https udp efs udp 4353 udp snmp
        }
    """

    def bigpipe(self, obj):
        value = obj.rename_key('stp')
        value['config name'] = 'none'

        value = obj.rename_key('self allow')
        value['default tcp domain udp 1026 tcp ssh tcp snmp proto ospf tcp 4353 udp domain tcp https udp efs udp 4353 udp snmp'] = None
        return None, obj


class Platform(Stamp):
    TMSH = """
        sys management-ip %(ip)s/%(netmask)s { }
        sys management-route default {
           gateway none
        }
        sys db dhclient.mgmt {
            value "disable"
        }
        sys global-settings {
           mgmt-dhcp disabled
           gui-setup disabled
           hostname bigip1
        }
    """
    BIGPIPE = """
        mgmt %(ip)s {
           netmask %(netmask)s
        }
        mgmt route default inet {
           gateway none
        }
        system {
           hostname bigip1
        }
    """

    def __init__(self, address, gateway, hostname=None, dhcp=False, wizard=False):
        self.address = address
        self.gateway = gateway
        self.hostname = hostname or "ip-%s.mgmt.pdsea.f5net.com" % str(address.ip).replace('.', '-')
        self.dhcp = dhcp
        self.wizard = wizard
        super(Platform, self).__init__()

    def tmsh(self, obj):
        obj.rename_key('sys management-ip %(ip)s/%(netmask)s',
                       ip=self.address.ip, netmask=self.address.netmask)
        value = obj['sys management-route default']
        value['gateway'] = str(self.gateway)
        if self.dhcp:
            obj['sys db dhclient.mgmt']['value'] = 'enable'

        value = obj['sys global-settings']
        value['gui-setup'] = 'enabled' if self.wizard else 'disabled'
        value['mgmt-dhcp'] = 'enabled' if self.dhcp else 'disabled'
        value['hostname'] = self.hostname
        return None, obj

    def bigpipe(self, obj):
        value = obj.rename_key('mgmt %(ip)s', ip=self.address.ip)
        value['netmask'] = str(self.address.netmask)
        value = obj['mgmt route default inet']
        value['gateway'] = str(self.gateway)
        value = obj['system']
        value['gui setup'] = 'enable' if self.wizard else 'disable'
        value['hostname'] = self.hostname
        return None, obj


class DNS(Stamp):
    TMSH = """
        sys dns {
            name-servers { 172.27.1.1 }
            search { mgmt.pdsea.f5net.com f5net.com }
        }
    """
    BIGPIPE = """
        dns {
           nameservers
              172.27.1.1
           search
              mgmt.pdsea.f5net.com
              f5net.com
        }
    """

    def __init__(self, servers, suffixes=None):
        self.servers = servers
        self.suffixes = suffixes or []
        super(DNS, self).__init__()

    def tmsh(self, obj):
        obj['sys dns']['name-servers'] = self.servers
        obj['sys dns']['search'] = self.suffixes
        return None, obj

    def bigpipe(self, obj):
        value = obj['dns']
        value.clear()
        value.update({'nameservers': RawEOL})
        value.update(dict((x, tmsh.RawEOL) for x in self.servers))
        if self.suffixes:
            value.update({'search': RawEOL})
            value.update(dict((x, tmsh.RawEOL) for x in self.suffixes))
        return None, obj


class NTP(Stamp):
    TMSH = """
        sys ntp {
            servers { ntp.f5net.com }
            timezone America/Los_Angeles
        }
    """
    BIGPIPE = """
        ntp {
           servers ntp.f5net.com
           timezone "America/Los_Angeles"
        }
    """

    def __init__(self, servers, timezone=None):
        self.servers = servers or []
        self.timezone = timezone
        super(NTP, self).__init__()

    def tmsh(self, obj):
        value = obj['sys ntp']
        value.clear()
        value['servers'] = self.servers
        if self.timezone:
            value['timezone'] = self.timezone
        return None, obj

    def bigpipe(self, obj):
        value = obj['ntp']
        value.clear()
        if self.servers:
            value['servers'] = tmsh.RawString(' '.join(self.servers))
        if self.timezone:
            value['timezone'] = self.timezone
        return None, obj


class Mail(Stamp):
    TMSH = """
        sys smtp-server %(key)s {
            from-address nobody@f5net.com
            local-host-name test.net
            smtp-server-host-name mail.f5net.com
            smtp-server-port 25
        }
        """

    def __init__(self, server, port=25, originator='nobody@f5net.com'):
        self.server = server
        self.port = port
        self.originator = originator
        super(Mail, self).__init__()

    def tmsh(self, obj):
        v = self.folder.context.version
        if v.product.is_bigip and v >= 'bigip 11.3.0' or \
           v.product.is_em and v >= 'em 3.0.0':
            key = self.folder.SEPARATOR.join((self.folder.key(), self.server))
            value = obj.rename_key('sys smtp-server %(key)s', key=key)
            value['smtp-server-host-name'] = self.server
            value['smtp-server-port'] = self.port
            value['from-address'] = self.originator
            return key, obj
        return None, None
