'''
Created on Apr 12, 2013

@author: jono
'''
from .scaffolding import Stamp
import itertools
import netaddr
from ...utils.parsers import tmsh
from ...utils.parsers.tmsh import RawEOL


class Node(Stamp):
    TMSH = """
        ltm node %(key)s {
           address 10.10.0.1
           #limit 100
           #ratio 1
        }
    """
    BIGPIPE = """
        node %(address)s {
           screen Node-name
           #limit 100
           #ratio 1
        }
    """

    def __init__(self, address, name=None, rd=None, monitors=None):
        self.address = str(address)
        self.name = name or str(address)
        self.rd = rd
        self.monitors = monitors or []
        super(Node, self).__init__()

    def from_template(self, name):
        "This is a major speedup over the deepcopy version"
        if name == 'TMSH':
            return tmsh.GlobDict({'ltm node %(key)s': {}})
        return super(Node, self).from_template(name)

    def tmsh(self, obj):
        v = self.folder.context.version
        if v.product.is_bigip:
            key = self.folder.SEPARATOR.join((self.folder.key(), self.name))
            value = obj.rename_key('ltm node %(key)s', key=key)
            address = self.address + '%%%d' % self.rd.id_ if self.rd else self.address
            value['address'] = address
            if self.monitors:
                value['monitor'] = tmsh.RawString(' and '.join(self.monitors))
            return key, obj

    def bigpipe(self, obj):
        v = self.folder.context.version
        if v.product.is_bigip:
            key = self.name
            value = obj.rename_key('node %(address)s', address=self.address)
            value['screen'] = self.name
            if self.monitors:
                value['monitor'] = tmsh.RawString(' and '.join(self.monitors))
            return key, obj


class Pool(Stamp):
    TMSH = """
        ltm pool %(key)s {
            monitor /Common/gateway_icmp
            members {
                /Common/a/b/node_b:80 {
                    address 2002::b
                }
                /Common/a/node_a:80 {
                    address 2002::a
                }
                /Common/aa/node_aa:80 {
                    address 2002::aa
                }
            }
        }
    """
    BIGPIPE = """
        pool %(name)s {
           monitor all gateway_icmp and http
           members
              10.10.0.50:http
              monitor gateway_icmp
              10.10.0.51:http
              ratio 3
              monitor gateway_icmp and http and https
        }
    """

    def __init__(self, name, nodes, ports, monitors, pool_monitors=None):
        self.name = name
        self.nodes = nodes
        self.ports = ports
        self.monitors = monitors
        self.pool_monitors = pool_monitors
        super(Pool, self).__init__()

    def from_template(self, name):
        "This is a major speedup over the deepcopy version"
        if name == 'TMSH':
            return tmsh.GlobDict({'ltm pool %(key)s': {'members': {},
                                                       'monitor': None}})
        return super(Pool, self).from_template(name)

    def get_separator(self, address):
        if netaddr.IPAddress(address).version == 4:
            return ':'
        else:
            return '.'

    def set_monitor(self, value, monitor):
        monitors = ''
        if isinstance(monitor, basestring):
            monitors += monitor
        else:
            if monitor:
                monitors += ' and '.join(monitor)

        if monitors:
            value['monitor'] = tmsh.RawString(monitors)

    def tmsh(self, obj):
        v = self.folder.context.version
        if v.product.is_bigip:
            key = self.folder.SEPARATOR.join((self.folder.key(), self.name))
            value = obj.rename_key('ltm pool %(key)s', key=key)

            if self.pool_monitors:
                value.update({'monitor': ' and '.join(self.pool_monitors)})
            else:
                value.pop('monitor')

            members = value['members']
            members.clear()
            for node, port, monitor in itertools.izip(self.nodes,
                                                      self.ports,
                                                      self.monitors):
                member = node.get(reference=True)
                if member == node.address:
                    sep = self.get_separator(member)
                else:
                    sep = ':'
                member = '%s%s%s' % (member, sep, port)

                members[member] = {'address': node.address}
                self.set_monitor(members[member], monitor)
            return key, obj

    def bigpipe(self, obj):
        v = self.folder.context.version
        if v.product.is_bigip:
            key = self.name
            value = obj.rename_key('pool %(name)s', name=self.name)
            value.clear()
            if self.pool_monitors:
                value.update({tmsh.RawString('monitor all'): ' and '.join(self.pool_monitors)})
            value.update({'members': RawEOL})
            for node, port, monitor in itertools.izip(self.nodes,
                                                      self.ports,
                                                      self.monitors):
                address = node.address
                sep = self.get_separator(address)
                member = '%s%s%s' % (address, sep, port)

                value[member] = RawEOL
                self.set_monitor(value, monitor)
            return key, obj


