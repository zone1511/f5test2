'''
Created on Jun 10, 2011

@author: jono
'''
from ..base import Macro
from ...utils.net import ip4to6
import logging
import itertools as IT
import netaddr
from .scaffolding import Stamp, make_partitions
from .profile import BuiltinProfile, ClientSsl, ServerSsl
from .ltm import Node, Pool, VirtualServer
from .security import (AddressList, Rule, RuleList, PortList, RuleDestination,
                       RuleSource, Firewall)
from .net import (SelfIP, Vlan, RouteDomain, Trunk)
from .auth import User
from .sys import Provision, Defaults, Platform, DNS, NTP, Mail

PARTITION_COMMON = 'Common'
RD_START = 100
NODE_START = '10.10.0.50'
VIP_START = '10.11.0.50'
LOG = logging.getLogger(__name__)

LOG = logging.getLogger(__name__)
__version__ = '0.1'


def cycle_partition_stamps(dictionary, infinite=True, include_common=True):
    """Given a partition -> list of stamps mapping it will return a similar
    mapping but instead of lists there will be cycle iterators.
    Any non-Common partition will have cycle though Common partition elements
    first then through its own."""
    f = IT.cycle if infinite else lambda x: iter(x)
    g = IT.chain if include_common else lambda x, y: iter(y)
    from_common = dictionary[PARTITION_COMMON]
    return dict((k, f(v) if k == PARTITION_COMMON
                         else f(g(from_common, v)))
                for k, v in dictionary.iteritems())


def take(n, iterable):
    "Return first n items of the iterable as a list"
    return list(IT.islice(iterable, n))


def take_f(n, mapping, folder):
    "Return first n items of the iterable as a list"
    return take(n, mapping[folder.partition().name])


def next_f(mapping, folder):
    return next(mapping[folder.partition().name])


def count_ip(start):
    "Returns an iterator which generates a new IP string each time"
    ip = netaddr.IPAddress(start)
    while True:
        yield str(ip)
        ip += 1


def cycle_ip_network(start):
    "Returns an iterator which generates a new IP/prefix string each time"
    ip = netaddr.IPNetwork(start)
    while True:
        yield str(ip)
        ip.value += 1


class SystemConfig(Macro):

    def __init__(self, context, mgmtip=None, gateway=None, dhcp=False,
                 nameservers=None, suffixes=None, ntpservers=None,
                 timezone=None, partitions=3, provision=None, users=None,
                 smtpserver=None, hostname=None, tree=None):
        self.context = context
        self.mgmtip = netaddr.IPNetwork(mgmtip or '127.0.0.1/24')
        self.gateway = netaddr.IPAddress(gateway or '0.0.0.0')
        self.dhcp = dhcp
        self.nameservers = nameservers
        self.suffixes = suffixes
        self.ntpservers = ntpservers
        self.timezone = timezone
        self.partitions = partitions
        self.provision = provision or {}
        self.users = users or {}
        self.smtpserver = smtpserver
        self.hostname = hostname
        self.tree = tree
        super(SystemConfig, self).__init__()

    def setup(self):
        LOG.info('Platform configuration')
        #context = AttrDict(version=self.version)
        tree = self.tree or make_partitions(count=self.partitions,
                                            context=self.context)
        common = tree[PARTITION_COMMON]
        #all_partitions = tuple(tree.enumerate(False))
        #folder = common.add('folder').add('subfolder')
        #folder = tree['Partition1'].add('folder').add('subfolder')

        # Constants
        common.hook(Defaults())
        # Management IP
        common.hook(Platform(self.mgmtip, self.gateway, self.hostname,
                             dhcp=self.dhcp))
        # DNS
        if self.nameservers:
            common.hook(DNS(self.nameservers, self.suffixes))
        # NTP
        if self.ntpservers:
            common.hook(NTP(self.ntpservers, self.timezone))

        # Mail
        if self.smtpserver:
            common.hook(Mail(self.smtpserver))

        LOG.info('Generating users...')
        for name, specs in self.users.iteritems():
            if isinstance(specs, basestring):
                u = User(name, role=specs)
            else:
                u = User(name, **specs)
            common.hook(u)

        LOG.info('Generating provision...')
        for name, level in self.provision.iteritems():
            p = Provision(name, level)
            common.hook(p)

        return tree


