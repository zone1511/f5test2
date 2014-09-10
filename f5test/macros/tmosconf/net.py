'''
Created on Apr 12, 2013

@author: jono
'''
from .scaffolding import Stamp
from ...utils.parsers.tmsh import RawDict, RawEOL
from netaddr import IPNetwork


can_tmsh = lambda v: (v.product.is_bigip and v >= 'bigip 11.0.0' or
                      v.product.is_em and v >= 'em 2.0.0' or
                      v.product.is_bigiq)


class SelfIP(Stamp):
    TMSH = """
        net self %(key)s {
            address fd32:f5:0:a0a::15ec/64
            allow-service {
                default
            }
            fw-rules {
                aaaaa {
                    description none
                    rule-list rule_list1
                }
                bbbb {
                    rule-list _sys_self_allow_all
                }
            }
            vlan internal
        }
    """
    BIGPIPE = """
        self %(address)s {
           netmask 255.255.0.0
           vlan internal
           allow default
        }
    """

    def __init__(self, address, vlan, name=None, allow=None, rules=None, rd=None):
        self.address = address if isinstance(address, IPNetwork) else IPNetwork(address)
        self.vlan = vlan
        self.name = name or str(address).replace('/', '_')
        self.allow = allow or ['default']
        self.rules = rules or []
        self.rd = rd
        super(SelfIP, self).__init__()

    def tmsh(self, obj):
        # We don't want to use tmsh to set selfIPs on BIGIQ because of reasons.
        v = self.folder.context.version
        if v.product.is_bigiq and v >= 'bigiq 4.2.0':
            return None, None
        key = self.folder.SEPARATOR.join((self.folder.key(), self.name))
        value = obj.rename_key('net self %(key)s', key=key)
        value['allow-service'] = dict((x, RawEOL) for x in self.allow)
        #value['fw-rules'] = dict((x, RawEOL) for x in self.rules)
        if self.rules:
            value['fw-rules'].clear()
            map(lambda x: value['fw-rules'].update(x.get_for_firewall()),
                self.rules)
        else:
            #LOG.info('AFM not provisioned')
            value.pop('fw-rules')
        rd_suffix = '%' + str(self.rd.id_) if self.rd else ''
        #value['address'] = "{0.ip}{1}/{0.prefixlen}".format(self.address, rd_suffix)
        value['address'] = str(self.address).replace('/', rd_suffix + '/')
        value['vlan'] = self.vlan.get(reference=True)
        return key, obj

    def bigpipe(self, obj):
        key = str(self.address.ip)
        value = obj.rename_key('self %(address)s', address=key)
        value['netmask'] = str(self.address.netmask)
        if len(self.allow) == 1:
            value['allow'] = self.allow[0]
        else:
            value['allow'] = dict(x.split(':') for x in self.allow)
        value['vlan'] = self.vlan.get(reference=True)
        return key, obj


class Trunk(Stamp):
    TMSH = """
        net trunk %(name)s {
            lacp disabled
            interfaces {
                1/1.2
                2/1.2
                3/1.2
                4/1.2
                5/1.2
                6/1.2
                7/1.2
                8/1.2
            }
        }
    """
    BIGPIPE = """
        trunk %(name)s {
            lacp disable
            interfaces {
                1/1.1
                2/1.1
                3/1.1
                4/1.1
            }
        }
    """

    def __init__(self, name, interfaces=None, lacp=None):
        self.name = name
        self.interfaces = interfaces or set()
        self.lacp = lacp
        super(Trunk, self).__init__()

    def compile(self):
        v = self.folder.context.version
        if can_tmsh(v):
            key = self.folder.SEPARATOR.join((self.folder.key(), self.name))
            obj = self.from_template('TMSH')
            value = obj.rename_key('net trunk %(name)s', name=self.name)
            if self.interfaces:
                value['interfaces'].clear()
                value['interfaces'].update(dict((x, RawEOL) for x in self.interfaces))
            else:
                value.pop('interfaces')
            if self.lacp:
                value['lacp'] = 'enabled'
        else:
            key = obj = None
        return key, obj


class Vlan(Stamp):
    TMSH = """
        net vlan %(name)s {
#            if-index 128
            partition Part1
            interfaces {
                1.3 {
                    tagged
                }
            }
#            tag 4092
        }
    """
    BIGPIPE = """
        vlan %(name)s {
           interfaces {
               1.1
           }
        }
    """

    def __init__(self, name, untagged=None, tagged=None, tag=None):
        self.name = name
        self.untagged = untagged or []
        self.tagged = tagged or []
        self.tag = tag
        super(Vlan, self).__init__()

    def tmsh(self, obj):
        key = self.folder.SEPARATOR.join((self.folder.key(), self.name))
        partition = self.folder.partition().name
        value = obj.rename_key('net vlan %(name)s', name=self.name)
        value['description'] = self.name
        value['partition'] = partition
        if self.untagged or self.tagged:
            value['interfaces'].clear()
            value['interfaces'].update(dict((x, []) for x in self.untagged))
            value['interfaces'].update(dict((x, ['tagged']) for x in self.tagged))
        else:
            value.pop('interfaces')
        if self.tagged:
            value['tag'] = self.tag
        return key, obj

    def bigpipe(self, obj):
        v = self.folder.context.version
        key = self.name
        #partition = self.folder.partition().name
        if v.product.is_bigip and v < 'bigip 10.0':
            D = RawDict
        else:
            D = dict

        value = obj.rename_key('vlan %(name)s', name=self.name)
        if self.untagged:
            value['interfaces'] = D()
            value['interfaces'].update(D((x, RawEOL) for x in self.untagged))
        else:
            value.pop('interfaces')

        if self.tagged:
            value['tag'] = self.tag
            value['interfaces tagged'] = D()
            value['interfaces tagged'].update(D((x, RawEOL) for x in self.tagged))

        return key, obj


class RouteDomain(Stamp):
    TMSH = """
        net route-domain %(name)s {
            description "Default Route Domain"
            id 0
            partition Common
#            parent /Common/0
            fw-rules {
                aaaaa {
                    description none
                    rule-list rule_list1
                }
                bbbb {
                    rule-list _sys_self_allow_all
                }
            }
            vlans {
                /Part1/ha
                /Part1/ga-ha
                internal
                external
                v1-a
            }
        }
    """

    def __init__(self, id_, name=None, vlans=None, parent=None, rules=None):
        self.id_ = id_
        self.name = name or id_
        self.vlans = vlans or []
        self.parent = parent
        self.rules = rules or []
        super(RouteDomain, self).__init__()

    def compile(self):
        ctx = self.folder.context
        v = ctx.version
        if can_tmsh(v):
            key = self.name
            partition = self.folder.partition().name
            obj = self.from_template('TMSH')
            value = obj.rename_key('net route-domain %(name)s', name=self.name)
            value['id'] = self.id_
            value['partition'] = partition
            if self.vlans:
                value['vlans'].clear()
                value['vlans'].update(dict((x.get(reference=True), RawEOL) for x in self.vlans))
            else:
                value.pop('vlans')
            if self.parent:
                value['parent'] = self.parent

            if ctx.provision.afm and self.rules:
                value['fw-rules'].clear()
                map(lambda x: value['fw-rules'].update(x.get_for_firewall()),
                    self.rules)
            else:
                #LOG.info('AFM not provisioned')
                value.pop('fw-rules')
        else:
            key = obj = None
        return key, obj
