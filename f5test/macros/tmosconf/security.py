'''
Created on Apr 12, 2013

@author: jono
'''
from .scaffolding import Stamp
from ...base import enum, AttrDict


class AddressList(Stamp):
    TMSH = """
        security firewall address-list %(key)s {
            addresses {
                1.1.1.2 { }
                1.1.0.0/16 { }
                2::/16 { }
                1.1.2.0/24 { }
            }
            description none
        }
    """

    def __init__(self, name, addresses, description=None):
        self.name = name
        self.description = description
        self.addresses = dict((k, {}) for k in addresses or [])
        super(AddressList, self).__init__()

    def compile(self):
        v = self.folder.context.version
        if v.product.is_bigip and v >= 'bigip 11.3.0':
            key = self.folder.SEPARATOR.join((self.folder.key(), self.name))
            obj = self.from_template('TMSH')
            value = obj.rename_key('security firewall address-list %(key)s', key=key)
            value['addresses'].clear()
            value['addresses'].update(self.addresses)
        else:
            key = obj = None
        return key, obj


class PortList(Stamp):
    TMSH = """
        security firewall port-list %(key)s {
            ports {
                443 { }
                1029-1043 { }
                4353 { }
            }
            description none
        }
    """

    def __init__(self, name, ports, description=None):
        self.name = name
        self.description = description
        self.ports = dict((k, {}) for k in ports or [])
        super(PortList, self).__init__()

    def compile(self):
        v = self.folder.context.version
        if v.product.is_bigip and v >= 'bigip 11.3.0':
            key = self.folder.SEPARATOR.join((self.folder.key(), self.name))
            obj = self.from_template('TMSH')
            value = obj.rename_key('security firewall port-list %(key)s', key=key)
            value['ports'].clear()
            value['ports'].update(self.ports)
        else:
            key = obj = None
        return key, obj


class RuleDestination(AttrDict):

    def __init__(self, *args, **kwargs):
        super(RuleDestination, self).__init__(*args, **kwargs)
        self.setdefault('address-lists', [])
        self.setdefault('port-lists', [])
        self.setdefault('addresses', [])
        self.setdefault('ports', [])

    # We don't use the extra attributes for list references
    def _as_dict(self):
        for k, v in self.iteritems():
            if k in ('address-lists', 'port-lists', 'vlans'):
                self[k] = dict((x.get(reference=True), None) for x in v)
            else:
                self[k] = dict((x, {}) for x in v)
        return self


class RuleSource(RuleDestination):

    def __init__(self, *args, **kwargs):
        super(RuleSource, self).__init__(*args, **kwargs)
        self.setdefault('vlans', [])


class Rule(Stamp):
    TMSH = """
        %(name)s {
            action accept
            description none
            ip-protocol udp
            destination {
                address-lists {
                    al_1
                }
                port-lists {
                    port_list1
                }
                ports {
                    57 { }
                }
            }
            source {
                address-lists {
                    al_1
                }
                addresses {
                    2002:1::/32 { }
                }
                port-lists {
                    port_list1
                }
                ports {
                    40-50 { }
                    90 { }
                }
                vlans {
                    internal
                }
            }
        }
    """
    states = enum(ENABLED='enabled',
                  DISABLED='disabled',
                  SCHEDULED='scheduled')
    actions = enum(ACCEPT='accept',
                   ACCEPT_DECISIVELY='accept-decisively',
                   REJECT='reject',
                   DROP='drop')
    # Only common protocols listed here
    protocols = enum(ICMP='icmp',
                     ICMPV6='ipv6-icmp',
                     TCP='tcp',
                     UDP='udp')

    def __init__(self, name, description=None, action=actions.ACCEPT,
                 protocol=protocols.TCP, destination=None, source=None):
        self.name = name
        self.description = description
        self.action = action
        self.protocol = protocol
        self.destination = destination or RuleDestination()
        self.source = source or RuleSource()
        super(Rule, self).__init__()

    def get_for_firewall(self):
        return self.get(reference=False)

    def compile(self):
        key = self.name
        obj = self.from_template('TMSH')
        value = obj.rename_key('%(name)s', name=self.name)
        if self.description:
            value['description'] = self.description
        value['action'] = self.action
        value['ip-protocol'] = self.protocol

        value['destination'].update(self.destination._as_dict())
        value['source'].update(self.source._as_dict())
        return key, obj


class RuleList(Stamp):
    TMSH = """
        security firewall rule-list %(key)s {
            description none
            rules {
                rule_1 {
                    action accept
                }
                rule_2 {
                    action accept
                    description "rule_2 description"
                    ip-protocol udp
                    destination {
                        address-lists {
                            al_1
                        }
                        port-lists {
                            port_list1
                        }
                        ports {
                            57 { }
                        }
                    }
                    source {
                        address-lists {
                            al_1
                        }
                        addresses {
                            2002:1::/32 { }
                        }
                        port-lists {
                            port_list1
                        }
                        ports {
                            40-50 { }
                            90 { }
                        }
                        vlans {
                            internal
                        }
                    }
                }
            }
        }
    """

    def __init__(self, name, description=None, rules=None):
        self.name = name
        self.description = description
        self.rules = rules or []
        super(RuleList, self).__init__()

    def get_for_firewall(self):
        return {self.name: {'rule-list': self.get(reference=True)}}

    def compile(self):
        v = self.folder.context.version
        if v.product.is_bigip and v >= 'bigip 11.3.0':
            key = self.folder.SEPARATOR.join((self.folder.key(), self.name))
            obj = self.from_template('TMSH')
            value = obj.rename_key('security firewall rule-list %(key)s', key=key)
            if self.description:
                value['description'] = self.description

            value['rules'].clear()
            map(lambda x: value['rules'].update(x.get()), self.rules)
            #print self.rules[0].get()
            #raise
        else:
            key = obj = None
        return key, obj


class Firewall(Stamp):
    TMSH = """
        %(key)s {
            rules {
            }
        }
    """
    types = enum('GLOBAL', 'MANAGEMENT_PORT', 'SELF_IP', 'ROUTE_DOMAIN',
                 'VIRTUAL_SERVER')
    type_to_key = {types.GLOBAL: 'security firewall global-rules',
                   types.MANAGEMENT_PORT: 'security firewall management-ip-rules',
                   types.SELF_IP: 'fw-rules',
                   types.ROUTE_DOMAIN: 'fw-rules',
                   types.VIRTUAL_SERVER: 'fw-rules',
                   }

    def __init__(self, type_=types.GLOBAL, rules=None):
        self.type = type_
        self.rules = rules or []
        super(Firewall, self).__init__()

    def compile(self):
        v = self.folder.context.version
        if v.product.is_bigip and v >= 'bigip 11.3.0':
            key = Firewall.type_to_key[self.type]
            obj = self.from_template('TMSH')
            value = obj.rename_key('%(key)s', key=key)

            value['rules'].clear()
            map(lambda x: value['rules'].update(x.get_for_firewall()),
                self.rules)

            # Nuke the vlan property from <rule>.source
            if self.type is Firewall.types.MANAGEMENT_PORT:
                map(lambda v: 'source' in v and
                              'vlans' in v['source'] and
                              v['source'].pop('vlans'),
                    value['rules'].values())
        else:
            key = obj = None
        return key, obj