class NetworkConfig(Macro):

    def __init__(self, context, trunks=None, vlans=None, selfips=None,
                tree=None):
        self.context = context
        self.trunks = trunks or {}
        self.vlans = vlans or {}
        self.selfips = selfips or {}
        self.tree = tree
        super(NetworkConfig, self).__init__()

    def setup(self):
        LOG.info('Network configuration')
        tree = self.tree or make_partitions(count=0, context=self.context)
        common = tree[PARTITION_COMMON]

        # This is a simplified configuration where all interfaces in one VLAN
        # can be either tagged or untagged, and - if using trunks - only one
        # trunk is assigned to one VLAN. Trunks have the same name as the VLANs
        # they assigned to.
        if self.trunks:
            LOG.info('Generating trunks...')
            for name, specs in self.trunks.iteritems():
                if isinstance(specs, Stamp):
                    t = specs
                else:
                    t = Trunk(name, specs.interfaces, specs.lacp)
                common.hook(t)

        LOG.info('Generating VLANs...')
        vlan_name_map = {}
        for name, specs in self.vlans.iteritems():
            if isinstance(specs, Stamp):
                v = specs
            else:
                v = Vlan(name=name, untagged=specs.untagged, tagged=specs.tagged,
                         tag=specs.tag)
            common.hook(v)
            vlan_name_map[name] = v

        if self.selfips:
            LOG.info('Generating Self IPs...')
            for vlan, specs in self.selfips.iteritems():
                if isinstance(specs, (basestring, netaddr.IPNetwork)):
                    s = SelfIP(specs, vlan_name_map[vlan])
                    common.hook(s)
                elif isinstance(specs, (list, tuple)):
                    for x in specs:
                        s = SelfIP(vlan=vlan_name_map[vlan], **x)
                        common.hook(s)
                else:
                    s = SelfIP(vlan=vlan_name_map[vlan], **specs)
                    common.hook(s)

        return tree


class LTMConfig(Macro):

    def __init__(self, context, nodes=10, pools=60, members=3, vips=8,
                 node1=NODE_START, vip1=VIP_START, with_monitors=True,
                 tree=None):
        self.context = context
        self.nodes = nodes
        self.pools = pools
        self.members = members
        self.vips = vips
        self.node1 = node1
        self.vip1 = vip1
        self.with_monitors = with_monitors
        self.tree = tree
        super(LTMConfig, self).__init__()

    def setup(self):
        LOG.info('LTM configuration')
        tree = self.tree or make_partitions(count=0, context=self.context)
        common = tree[PARTITION_COMMON]
        all_partitions = tuple(tree.enumerate(False))
        #folder = common.add('folder').add('subfolder')

        LOG.info('Generating built-in profiles in Common partition...')
        profile_serverssl = ServerSsl('serverssl')
        profile_clientssl = ClientSsl('clientssl')
        profile_http = BuiltinProfile('http')
        profile_tcp = BuiltinProfile('tcp')
        common.hook(profile_serverssl, profile_clientssl, profile_http, profile_tcp)

        LOG.info('Generating nodes...')
        #count = IT.count(1)
        default_monitors = ['gateway_icmp'] if self.with_monitors else []
        v4nodes = count_ip(self.node1)
        all_folders = IT.cycle(tree.enumerate())
        all_nodes = dict((x.name, []) for x in all_partitions)
        for _ in range(self.nodes):
            ipv4 = next(v4nodes)
            n = Node(ipv4, name='Node_%s' % _,
                     monitors=default_monitors)
            n6 = Node(ip4to6(ipv4, prefix=16), name='Nodev6_%s' % _,
                      monitors=default_monitors)
            folder = all_folders.next()
            folder.hook(n, n6)
            all_nodes[folder.partition().name] += (n, n6)

        LOG.info('Generating pools...')
        http_ports = IT.repeat(80)
        https_ports = IT.repeat(443)
        monitors = IT.repeat(None)
        http_pools = dict((x.name, []) for x in all_partitions)
        https_pools = dict((x.name, []) for x in all_partitions)
        all_nodes = cycle_partition_stamps(all_nodes)
        for _ in range(self.pools):
            folder = all_folders.next()
            nodes = take(self.members, all_nodes[folder.partition().name])
            p = Pool('Pool%d-a' % _, nodes, http_ports, monitors,
                     pool_monitors=default_monitors)
            p2 = Pool('Pool%d-b' % _, nodes, https_ports, monitors,
                      pool_monitors=default_monitors)
            folder.hook(p, p2)
            http_pools[folder.partition().name].append(p)
            https_pools[folder.partition().name].append(p2)

        LOG.info('Generating virtual servers...')
        http_pools = cycle_partition_stamps(http_pools)
        https_pools = cycle_partition_stamps(https_pools)
        profiles = IT.cycle([(profile_http, profile_tcp),
                             (profile_serverssl, profile_http, profile_tcp),
                             (profile_clientssl, profile_serverssl, profile_http, profile_tcp)])
        # server_profiles = IT.cycle([])
        v4vips = count_ip(self.vip1)
        if not self.vip1:
            self.vips = 0
        for _ in range(self.vips):
            folder = all_folders.next()
            http_pool = http_pools[folder.partition().name].next()
            ipv4 = next(v4vips)
            # profile = profiles.next()
            # http_port = http_ports.next()
            vs = VirtualServer('VS%d-a' % _, ipv4, 80,
                                  http_pool, next(profiles))

            https_pool = https_pools[folder.partition().name].next()
            vs2 = VirtualServer('VS%d-b' % _, ip4to6(ipv4, prefix=16), 80,
                                  https_pool, next(profiles))

            https_pool = https_pools[folder.partition().name].next()
            vs3 = VirtualServer('VS%d-c' % _, ipv4, 443,
                                  https_pool, next(profiles))

            folder.hook(vs, vs2, vs3)
        return tree