class VirtualServer(Stamp):
    TMSH = """
        ltm virtual %(key)s {
            destination 10.11.0.1:80
            snat automap
            ip-protocol tcp
            fw-rules {
            }
            profiles {
                /Common/serverssl {
                    context serverside
                }
                /Common/clientssl {
                    context clientside
                }
                /Common/http { }
                /Common/tcp { }
            }
            pool none
        }
        ltm virtual-address %(key_va)s {
            address 10.11.0.1
            mask 255.255.255.255
            traffic-group /Common/traffic-group-1
        }
    """
    BIGPIPE = """
        virtual %(name)s {
           destination 10.11.0.1:80
           snat automap
           ip protocol tcp
           profile clientssl serverssl http tcp
           pool none
        }
    """

    def __init__(self, name, address, port, pool=None, profiles=None, rules=None,
                 rd=None):
        self.name = name
        self.address = str(address)
        self.port = port
        self.pool = pool
        self.profiles = profiles or []
        self.rules = rules or []
        self.rd = rd
        super(VirtualServer, self).__init__()

    def from_template(self, name):
        "This is a major speedup over the deepcopy version"
        if name == 'TMSH':
            return tmsh.GlobDict({'ltm virtual %(key)s': {'profiles': {},
                                                          'fw-rules': {},
                                                          'snat': 'automap',
                                                          'ip-protocol': 'tcp',
                                                          'pool': 'none'},
                                  'ltm virtual-address %(key_va)s': {}})
        return super(VirtualServer, self).from_template(name)

    def get_address_port(self):
        if netaddr.IPAddress(self.address).version == 4:
            sep = ':'
        else:
            sep = '.'
        address = self.address + '%%%d' % self.rd.id_ if self.rd else self.address
        return "%s%s%s" % (address, sep, self.port)

    def tmsh(self, obj):
        ctx = self.folder.context
        v = ctx.version
        if v.product.is_bigip:
            folder_path = self.folder.key()
            key = self.folder.SEPARATOR.join((folder_path, self.name))
            key_va = self.folder.SEPARATOR.join((folder_path, self.address))
            obj = self.from_template('TMSH')

            # Update the virtual part
            value = obj.rename_key('ltm virtual %(key)s', key=key)
            value['destination'] = self.get_address_port()
            value['profiles'].clear()
            for profile in self.profiles:
                value['profiles'].update(profile.get_vs_profile())

            if self.pool:
                value['pool'] = self.pool.get(reference=True)

            if ctx.provision.afm and self.rules:
                value['fw-rules'].clear()
                map(lambda x: value['fw-rules'].update(x.get_for_firewall()),
                    self.rules)
            else:
                #LOG.info('AFM not provisioned')
                value.pop('fw-rules')

            # Update the virtual-address part
            value = obj.rename_key('ltm virtual-address %(key_va)s',
                                   key_va=key_va)
            value['address'] = self.address + '%%%d' % self.rd.id_ if self.rd \
                                                                   else self.address
            return key, obj

    def bigpipe(self, obj):
        v = self.folder.context.version
        if v.product.is_bigip:
            key = self.name
            obj = self.from_template('BIGPIPE')
            value = obj.rename_key('virtual %(name)s', name=self.name)
            value.clear()
            value['destination'] = self.get_address_port()
            value['profiles'] = tmsh.RawString(' '.join([x.get_vs_profile() for x in self.profiles]))
            if self.pool:
                value['pool'] = self.pool.get(reference=True)
            return key, obj