class AFMConfig(Macro):

    def __init__(self, context, address_lists=10, port_lists=10, rules=10,
                 rules_lists=10, vlans=0, self_ips=0, route_domains=0,
                 vips=0, tree=None):
        self.context = context
        self.address_lists = address_lists
        self.port_lists = port_lists
        self.rules = rules
        self.rules_lists = rules_lists
        self.vlans = vlans
        self.self_ips = self_ips
        self.route_domains = route_domains
        self.vips = vips
        self.tree = tree
        super(AFMConfig, self).__init__()

    def setup(self):
        LOG.info('AFM configuration')
        tree = self.tree or make_partitions(count=0, context=self.context)
        common = tree[PARTITION_COMMON]
        all_partitions = tuple(tree.enumerate(False))
        all_folders = IT.cycle(tree.enumerate())

        # Cut it short if we're running on a pre-11.3.0 BIGIP.
        v = common.context.version
        if not (v.product.is_bigip and v >= 'bigip 11.3.0'):
            LOG.info('Sorry, no AFM support.')
            return tree

        LOG.info('Generating VLANs...')
        all_vlans = dict((x.name, []) for x in all_partitions)
        all_vlans_nord = dict((x.name, []) for x in all_partitions)
        for _ in range(self.vlans):
            folder = all_folders.next()
            v1 = Vlan('Vlan%d-u' % _)
            v2 = Vlan('Vlan%d-n' % _)
            folder.hook(v1, v2)
            all_vlans[folder.partition().name] += (v1,)
            all_vlans_nord[folder.partition().name] += (v2,)

        LOG.info('Generating address lists...')
        addresses = IT.cycle([('1.1.1.1', '1.1.1.2'),
                             ('1.1.1.0/24', '1.1.2.1', '172.0.0.0/8'),
                             ('::', '0.0.0.0/0'),
                             ('2002::1', 'baad::/16', 'dead:beef::/32')])
        all_address_lists = dict((x.name, []) for x in all_partitions)
        for _ in range(self.address_lists):
            folder = all_folders.next()
            a = AddressList('AddressList%d' % _, next(addresses))
            folder.hook(a)
            all_address_lists[folder.partition().name] += (a,)

        LOG.info('Generating port lists...')
        ports = IT.cycle([(1, 32767, 65535),
                         (443, '443-453', 10000),
                         ('20000-30000', 12345),
                         ('1-65535',)])
        all_port_lists = dict((x.name, []) for x in all_partitions)
        for _ in range(self.port_lists):
            folder = all_folders.next()
            p = PortList('PortList%d' % _, next(ports))
            folder.hook(p)
            all_port_lists[folder.partition().name] += (p,)

        LOG.info('Generating rules...')
        ipv4addresses = count_ip('10.0.0.1')
        ipv6addresses = count_ip('2001::1')
        ports = IT.cycle(xrange(1, 65536))
        address_lists = cycle_partition_stamps(all_address_lists)
        port_lists = cycle_partition_stamps(all_port_lists)
        all_rules = dict((x.name, []) for x in all_partitions)
        vlans = cycle_partition_stamps(all_vlans)
        for _ in range(self.rules):
            folder = all_folders.next()

            destination = RuleDestination()
            destination['address-lists'] = take_f(3, address_lists, folder)
            destination['addresses'] += take(4, ipv4addresses)
            destination['addresses'] += take(6, ipv6addresses)
            destination['port-lists'] = take_f(5, port_lists, folder)
            destination['ports'] = take(6, ports)

            source = RuleSource()
            source['address-lists'] = take_f(3, address_lists, folder)
            source['addresses'] += take(4, ipv4addresses)
            source['addresses'] += take(6, ipv4addresses)
            source['port-lists'] = take_f(5, port_lists, folder)
            source['ports'] = take(6, ports)
            source['vlans'] = take_f(3, vlans, folder)

            r = Rule('Rule%d' % _, destination=destination, source=source)
            #folder.hook(p)
            all_rules[folder.partition().name] += (r,)

        LOG.info('Generating rule lists...')
        all_rule_lists = dict((x.name, []) for x in all_partitions)
        for _ in range(self.rules_lists):
            folder = all_folders.next()
            rules = take(5, all_rules[folder.partition().name])
            rl = RuleList('RuleList%d' % _, rules=rules)
            folder.hook(rl)
            all_rule_lists[folder.partition().name] += (rl,)

        LOG.info('Generating global firewall...')
        rule_lists = cycle_partition_stamps(all_rule_lists)
        fw = Firewall(Firewall.types.GLOBAL,  # @UndefinedVariable
                      rules=take(5, rule_lists[PARTITION_COMMON]))
        folder.hook(fw)

        LOG.info('Generating management firewall...')
        rules = cycle_partition_stamps(all_rules)
        fw = Firewall(Firewall.types.MANAGEMENT_PORT,  # @UndefinedVariable
                      rules=take(5, rules[PARTITION_COMMON]))
        folder.hook(fw)

        LOG.info('Generating Route Domains...')
        all_route_domains = dict((x.name, []) for x in all_partitions)
        vlans = cycle_partition_stamps(all_vlans, infinite=False,
                                       include_common=False)
        vlan_to_rd = {}
        rd_ids = IT.count(RD_START)
        for _ in range(self.route_domains):
            folder = all_folders.next()
            _ = take_f(3, vlans, folder)
            rd = RouteDomain(next(rd_ids), rules=take_f(2, rules, folder) +
                                                 take_f(3, rule_lists, folder),
                             vlans=_)
            vlan_to_rd.update([(v, rd) for v in _])
            folder.hook(rd)
            all_route_domains[folder.partition().name] += (rd,)

        LOG.info('Generating Self IPs...')
        vlans = cycle_partition_stamps(all_vlans)
        vlans_nord = cycle_partition_stamps(all_vlans_nord)
        selfv4 = cycle_ip_network('10.1.0.1/32')
        selfv6 = cycle_ip_network('dead:beef::1/128')
        for _ in range(self.self_ips):
            folder = all_folders.next()

            vlan = next_f(vlans, folder)
            s1 = SelfIP(next(selfv4), vlan=vlan, rd=vlan_to_rd[vlan],
                        name='SelfIP%d' % _, rules=take_f(3, rules, folder))
            s2 = SelfIP(next(selfv6), vlan=vlan, rd=vlan_to_rd[vlan],
                        rules=take_f(5, rules, folder))
            s3 = SelfIP(next(selfv4), vlan=next_f(vlans_nord, folder),
                        rules=take_f(2, rules, folder))
            folder.hook(s1, s2, s3)

        LOG.info('Generating Virtual IPs...')
        profile_tcp = BuiltinProfile('tcp')
        common.hook(profile_tcp)
        route_domains = cycle_partition_stamps(all_route_domains)
        for _ in range(self.vips):
            folder = all_folders.next()

            v1 = VirtualServer('VS%d-a' % _, next(ipv4addresses), 80,
                               rules=take_f(5, all_rules, folder),
                               profiles=[profile_tcp])
            v2 = VirtualServer('VS%d-b' % _, next(ipv6addresses), 443,
                               rules=take_f(5, all_rules, folder),
                               profiles=[profile_tcp])
            v3 = VirtualServer('VS%d-c' % _, next(ipv6addresses), 443,
                               rules=take_f(2, all_rules, folder),
                               profiles=[profile_tcp],
                               rd=next_f(route_domains, folder))
            folder.hook(v1, v2, v3)

        return tree
