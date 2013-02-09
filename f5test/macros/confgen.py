#!/usr/bin/env python
from f5test.interfaces.ssh import SSHInterface
from f5test.interfaces.config import ConfigInterface
from f5test.interfaces.rest.irack import IrackInterface
from f5test.commands.shell import bigpipe as BIGPIPE
from f5test.commands.shell import ssh as SSH
import f5test.commands.shell as SCMD
from f5test.commands.shell.base import SSHCommandError
from f5test.utils.version import Version, Product
from f5test.utils.net import ip4to6
from f5test.utils.parsers.tmsh import tmsh_to_dict
from f5test.macros.base import Macro
from f5test.macros.webcert import WebCert
from f5test.macros.keyswap import KeySwap
from f5test.base import Options
from f5test.defaults import ROOT_USERNAME, ROOT_PASSWORD
from pygraph.algorithms.accessibility import accessibility  # @UnresolvedImport
from pygraph.classes.graph import graph  # @UnresolvedImport
from netaddr import IPAddress, IPNetwork
import logging
import os
import re
import socket
import tempfile
import yaml
from pkg_resources import ResourceManager, get_provider

LOG = logging.getLogger(__name__)

PREFIX_NODE = 'Node'
PREFIX_POOL = 'Pool'
PREFIX_VIP = 'Virtual'
PREFIX_USER = 'User'
PREFIX_PROFILE = 'Profile'
PREFIX_PARTITION = 'Partition'
MIN_VER = '9.3.1'
MAX_VER = '99.9.9'

DEFAULT_NODES = 10
DEFAULT_NODE_START = '10.10.0.50'
DEFAULT_POOLS = 60
DEFAULT_MEMBERS = 1
DEFAULT_VIPS = 8
DEFAULT_PARTITIONS = 0
DEFAULT_ROOT_PASSWORD = ROOT_PASSWORD
DEFAULT_TIMEOUT = 180
DEFAULT_SELF_PREFIX = 16
DEFAULT_BIGPIPE_CONFIG = 'remote_config.default.yaml'
DEFAULT_TMSH_CONFIG = 'remote_config.tmsh.yaml'

# All known 172.27.XXX.0/24 subnets tangent to the VLAN1011.
# This is used for VS address allocation.
SUBNET_MAP = dict([(y, x) for x, y in enumerate((27, 58, 62, 63, 65, 90, 91, 92,
                                                 93, 94, 95, 96, 97, 59, 11))])

__version__ = 1.2


class ConfigGeneratorError(Exception):
    pass


class Nodes(object):
    def __init__(self, level, prefix):
        self._nodes = []
        self._level = level
        self._prefix = prefix

    def __getitem__(self, key):
        if key == len(self._nodes):
            self._nodes.append(Node(key, self._level, self._prefix))
        elif key > len(self._nodes):
            raise Exception('Cannot add item %d' % key)
        return self._nodes[key]

    def __iter__(self):
        return iter(self._nodes)

    def __len__(self):
        return len(self._nodes)


class Node(object):
    """Abstract node used to construct the config graph.

    @param i: a node numeric identifier
    @type i: int
    @param level: the level of this node
    @type level: int
    @param prefix: the node "type" described by a prefix word
    @type prefix: str
    """
    def __init__(self, i, level, prefix):
        self.i = i
        self._level = level
        self._prefix = prefix
        self.data = None
        self.context = {}

    def prefix(self):
        return self._prefix

    def __cmp__(self, other):
        if isinstance(other, Node):
            self_sig = '%d.%s.%d' % (self._level, self._prefix, self.i)
            other_sig = '%d.%s.%d' % (other._level, other._prefix, other.i)
            return cmp(self_sig, other_sig)
        return -1

    def __repr__(self):
        #if self.data is not None:
        #    return '%s.%d <%s>' % (self._prefix, self.i, self.data)
        return '%s.%d' % (self._prefix, self.i)


def merge(user, default):
    if isinstance(user, dict) and isinstance(default, dict):
        for k, v in default.iteritems():
            if k not in user:
                user[k] = v
            else:
                user[k] = merge(user[k], v)
    return user


def extend(cwd, config):
    if isinstance(config.get('$extends'), list):
        for filename in config.get('$extends'):
            filename = os.path.join(cwd, filename)
            base_config = yaml.load(open(filename, 'rb').read())
            config = merge(config, base_config)
    elif isinstance(config.get('$extends'), basestring):
        filename = os.path.join(cwd, config.get('$extends'))
        base_config = yaml.load(open(filename, 'rb').read())
        config = merge(config, base_config)
    return config


class ConfigGenerator(Macro):
    """A macro that's able to configure any TMOS based device. The actual
    configuration is composed off snippets from the config file.

    @param options: an Options instance
    @type options: Options
    """
    def __init__(self, options, address=None, *args, **kwargs):
        self.options = Options(options)

        self.options.setifnone('node_count', DEFAULT_NODES)
        self.options.setifnone('pool_count', DEFAULT_POOLS)
        self.options.setifnone('pool_members', DEFAULT_MEMBERS)
        self.options.setifnone('vip_count', DEFAULT_VIPS)
        self.options.setifnone('partitions', DEFAULT_PARTITIONS)
        self.options.setifnone('password', DEFAULT_ROOT_PASSWORD)
        self.options.setifnone('timeout', DEFAULT_TIMEOUT)

        if self.options.device:
            device = ConfigInterface().get_device(options.device)
            self.address = device.hostname
        else:
            self.address = address

        if self.options.peer_device:
            peer_device = ConfigInterface().get_device(options.peer_device)
            self.options['peer'] = peer_device.address
            self.options['peerpassword'] = peer_device.get_root_creds().password

        self.config = Options()
        self.ssh = None
        self.selfip_internal = None
        self.selfip_external = None
        self._peer = Options()
        self._hostname = None
        self._ip = None
        self._platform = None
        self._product = None
        self._version = None
        self._project = None
        self._status = None
        self._modules = {}
        self._features = {}
        self._provision = {}

        self.f_base = None
        self.f_common = None
        self.f_base_name = None
        self.f_common_name = None

        self._partitions = []
        self._profiles = []
        self._users = []
        self._nodes = []
        self._pools = []
        self._vips = []
        self.g = graph()

        self.can_scf = False
        self.can_partition = False
        self.can_user = False
        self.can_node = False
        self.can_pool = False
        self.can_virtual = False
        self.can_provision = False
        self.can_cluster = False
        self.need_tweak = False
        self.can_not_raum = False
        self.can_net_failover = False
        self.can_tmsh = False
        self.can_folders = False
        self.can_afm = False

        self.formatter = {}
        self.formatter['VERSION'] = __version__
        super(ConfigGenerator, self).__init__(*args, **kwargs)

    def _find_subgraphs(self, filter_out=[], filter_in=[]):
        g = self.g
        acc = accessibility(g)
        subgraphs = []
        if not filter_in:
            filter_in = [PREFIX_PARTITION, PREFIX_NODE, PREFIX_POOL,
                         PREFIX_VIP, PREFIX_USER, PREFIX_PROFILE]
        for key in acc.keys():
            if key.prefix() not in filter_out and \
               key.prefix() in filter_in and \
               acc.get(key):
                tmp = acc[key]
                tmp.sort()
                subgraphs.append(tmp)
                for node in tmp:
                    acc.pop(node)
        return subgraphs

    def _link_roots(self, roots, subgraphs):
        g = self.g

        roots_count = len(roots)
        subgraphs.sort()
        last_length = -1
        for subgraph in subgraphs:
            if len(subgraph) != last_length:
                i = 0
            for node in subgraph:
                g.add_edge(edge=(roots[i % roots_count], node))
            i += 1
            last_length = len(subgraph)

    def _stack_levels(self, levels, parities):
        assert len(levels) > 1
        g = self.g
        j = 0

        level_pre = levels.pop(0)
        for level_cur in levels:
            parity_count = parities[j]
            k = 0
            level_pre_count = len(level_pre)
            for elem in level_cur:
                i = elem.i
                for _ in range(parity_count):
                    g.add_edge(edge=(level_cur[i], level_pre[k % level_pre_count]))
                    k += 1
            level_pre = level_cur
            j += 1

    def _set_modules(self):

        try:
            tokens = SSH.parse_license(ifc=self.ssh, tokens_only=True)
            modules = dict([(k[4:], v) for (k, v) in tokens.items()
                                    if k.startswith('mod_')])
            LOG.info('Licensed modules: %s', modules.keys())
            self._modules = modules

            features = dict([(k, v) for (k, v) in tokens.items()
                                     if not k.startswith('mod_')])
            self._features = features
        except SSH.LicenseParsingError, e:
            LOG.warning('Could not get modules. '
                        'Probably an un-licensed box: %s' % e)

    def _set_platform(self):
        platform_data = SSH.get_platform(ifc=self.ssh)
        LOG.info('Platform: %(platform)s' % platform_data)
        self._platform = platform_data['platform']

    def _set_version(self):
        version_data = SSH.get_version(ifc=self.ssh)
        LOG.info('Version: %s', version_data)

        self._version = version_data
        self._product = version_data.product
        self._project = SCMD.ssh.parse_keyvalue_file('/VERSION',
                                                     ifc=self.ssh).get('project')

    def _set_status(self):
        status = SCMD.ssh.GetPrompt(ifc=self.ssh).run_wait(lambda x: x not in ('INOPERATIVE',),
                                                  progress_cb=lambda x: 'Still inoperative...',
                                                  timeout=self.options.timeout)
        LOG.info('Status: %s', status)
        self._status = status

    def _link_graph(self):
        nodes_per_pool = self.options['pool_members']
        self._stack_levels([self._nodes, self._pools, self._vips],
                           [nodes_per_pool, 1])

        #=======================================================================
        # Sort of a "optimization". When there are no partitions defined
        # don't try to balance anything and gain some speed
        #=======================================================================
        if not self.options['partitions']:
            LOG.info('Putting all objects into Common partition')
            return

        if self.config['options']['put users on Common partition']:
            # Find all subgraphs excluding partition nodes
            subgraphs = self._find_subgraphs([PREFIX_PARTITION, PREFIX_USER,
                                              PREFIX_PROFILE])
            # Balance by "weight" all subgraphs
            self._link_roots(self._partitions, subgraphs)

            subgraphs = self._find_subgraphs(filter_in=[PREFIX_USER,
                                                        PREFIX_PROFILE])
            self._link_roots([self._partitions[0]], subgraphs)

        else:
            subgraphs = self._find_subgraphs([PREFIX_PARTITION])
            self._link_roots(self._partitions, subgraphs)

    def _dump_graph(self):
        subgraphs = self._find_subgraphs()
        LOG.debug('Subgraphs found: %d' % len(subgraphs))
        for subgraph in subgraphs:
            partition_context = {}
            for node in subgraph:
                if node.prefix() is PREFIX_PARTITION:
                    partition_context = node.context
                context = self.formatter
                context.update(partition_context)
                context.update(node.context)
                #print node.data, context
                data = node.data % context
                if node.prefix() is PREFIX_POOL:
                    data = data % context
                self.f_common.write(data)

    def call(self, *args, **kwargs):

        if self.options.get('dry_run'):
            LOG.info('Would call: %s', args)
            return
        ret = SSH.generic(command=args[0], ifc=self.ssh)

        if ret and ret.status:
            LOG.warn(ret)
        else:
            LOG.debug(ret)
        return ret

    def copy(self, src, dst):
        sp = self.ssh.api

        if self.options.get('dry_run'):
            LOG.info('Would copy: %s to %s', src, dst)
            return
        ret = sp.put(src, dst)

        LOG.debug(ret)

    def irack_provider(self, address, username, apikey, mgmtip, timeout=120):
        """Get the static data for a device with a given mgmtip from iRack."""
        data = {}
        with IrackInterface(address=address,
                            timeout=timeout,
                            username=username,
                            password=apikey, proto='http') as irack:
            params = dict(address_set__address__in=mgmtip)
            # Locate the static bag for the F5Asset with mgmtip
            ret = irack.api.staticbag.filter(asset__type=1, **params)

            if ret.data.meta.total_count == 0:
                raise ConfigGeneratorError("No devices with mgmtip=%s found in iRack." % mgmtip)
            if ret.data.meta.total_count > 1:
                raise ConfigGeneratorError("More than one device with mgmtip=%s found in iRack." % mgmtip)

            bag = ret.data.objects[0]
            bagid = bag['id']

            # Get the hostname
            ret = irack.api.staticsystem.filter(bag=bagid)
            assert ret.data.meta.total_count == 1, "No StaticSystem entries for bagid=%s" % bagid
            hostname = ret.data.objects[0]['hostname']
            data['hostname'] = hostname

            # Get all reg_keys
            ret = irack.api.staticlicense.filter(bag=bagid)
            assert ret.data.meta.total_count >= 1, "No StaticLicense entries for bagid=%s" % bagid
            data['licenses'] = {}
            data['licenses']['reg_key'] = [x['reg_key'] for x in ret.data.objects]

            # Get all VLAN -> self IPs pairs
            ret = irack.api.staticaddress.filter(bag=bagid, type=1)
            #assert ret.data.meta.total_count >= 1, "No StaticAddress entries for bagid=%s" % bagid
            data['selfip'] = {}
            for o in ret.data.objects:
                vlan = o['vlan'].split('/')[-1]
                # TODO: IPv6 support...someday?
                if IPAddress(o['address']).version == 4 \
                   and not int(o['floating']):
                    data['selfip'][vlan] = dict(address=o['address'],
                                                netmask=o['netmask'])

            # Get all mgmt ips
            ret = irack.api.staticaddress.filter(bag=bagid, type=0)
            assert ret.data.meta.total_count >= 1, "No StaticAddress entries for bagid=%s" % bagid
            data['mgmtip'] = {}
            for o in ret.data.objects:
                if IPAddress(o['address']).version == 4:
                    data['mgmtip'] = dict(address=o['address'],
                                          netmask=o['netmask'])

            # GW
            ret = irack.api.staticaddress.filter(bag=bagid, type=3)
            assert ret.data.meta.total_count >= 1, "No StaticAddress entries for bagid=%s" % bagid
            for o in ret.data.objects:
                if IPAddress(o['address']).version == 4:
                    data['mgmtip']['gateway'] = o['address']

        LOG.debug(data)
        return {mgmtip: data}

    def try_irack(self, mgmtip):
        # Lookup static values in iRack.
        if self.options.get('irack_address'):
            if not (self.options.get('irack_username') and
                    self.options.get('irack_apikey')):
                raise ValueError("--irack-username and --irack-password are required.")

            LOG.info("Looking up device with mgmtip '%s' in iRack...", mgmtip)
            static = self.config.setdefault('static', {})
            static.update(
                            self.irack_provider(address=self.options.irack_address,
                                                username=self.options.irack_username,
                                                apikey=self.options.irack_apikey,
                                                mgmtip=mgmtip,
                                                timeout=self.options.timeout)
            )
            LOG.info("iRack query was successful.")

    def prepare(self):
        assert self.options['pool_members'] <= self.options['node_count'], \
               "Pool members > Nodes. Please add more nodes!"
        passwd = self.options['password']
        fqdn, _, ip_list = socket.gethostbyname_ex(self.address)
        ip = ip_list[0]
        ltm_label = "{2}-{3}".format(*ip.split('.'))
        self._ip = ip

        # Lookup static values in iRack (if enabled).
        self.try_irack(ip)
        if self.address != ip:
            host = self.address.split('.', 1)[0]
            try:
                domain = fqdn.split('.', 1)[1]
            except IndexError:
                domain = 'test.net'
            self._hostname = "%s.%s" % (host, domain)
        elif self.options.get('hostname'):
            self._hostname = self.options['hostname']
        else:
            if self.config.get('static') and self.config['static'].get(ip) and \
            self.config['static'][ip].get('hostname'):
                self._hostname = self.config['static'][ip]['hostname']
            else:
                self._hostname = 'device{2}-{3}.test.net'

        self._hostname = self._hostname.format(*ip.split('.'))
        LOG.info('Using hostname: %s', self._hostname)

        self.prov = []
        if self.options.get('provision'):
            for prov in self.options['provision'].split(','):
                if prov:
                    bits = prov.lower().split(':', 1)
                    if len(bits) > 1:
                        module, level = bits
                        assert level in ('minimum', 'nominal', 'dedicated')
                    else:
                        module = bits[0]
                        level = 'nominal' if module == 'ltm' else 'minimum'
                    self.prov.append((module, level))

        if self.options.get('peer'):
            _, _, ip_list = socket.gethostbyname_ex(self.options['peer'])
            peer_ip = ip_list[0]
            peer_ltm_label = "{2}-{3}".format(*peer_ip.split('.'))
            peer_passwd = self.options['peerpassword']

            # Lookup static values for peer in iRack (if enabled).
            self.try_irack(peer_ip)

            p = self._peer
            peer_ssh = SSHInterface(address=peer_ip, password=peer_passwd,
                                    timeout=self.options.timeout,
                                    port=self.options.ssh_port)

            ret = BIGPIPE.generic('mgmt list', ifc=peer_ssh)
            address = tmsh_to_dict(ret.stdout)
            p.ip = IPNetwork("{0}/{1}".format(address['mgmt'].keys()[0],
                                       address['mgmt'][address['mgmt'].keys()[0]]['netmask']))

            if self.options.get('peer_selfip_internal'):
                p.selfip_internal = self.options['peer_selfip_internal']
            else:
                try:
                    p.selfip_internal = IPNetwork("{0[selfip][internal][address]}/{0[selfip][internal][netmask]}".
                                            format(self.config['static'][peer_ip]))
                    p.selfip_external = IPNetwork("{0[selfip][external][address]}/{0[selfip][external][netmask]}".
                                            format(self.config['static'][peer_ip]))
                except KeyError:
                    LOG.debug('No Self IP addresses will be set.')

            if self.options.get('unitid'):
                p['unit'] = self.options['unitid']
            else:
                ret = BIGPIPE.generic('db Failover.UnitId', ifc=peer_ssh)
                p['unit'] = int(ret.stdout.strip().split('=')[1]) % 2 + 1

            # The device having UnitID=1 will always try to be the Active one.
            if p['unit'] == 1:
                self.formatter['ltm.id'] = peer_ltm_label
                self.formatter['failover.active'] = 'force active enable'
            else:
                self.formatter['ltm.id'] = ltm_label
                self.formatter['failover.active'] = 'force standby enable'
        else:
            self.formatter['ltm.id'] = ltm_label

        if self.options.get('mgmtip'):
            self.formatter['ltm.ip'] = self.options['mgmtip']
        else:
            self.formatter['ltm.ip'] = ip

        if (self.options.get('selfip_internal') and
            self.options.get('selfip_external')):

            # Internal selfIP
            self.selfip_internal = IPNetwork(self.options.selfip_internal)
            if self.selfip_internal.prefixlen == 32:
                self.selfip_internal.prefixlen = 16
                LOG.warning('Did you mean internal self IP = %s?',
                            self.selfip_internal)

            # External selfIP
            self.selfip_external = IPNetwork(self.options.selfip_external)
            if self.selfip_external.prefixlen == 32:
                self.selfip_external.prefixlen = 16
                LOG.warning('Did you mean internal self IP = %s?',
                            self.selfip_external)

        else:
            try:
                self.selfip_internal = IPNetwork("{0[address]}/{0[netmask]}".format(
                               self.config['static'][ip]['selfip']['internal']))
                self.selfip_external = IPNetwork("{0[address]}/{0[netmask]}".format(
                               self.config['static'][ip]['selfip']['external']))
            except KeyError:
                LOG.debug('No Self IP addresses will be set.')

        if self.selfip_internal:
            LOG.info('Internal selfIP: %s', self.selfip_internal)
        if self.selfip_external:
            LOG.info('External selfIP: %s', self.selfip_external)

        self.ssh = SSHInterface(address=self.address, password=passwd,
                               timeout=self.options.timeout,
                               port=self.options.ssh_port)
        self.ssh.open()

        self._set_platform()
        self._set_version()
        self._set_modules()
        self._set_status()

        if (self._product.is_em and self._version >= 'em 2.0.0') \
        or (self._product.is_bigip and self._version >= 'bigip 9.4.3'):
            self.can_scf = True

        if (self._product.is_em and self._version >= 'em 2.0.0') \
        or (self._product.is_bigip and self._version >= 'bigip 10.0.1'):
            self.can_provision = True
            self.can_net_failover = True

        if (self._product.is_bigip and self._version < 'bigip 9.4.0') \
        or (self._product.is_em and self._version < 'em 2.0.0') \
        or (self._product.is_wanjet and self._version > 'wanjet 5.0.2') \
        or (self._product.is_sam and self._version > 'sam 8.0.0'):
            self.need_tweak = True

        if (self._product.is_bigip and self._version > 'bigip 9.3.2') \
        or (self._product.is_em and self._version >= 'em 1.6.0') \
        or (self._product.is_wanjet and self._version >= 'wanjet 5.0.2') \
        or (self._product.is_sam and self._version >= 'sam 8.0.0'):
            self.can_partition = True
            self.can_user = True

        if self._product.is_bigip:
            self.can_node = True
            self.can_pool = True
            self.can_virtual = True

        if (self._product.is_em and self._version < 'em 2.0.0') \
        or (self._product.is_wanjet and self._version >= 'wanjet 5.0.2') \
        or (self._product.is_sam and self._version >= 'sam 8.0.0'):
            self.can_not_raum = True

        # Only solstice-em EM 3.0 needs the new tmsh-style configuration.
        if (self._product.is_em and self._version >= 'em 3.0.0') \
        or (self._product.is_bigip and self._version >= 'bigip 11.0.0'):
            self.can_tmsh = True
            self.can_folders = True
            #raise NotImplementedError('eh...')

        if self._product.is_bigip and self._version >= 'bigip 11.3.0':
            self.can_afm = True

        # XXX: Temporary workaround before the solstice merges into EM3.0
        #if (self._product.is_em and self._version < 'em 3.0.1'):
        #    self.can_folders = False

        #if self._platform in ['A100', 'A101', 'A107', 'A111']:
        if self._platform.startswith('A') or self._platform in ('D113',):
            self.can_cluster = True

    def pick_configuration(self):

        if self.options.get('config'):
            config_filename = self.options['config']
            cwd = os.path.dirname(os.path.realpath(config_filename))
        else:
            provider = get_provider(__package__)
            manager = ResourceManager()
            config_path = provider.get_resource_filename(manager, '')
            base_dir = os.path.join(config_path, 'configs')
            cwd = os.path.realpath(base_dir)

            if self.can_tmsh:
                config_filename = os.path.join(base_dir, DEFAULT_TMSH_CONFIG)
            else:
                config_filename = os.path.join(base_dir, DEFAULT_BIGPIPE_CONFIG)

        config = yaml.load(file(config_filename, 'rb').read())
        extend(cwd, config)
        self.config.update(config)
        LOG.info('Picked configuration: %s' % config_filename)

    def print_header(self):
        tmpl = self.config['header']
        formatter = self.formatter

        self.f_common.write(tmpl % formatter)

    def print_footer(self):
        tmpl = self.config['footer']
        formatter = self.formatter

        self.f_common.write(tmpl % formatter)

    def print_provision(self):
        if not self.can_provision:
            LOG.info('Provision not supported on the target')
            return
        tmpl = self.config['provision']['template']
        formatter = self.formatter

        if self.prov:
            for module, level in self.prov:
                if module == 'afm' and not self.can_afm:
                    LOG.warning('AFM cannot be provisioned on this target.')
                    continue
                formatter['provision.key'] = module
                formatter['provision.level'] = level
                self._provision[module] = level
                self.f_base.write(tmpl % formatter)
        else:
            # Preserve provisioning.
            modules = SCMD.tmsh.get_provision(ifc=self.ssh)
            for module, level_kv in modules.iteritems():
                if level_kv:
                    level = level_kv['level']
                    formatter['provision.key'] = module
                    formatter['provision.level'] = level
                    self._provision[module] = level
                    self.f_base.write(tmpl % formatter)

    def print_mgmt(self):
        tmpl = self.config['mgmt']
        formatter = self.formatter

        if self.options.mgmtip:
            ip = IPNetwork(self.options.mgmtip)
            if ip.prefixlen == 32:
                ip.prefixlen = 24
                LOG.warning('Assuming /24 to the management IP.')
            mgmtip = {}
            mgmtip['address'] = str(ip.ip)
            mgmtip['netmask'] = str(ip.netmask)
            mgmtip['gateway'] = str(ip.broadcast - 1)
        else:
            mgmtip = self.config['static'].get(self._ip)
            if mgmtip:
                mgmtip = mgmtip.get('mgmtip')

        if mgmtip:
            formatter['ltm.ip'] = mgmtip['address']
            formatter['ltm.netmask'] = mgmtip['netmask']
            formatter['ltm.gateway'] = mgmtip['gateway']
            self.f_base.write(tmpl % formatter)
            return

        # Try to find the existing IP configuration on management interface.
        ret = self.call(r"ethconfig --getcurrent")
        bits = ret.stdout.split()
        ip = IPNetwork("{0[0]}/{0[1]}".format(bits))
        gw = IPAddress(bits[2])

        formatter['ltm.ip'] = str(ip.ip)
        formatter['ltm.netmask'] = str(ip.netmask)
        formatter['ltm.gateway'] = str(gw)

        self.f_base.write(tmpl % formatter)

    def do_generate_vlan(self, tmpl, tags, **kwargs):
        formatter = {}
        formatter.update(kwargs)
        formatter['interfaces'] = ''
        formatter['tag'] = ''
        for tag in re.split('\s+', tags):
            key, value = tag.split('=')
            if key == 'tag':
                formatter[key] = "tag %s\n" % value
            elif key in ('tagged', 'untagged'):
                for interface in value.split(','):
                    label = key if key == 'tagged' else ''
                    formatter['interfaces'] += "%s { %s }\n" % (interface, label)
            else:
                LOG.warning('Unknown key "%s" found in %s', key, tags)
        return tmpl % formatter

    def print_vlan(self):
        root = self.config['vlan']
        trunk = self.config['trunk']
        formatter = self.formatter

        if self.can_cluster:
            if self._platform in ['A100']:
                tmpl = trunk['puma1']
            elif self._platform in ['A108']:
                tmpl = trunk['P8']
            elif self._platform in ['A107', 'A109', 'A111']:
                tmpl = trunk['puma2']

            if self.options.trunks_lacp:
                if self.can_tmsh:
                    formatter['lacp.enabled'] = 'lacp enabled'
                else:
                    formatter['lacp.enabled'] = 'lacp enable'
            else:
                formatter['lacp.enabled'] = ''

            self.f_base.write(tmpl % formatter)

        if self.options.get('vlan_internal') and \
           self.options.get('vlan_external'):
            tmpl = self.do_generate_vlan(root['generic'],
                                         self.options['vlan_internal'],
                                         vlan='internal')
            tmpl += self.do_generate_vlan(root['generic'],
                                          self.options['vlan_external'],
                                          vlan='external')
        else:
            if self._platform in ['Z101']:
                ret = self.call(r"tmsh list net vlan")
                tmpl = ret.stdout
            elif self._platform in ['D84']:
                tmpl = root['D84']
            elif self._platform in ['D100', 'D41']:
                tmpl = root['wanjet']
            elif self._platform in ['SKI23']:
                tmpl = root['SKI23']
            elif self.can_cluster:
                tmpl = root['cluster']
            else:
                tmpl = root['common']

        self.f_base.write(tmpl % formatter)

    def print_self(self):
        formatter = self.formatter
        if self.selfip_internal:
            tmpl = self.config['self internal']
            int_ip6 = ip4to6(self.selfip_internal)
            formatter['self.int_ip.addr'] = str(self.selfip_internal.ip)
            formatter['self.int_ip.prefix'] = self.selfip_internal.prefixlen
            formatter['self.int_ip.netmask'] = str(self.selfip_internal.netmask)
            formatter['self.int_ip6.addr'] = str(int_ip6.ip)
            formatter['self.int_ip6.prefix'] = int_ip6.prefixlen
            formatter['self.int_ip6.netmask'] = str(int_ip6.netmask)
            self.f_base.write(tmpl % formatter)

        if self.selfip_external:
            tmpl = self.config['self external']
            ext_ip6 = ip4to6(self.selfip_external)
            formatter['self.ext_ip.addr'] = str(self.selfip_external.ip)
            formatter['self.ext_ip.prefix'] = self.selfip_external.prefixlen
            formatter['self.ext_ip.netmask'] = str(self.selfip_external.netmask)
            formatter['self.ext_ip6.addr'] = str(ext_ip6.ip)
            formatter['self.ext_ip6.prefix'] = ext_ip6.prefixlen
            formatter['self.ext_ip6.netmask'] = str(ext_ip6.netmask)
            self.f_base.write(tmpl % formatter)

    def print_simple(self, section, dest='base', can_print=True):
        if not can_print:
            LOG.info('Section %s not supported on this target' % section)
            return
        tmpl = self.config[section]
        formatter = self.formatter

        if dest == 'base':
            self.f_base.write(tmpl % formatter)
        else:
            self.f_common.write(tmpl % formatter)

    def print_dns(self):
        root = self.config['dns']
        tmpl = root['template']
        formatter = self.formatter
        formatter['dns.nameservers'] = ''
        formatter['dns.search'] = ''

        if self.can_tmsh:
            formatter['dns.nameservers'] = ' '.join(root['nameservers'])
        else:
            for elem in root['nameservers']:
                formatter['dns.nameservers'] += "%s\n" % elem

        if self.can_tmsh:
            formatter['dns.search'] = ' '.join(root['search'])
        else:
            for elem in root['search']:
                formatter['dns.search'] += "%s\n" % elem

        self.f_base.write(tmpl % formatter)

    def handle_dns(self):
        root = self.config['dns']

        if self.can_scf:
            self.print_dns()
        else:
            tmp = root['nameservers']
            self.call("""b db dns.nameservers '"%s"'""" % ' '.join(tmp))

            tmp = root['search']
            self.call("""b db dns.domainname '"%s"'""" % ' '.join(tmp))

            if self.need_tweak:
                self.call('tw_activate_keys dns.nameservers')

    def print_ntp(self):
        root = self.config['ntp']
        tmpl = root['template']
        formatter = self.formatter
        formatter['ntp.servers'] = ''

        if self.options.get('timezone'):
            tz = self.options['timezone'].replace(' ', '_')
            formatter['ntp.timezone'] = "timezone %s" % tz
        else:
            if self.can_tmsh:
                tz = SCMD.tmsh.list('sys ntp timezone', ifc=self.ssh)
                formatter['ntp.timezone'] = "timezone %s" % tz.sys.ntp.timezone
            else:
                ret = self.call('getdb NTP.TimeZone')
                tz = ret.stdout.strip()
                formatter['ntp.timezone'] = "timezone %s" % tz

        for elem in root['servers']:
            formatter['ntp.servers'] += "%s\n" % elem

        self.f_base.write(tmpl % formatter)

    def handle_ntp(self):
        root = self.config['ntp']

        if self.can_scf:
            self.print_ntp()
        else:
            acc = ''
            for elem in root['servers']:
                acc += "%s " % elem
            self.call('b db ntp.servers %s' % acc.strip())

            if self.need_tweak:
                self.call('tw_activate_keys ntp')

    def handle_failover(self):
        if not self.options.get('peer'):
            LOG.info('No HA setup')
            return
        tmpl = self.config['failover']
        tmpl_nf = self.config['network failover']
        tmpl_sf = self.config['self floating']
        formatter = self.formatter

        p = self._peer
        formatter['peer.int_ip.addr'] = str(p.selfip_internal.ip)
        formatter['peer.ext_ip.addr'] = str(p.selfip_external.ip)
        formatter['peer.int_ip.prefix'] = p.selfip_internal.prefixlen
        formatter['peer.ext_ip.prefix'] = p.selfip_external.prefixlen
        formatter['peer.int_ip.netmask'] = str(p.selfip_internal.netmask)
        formatter['peer.ext_ip.netmask'] = str(p.selfip_external.netmask)
        formatter['self.unit'] = p['unit']
        formatter['peer.ip'] = p['ip']
        formatter['peer.ip.addr'] = str(p['ip'].ip)
        formatter['peer.ip.netmask'] = str(p['ip'].netmask)
        LOG.debug('self.unit = %d', p['unit'])

        if self.can_scf:
            self.f_base.write(tmpl % formatter)
            if self.can_net_failover:
                self.f_base.write(tmpl_nf % formatter)

            if self.options.get('selfip_floating'):
                ip = IPNetwork(self.options['selfip_floating'])
                if ip.prefixlen == 32:
                    raise ValueError("Did you forget to append the prefix to the"
                    "floating ip (e.g. /16)?")
                formatter['self.int_floating.addr'] = str(ip.ip)
                formatter['self.int_floating.netmask'] = str(ip.netmask)
                formatter['peer.ip'] = p['ip']
                self.f_base.write(tmpl_sf % formatter)
        else:
            LOG.info('HA not supported on this target')

    def do_check_availability(self, section):
        value = section.get('min versions', ['bigip 9.0.0'])
        value = value if isinstance(value, list) else value.split(',')
        min_vers = [Version(x) for x in value]

        value = section.get('max versions', ['bigip 99.0.0'])
        value = value if isinstance(value, list) else value.split(',')
        max_vers = [Version(x) for x in value]

        req_mods = section.get('require modules', None)
        req_feats = section.get('require features', None)
        licensed_modules = self._modules
        licensed_features = self._features

        good = True
        v = self._version
        for min_ver in min_vers:
            if v.product == min_ver.product:
                good &= v >= min_ver

        for max_ver in max_vers:
            if v.product == max_ver.product:
                good &= v <= max_ver

        if req_mods:
            for req_mod in req_mods:
                good &= req_mod in licensed_modules

        if req_feats:
            for req_feat in req_feats:
                good &= req_feat in licensed_features

        if good:
            return True

        LOG.debug('Section %s not available.', section)
        return False

    def print_system(self):
        root = self.config['system']
        tmpl = root['template']
        formatter = self.formatter
        formatter['gui.setup'] = root['gui setup']
        formatter['system.hostname'] = self._hostname

        if root.get('mail') and self.do_check_availability(root['mail']):
            tmpl += root['mail']['data']

        self.f_base.write(tmpl % formatter)

    def handle_system(self):
        root = self.config['system']

        if self.can_scf:
            self.print_system()
        else:
            self.call('b db hostname %s' % self._hostname)
            self.call('b db setup.run %s' % (root['gui setup'] == 'disable' and
                                                            'false' or 'true'))
            if self.need_tweak:
                self.call('tw_activate_keys hostname')

    def prepare_partition(self):
        partitions = self.options['partitions']
        pn_tmpl = self.config['partition name template']

        self._partitions = Nodes(1, PREFIX_PARTITION)

        if not self.can_partition:
            LOG.debug('Partitions NOT supported on this target')
            n = self._partitions[0]
            n.data = '# Common partition placeholder\n'
            self.g.add_node(n)
            return

        if self.can_tmsh:
            if self.can_folders:
                tmpl = self.config['partition template']['folders']
            else:
                tmpl = self.config['partition template']['partitions']
        else:
            tmpl = self.config['partition template']

        context = {}
        context['partition.name'] = 'Common'
        context['partition.index'] = 0
        self.formatter.update(context)
        n = self._partitions[0]
        n.data = tmpl
        n.context = context
        self.g.add_node(n)

        if partitions:
            for i in range(partitions):
                context = {}
                context['partition.index'] = i + 1
                self.formatter.update(context)
                context['partition.name'] = pn_tmpl % self.formatter
                n = self._partitions[i + 1]
                n.data = tmpl
                n.context = context
                self.g.add_node(n)

    def prepare_node(self):
        if not self.can_node:
            LOG.debug('Nodes not supported on this target')
            return
        nodes = self.options['node_count']
        tmpl = self.config['node template'][0]
        node_start = IPAddress(self.options.get('node_start') or DEFAULT_NODE_START)
        LOG.info('Nodes: %s (+%d)', node_start, nodes)

        self._nodes = Nodes(3, PREFIX_NODE)
        for i in range(nodes):
            context = {}
            n = self._nodes[i]
            context['node.index'] = i + 1
            context['node.ip'] = str(node_start + i)
            n.data = tmpl
            n.context = context
            self.g.add_node(n)

    def prepare_pool(self):
        if not self.can_pool:
            LOG.debug('Pools not supported on this target')
            return

        nodes = self.options['node_count']
        pools = self.options['pool_count']
        nodes_per_pool = self.options['pool_members']
        tmpl = self.config['pool template'][0]
        pm_tmpl = self.config['pool member template']
        pm_prots = self.config['pool member protocols']
        pm_prots_count = len(pm_prots)
        local_context = {}
        node_start = IPAddress(self.options.get('node_start') or DEFAULT_NODE_START)

        self._pools = Nodes(4, PREFIX_POOL)
        j = 0
        if self.options.get('no_mon'):
            local_context['pool.monitor_enable'] = '#'
        else:
            local_context['pool.monitor_enable'] = ''

        for i in range(pools):
            n = self._pools[i]
            context = {}
            context.update(local_context)
            context['pool.index'] = i + 1
            context['pool.members'] = ''

            separator = ':' if node_start.version == 4 else '.'
            for _ in range(nodes_per_pool):
                pm_context = {}
                pm_context['node.ip'] = str(node_start + j % nodes)
                pm_context['node.ip.separator'] = separator
                pm_context['pool.proto'] = pm_prots[j % pm_prots_count]
                pm_context['pool.monitor'] = pm_context['pool.proto']
                context['pool.members'] += pm_tmpl % pm_context
                j += 1

            n.data = tmpl
            n.context = context
            self.g.add_node(n)

    def prepare_virtual(self):
        if not self.can_virtual:
            LOG.debug('VIPs not supported on this target')
            return

        pools = self.options['pool_count']
        vips = self.options['vip_count']
        if not vips:
            return

        tmpls = self.config['vip template']
        tmpl_count = len(tmpls)
        vip_start = self.options.get('vip_start')
        if not vip_start:
            subnet_id = int(self._ip.split('.')[2])
            host_id = int(self._ip.split('.')[3])
            subnet_index = SUBNET_MAP.get(subnet_id)

            if subnet_index is None:
                raise ValueError('The %d subnet was not found. Please add it to SUBNET_MAP list!' %
                                 subnet_id)

            # Start from 10.11.50.0 - 10.11.147.240 (planned for 10 subnets, 8 VIPs each)
            offset = 1 + 50 * 256 + DEFAULT_VIPS * (256 * subnet_index + host_id)

            vip_start = self.selfip_external.network + offset
        else:
            vip_start = IPAddress(vip_start)

        LOG.info('VIPs: %s (+%d)', vip_start, vips)

        self._vips = Nodes(5, PREFIX_VIP)
        separator = ':' if vip_start.version == 4 else '.'
        for i in range(vips):
            n = self._vips[i]
            context = {}
            context['pool.index'] = i % pools + 1
            context['vip.index'] = i + 1
            context['vip.ip'] = str(vip_start + i)
            context['vip.ip.separator'] = separator
            n.data = tmpls[i % tmpl_count]
            n.context = context
            self.g.add_node(n)

    def prepare_user(self):
        root = self.config['users']

        self._users = Nodes(2, PREFIX_USER)
        i = 0
        for key in root.keys():
            if key == 'policy editor' and \
               (not self._modules.get('asm') or \
               self._version >= 'bigip 10.2.0'):
                LOG.debug('%s user not added. '
                            'Not an ASM target or not supported' % key)
                continue
            if key in ['resource admin', 'user manager'] and \
               self.can_not_raum:
                LOG.debug("%s user not added. "
                        "It hasn't been invented on this target." % key)
                continue
            n = self._users[i]
            n.data = root[key]
            self.g.add_node(n)
            i += 1

    def prepare_profile(self):
        profiles = self.config.get('profiles')
        if profiles is None:
            LOG.info('Profiles disabled')
            return

        if not self.can_virtual:
            LOG.info('Profiles not supported on this product')
            return

        self._profiles = Nodes(2, PREFIX_PROFILE)
        i = 0
        licensed_modules = self._modules
        licensed_features = self._features
        provisioned_modules = self._provision

        for types in profiles:
            min_ver = Version(profiles[types].get('min version', MIN_VER),
                              Product.BIGIP)
            max_ver = Version(profiles[types].get('max version', MAX_VER),
                              Product.BIGIP)
            req_mod = profiles[types].get('require module', None)
            req_feat = profiles[types].get('require feature', None)
            req_prov = profiles[types].get('require provision', None)

            # XXX
            #if types == 'iiop':
            #    print licensed_modules, licensed_features
            # END

            if (self._version >= min_ver and
                self._version <= max_ver and
                (req_mod is None or licensed_modules.get(req_mod)) and
                (req_feat is None or licensed_features.get(req_feat)) and
                (req_prov is None or req_prov in provisioned_modules)
                ):

                tmpl = profiles[types]['text']
                n = self._profiles[i]
                n.data = tmpl
                self.g.add_node(n)
                i += 1

    def handle_user(self):
        if not self.can_user:
            LOG.debug('User not supported on this target. '
                        'Trying with f5passwd')
            # This special admin user is used below for pushing the SSL
            # certificate through iControl.
            SPECIAL_ADMIN_USERNAME = 'a'
            SPECIAL_ADMIN_PASSWORD = 'a'

            try:
                self.call('f5passwd %s %s' % (SPECIAL_ADMIN_USERNAME,
                                              SPECIAL_ADMIN_PASSWORD))
            except SSHCommandError:
                self.call('f5adduser -r admin -n %s' % SPECIAL_ADMIN_USERNAME)
                self.call('f5passwd %s %s' % (SPECIAL_ADMIN_USERNAME,
                                              SPECIAL_ADMIN_PASSWORD))

            root = self.config.get('legacy users')
            if not root:
                return
            if root.get('admin'):
                self.call('f5passwd admin %s' % root['admin'])

            if root.get('root'):
                self.call('f5passwd root %s' % root['root'])

        else:
            root = self.config.get('default users')
            self.prepare_user()

            if not root:
                return
            if self.can_tmsh:
                if root.get('admin'):
                    self.call('tmsh modify auth user admin { encrypted-password %s }' % root['admin'])

                #if root.get('root'):
                #    self.call('tmsh modify auth user root { encrypted-password %s }' % root['root'])

            else:
                if root.get('admin'):
                    self.call('b user admin password crypt %s' % root['admin'])

                if root.get('root'):
                    self.call('b user root password crypt %s' % root['root'])

    def print_graph(self):
        self._link_graph()
        self._dump_graph()

    def handle_license(self):
        ip = self.formatter['ltm.ip']
        try:
            lic = self.options.get('license') or \
                            self.config['static'][ip]['licenses']['reg_key'][0]
        except:
            lic = None

        if self._status in ['NO LICENSE'] and not lic:
            raise Exception('The box needs to be relicensed first.'
                            'Provide --license <regkey>')

        if lic and \
        self._status in ['LICENSE INOPERATIVE', 'NO LICENSE']:
            LOG.info('Licensing...')
            self.call('SOAPLicenseClient --verbose --basekey %s' % lic)
            # We need to re-set the modules based on the new license
            self._set_modules()
            # Tomcat doesn't like the initial licensing through CLI
            if self._product.is_em:
                ret = self.call('bigstart restart tomcat')

        elif self._status in ['LICENSE EXPIRED', 'REACTIVATE LICENSE']:
            LOG.info('Re-Licensing...')
            ret = self.call('SOAPLicenseClient --verbose --basekey `grep '
                             '"Registration Key" /config/bigip.license|'
                             'cut -d: -f2`')
            LOG.debug("SOAPLicenseClient returned: %s", ret)

        else:
            LOG.info('No licensing.')

    def handle_dbvars(self):
        # Workaround for Zenith on ESX with vswitch configuration
        if self._platform in ['Z100', 'Z99']:
            if self._product.is_bigip and self._version <= 'bigip 11.0.0':
                self.call('b db Vlan.MacAssignment vmw-compat')

    def handle_keycert(self):

        options = Options()
        options.admin_username = 'a'
        options.root_username = ROOT_USERNAME
        options.ssh_port = self.options.ssh_port
        options.ssl_port = self.options.ssl_port
        options.verbose = self.options.verbose
        options.timeout = self.options.timeout

        if self.options.get('dry_run'):
            LOG.info('Would push key/cert pair')
            return

        LOG.info('Pushing the key/certificate pair')

        # The special a:a admin user is used here. It should be included in the
        # remote_config yaml config in the users.administrator section.
        options.admin_password = 'a'
        options.root_password = self.options.password

        options.alias = [self._hostname]
        cs = WebCert(options, address=self.address)
        cs.run()

    def handle_sshkey(self):
        if self.options.get('dry_run'):
            LOG.info('Would exchange SSH keys.')
            return

        LOG.info('Exchanging SSH keys...')

        options = Options()
        options.password = self.options.password

        cs = KeySwap(options, address=self.address)
        cs.run()

    @property
    def _is_lvm(self):
        ret = self.call('/usr/lib/install/lvmtest')
        return not ret.status

    @property
    def _is_asm(self):
        modules = SCMD.tmsh.get_provision(ifc=self.ssh)
        return bool(modules.asm)

    def ready_wait(self):
        if self.options.get('dry_run'):
            return

        LOG.info('Waiting for reconfiguration...')
        timeout = self.options['timeout']
        SCMD.ssh.FileExists('/var/run/mprov.pid', ifc=self.ssh).run_wait(lambda x: x is False,
                                             progress_cb=lambda x: 'mprov still running...',
                                             timeout=timeout)
        if self.can_provision and self._is_asm and self._is_lvm:
            SCMD.ssh.FileExists('/var/lib/mysql/.moved.to.asmdbvol',
                                ifc=self.ssh).run_wait(lambda x: x,
                                                 progress_cb=lambda x: 'ASWADB still not there...',
                                                 timeout=timeout)
        # Wait for ASM config server to come up.
        if self.can_provision and self._is_asm:
            LOG.info('Waiting for ASM config server to come up...')
            SCMD.ssh.Generic(r'netstat -anp|grep "9781.*0\.0\.0\.0:\*.*/perl"|wc -l',
                            ifc=self.ssh).run_wait(lambda x: int(x.stdout),
                                                   progress_cb=lambda x: 'ASM cfg server not up...',
                                                   timeout=timeout)

        LOG.info('Waiting for Active prompt...')
        s = SCMD.ssh.GetPrompt(ifc=self.ssh).run_wait(lambda x: x in ('Active',
                                                                     'Standby',
                                                                     'ForcedOffline',
                                                                     'RESTART DAEMONS',
                                                                     'REBOOT REQUIRED'),
                                                  progress_cb=lambda x: 'Still not active...',
                                                  timeout=timeout)

        if s == 'RESTART DAEMONS':
            LOG.info('Restarting daemons...')
            self.call('bigstart restart')
            SCMD.ssh.GetPrompt(ifc=self.ssh).run_wait(lambda x: x in ('Active',
                                                                     'Standby',
                                                                     'ForcedOffline'),
                                                      progress_cb=lambda x: 'Still not active...',
                                                      timeout=timeout)
        elif s == 'REBOOT REQUIRED':
            LOG.warn('A manual reboot is required.')

        if SCMD.ssh.file_exists('/var/run/grub.conf.lock', ifc=self.ssh):
            self.ssh.api.remove('/var/run/grub.conf.lock')

    def clean_config(self):
        LOG.info('Cleaning up config on the target')
        self.open_config()
        try:
            self.print_header()
            self.print_provision()
            self.print_mgmt()
            self.handle_dns()
            self.handle_ntp()
            self.handle_system()
            self.print_footer()
            self.close_config()

            self.load_config()
            # 012e0028:3: There is no valid configuration to save.
            self.save_config()
        finally:
            self.close_config()
            self.remove_config()

    def save_config(self):
        LOG.info('Saving new config...')
        if self.can_tmsh:
            self.call('tmsh save sys config partitions all')
        else:
            self.call('b base save')
            self.call('b save')

    def open_config(self):
        LOG.debug('Open temporary config files')
        if self.can_scf:
            fd, self.f_base_name = tempfile.mkstemp(prefix='confgen-',
                                                        text=True)
            self.f_common = self.f_base = os.fdopen(fd, "w")
            LOG.debug('temp filename: %s', self.f_base_name)
        else:
            fd, self.f_base_name = tempfile.mkstemp(prefix='confgenb-',
                                                        text=True)
            self.f_base = os.fdopen(fd, "w")
            LOG.debug('base temp filename: %s', self.f_base_name)

            fd, self.f_common_name = tempfile.mkstemp(prefix='confgenc-',
                                                        text=True)
            self.f_common = os.fdopen(fd, "w")
            LOG.debug('common temp filename: %s', self.f_common_name)

    def close_config(self):
        LOG.debug('Close temporary config files')
        if self.can_scf:
            self.f_base and self.f_base.close()
            self.f_base = None
        else:
            self.f_base and self.f_base.close()
            self.f_common and self.f_common.close()
            self.f_base = self.f_common = None

    def remove_config(self):
        if self.f_base_name:
            os.remove(self.f_base_name)
            self.f_base_name = None
        if self.f_common_name:
            os.remove(self.f_common_name)
            self.f_common_name = None

    def load_default_config(self):

        if self.can_tmsh:
            LOG.info('Importing default config...')
            self.call('tmsh load sys config default')
        elif self.can_scf:
            LOG.info('Importing default config...')
            self.call('b import default')
        else:
            LOG.warning('Not implemented for this version/platform.')

    def load_config(self):

        if self.can_tmsh:
            LOG.info('Copying the new TMSH SCF config')
            LOG.debug(self.copy(self.f_base_name, '/tmp/config.scf'))

            LOG.info('Importing new config...')
            self.call('tmsh load sys config file /tmp/config.scf')

            LOG.info('Resetting Trust...')
            # XXX: workaround for 357822
            # XXX: disable altogether as w/o for 360368
            # XXX: disable it again as w/o for 362126
            # XXX: disable it again: for 362853
            if self.can_folders and not self.options.get('dry_run'):
                #self.call('bigstart restart devmgmtd')
                #self.call('tmsh delete cm trust-domain all')
                SCMD.ssh.Generic('tmsh delete cm trust-domain all', ifc=self.ssh).\
                    run_wait(lambda x: x.status == 0,
                             progress_cb=lambda x: 'delete trust-domain retry...',
                             timeout=self.options.timeout)

        elif self.can_scf:
            LOG.info('Copying the new SCF config')
            LOG.debug(self.copy(self.f_base_name, '/tmp/config.scf'))

            LOG.info('Importing new config...')
            self.call('b import /tmp/config.scf')
        else:
            LOG.info('Copying the new base config')
            LOG.debug(self.copy(self.f_base_name, '/config/bigip_base.conf'))

            LOG.info('Copying the new common config')
            LOG.debug(self.copy(self.f_common_name, '/config/bigip.conf'))

            self.call('b load')

    def cleanup(self):
        LOG.debug('Cleanup temporary files')
        if self.ssh:
            self.ssh.close()

        self.close_config()
        self.remove_config()
        LOG.info('Done.')

    def setup(self):
        self.prepare()
        self.pick_configuration()
        self.handle_license()

        if self.options.get('clean'):
            self.load_default_config()
            self.ready_wait()
            self.clean_config()
            self.ready_wait()
            return

        try:
            self.clean_config()
        except:
            LOG.warning("Clean config failed, it may be harmless if there's no "
                        "valid configuration to save")

        self.open_config()
        self.print_header()
        self.print_provision()
        self.print_mgmt()
        self.print_vlan()
        self.print_self()
        self.print_simple('stp')
        self.print_simple('self allow')
        self.handle_dns()
        self.handle_ntp()
        self.handle_failover()
        self.handle_system()

        if not self.options.get('no_mon'):
            self.print_simple('monitors', 'common', not \
                (self._modules.get('wj') or self._modules.get('em')))
        self.prepare_partition()
        self.handle_user()
        self.prepare_profile()
        self.prepare_node()
        self.prepare_pool()
        self.prepare_virtual()

        self.print_graph()
        self.print_footer()
        self.close_config()

        self.load_config()
        self.save_config()
        self.handle_dbvars()
        self.handle_keycert()
        self.handle_sshkey()
        self.ready_wait()


def main(*args, **kwargs):
    import optparse
    import sys

    LOG = logging.getLogger('remote_config')

    class OptionWithDefault(optparse.Option):
        strREQUIRED = 'required'
        ATTRS = optparse.Option.ATTRS + [strREQUIRED]

        def __init__(self, *opts, **attrs):
            if attrs.get(self.strREQUIRED, False):
                attrs['help'] = '(Required) ' + attrs.get('help', "")
            optparse.Option.__init__(self, *opts, **attrs)

    class OptionParser(optparse.OptionParser):
        strREQUIRED = 'required'

        def __init__(self, **kwargs):
            kwargs['option_class'] = OptionWithDefault
            optparse.OptionParser.__init__(self, **kwargs)

        def check_values(self, values, args):
            for option in self.option_list:
                if hasattr(option, self.strREQUIRED) and option.required:
                    if not getattr(values, option.dest):
                        self.error("option %s is required" % (str(option)))
            return optparse.OptionParser.check_values(self, values, args)

    def _parser():
        usage = """%prog [options] <address>"""

        formatter = optparse.TitledHelpFormatter(max_help_position=30)
        p = OptionParser(
                usage=usage,
                formatter=formatter,
                version="LTM Config Generator %s" % __version__,
        )

        p.add_option("-c", "--config", metavar="FILE", type="string",
                     help="Use this config template. (default: auto)")

        p.add_option("", "--partitions", metavar="NUMBER",
                     default=DEFAULT_PARTITIONS, type="int",
                     help="How many partitions. (default: %d)" % DEFAULT_PARTITIONS)
        p.add_option("", "--node-start", metavar="IP", type="string",
                     help="The start address for nodes. (default: 10.10.0.50)")
        p.add_option("-n", "--node-count", metavar="NUMBER",
                     default=DEFAULT_NODES, type="int",
                     help="How many nodes. (default: %d)" % DEFAULT_NODES)
        p.add_option("-o", "--pool-count", metavar="NUMBER",
                     default=DEFAULT_POOLS, type="int",
                     help="How many pools. (default: %d)" % DEFAULT_POOLS)
        p.add_option("", "--pool-members", metavar="NUMBER",
                     default=DEFAULT_MEMBERS, type="int",
                     help="How many pool members per pool. (default: %d)" % DEFAULT_MEMBERS)
        p.add_option("", "--vip-start", metavar="IP", type="string",
                     help="The start address for vips. (default: auto)")
        p.add_option("-v", "--vip-count", metavar="NUMBER",
                     default=DEFAULT_VIPS, type="int",
                     help="How many Virtual IPs. (default: %d)" % DEFAULT_VIPS)
        p.add_option("-p", "--password", metavar="STRING",
                     type="string", default=DEFAULT_ROOT_PASSWORD,
                     help="SSH root Password. (default: %s)" % DEFAULT_ROOT_PASSWORD)

        p.add_option("", "--peer", metavar="HOST",
                     type="string",
                     help="Make an HA pair with this device")
        p.add_option("", "--peer-selfip-internal", metavar="IP",
                     type="string",
                     help="Peer self IP address for internal vlan.")
        p.add_option("", "--peerpassword", metavar="STRING",
                     type="string", default=DEFAULT_ROOT_PASSWORD,
                     help="Peer's SSH root password. (default: %s)" % DEFAULT_ROOT_PASSWORD)

        p.add_option("", "--hostname", metavar="HOSTNAME",
                     type="string",
                     help="The device hostname")
        p.add_option("", "--mgmtip", metavar="IP/PREFIX",
                     type="string",
                     help="The device management address (if different from --ltm)")
        p.add_option("", "--ssl-port", metavar="INTEGER", type="int", default=443,
                     help="SSL Port. (default: 443)")
        p.add_option("", "--ssh-port", metavar="INTEGER", type="int", default=22,
                     help="SSH Port. (default: 22)")
        p.add_option("", "--selfip-internal", metavar="IP[/PREFIX]",
                     type="string",
                     help="Self IP address for internal vlan.")
        p.add_option("", "--selfip-external", metavar="IP[/PREFIX]",
                     type="string",
                     help="Self IP address for external vlan.")
        p.add_option("", "--selfip-floating", metavar="IP/PREFIX",
                     type="string",
                     help="Floating self IP address on the internal vlan for HA.")
        p.add_option("", "--vlan-internal", metavar="KEY-VALUE PAIRS",
                     type="string",
                     help="Internal VLAN configuration. (e.g 'tag=1111 tagged=1.1 untagged=1.2')")
        p.add_option("", "--vlan-external", metavar="IP[/PREFIX]",
                     type="string",
                     help="External VLAN configuration. (e.g 'tag=1112 tagged=1.1 untagged=1.2')")
        p.add_option("", "--trunks-lacp",
                     action="store_true",
                     help="Enable LACP on bonth internal and external trunks. (Clusters only)")
        p.add_option("", "--provision", metavar="MODULE:[LEVEL],[MODULE:LEVEL]",
                     type="string",
                     help="Provision module list")
        p.add_option("", "--license", metavar="REGKEY",
                     type="string",
                     help="Set the license")
        p.add_option("", "--timezone", metavar="ZONE",
                     type="string",
                     help="Set the timezone. (e.g. 'America/Los Angeles')")
        p.add_option("", "--clean",
                     action="store_true",
                     help="Clean vips, pools, nodes on the target")

        p.add_option("", "--irack-address", metavar="HOSTNAME",
                     type="string",
                     help="The iRack hostname or IP address")
        p.add_option("", "--irack-username", metavar="STRING",
                     type="string",
                     help="Username used to authenticate with iRack.")
        p.add_option("", "--irack-apikey", metavar="STRING",
                     type="string",
                     help="API key used to authenticate with iRack")

        p.add_option("", "--dry-run",
                     action="store_true",
                     help="Don't execute or copy anything to the target")
        p.add_option("", "--no-mon",
                     action="store_true",
                     help="Don't set monitors for nodes and pool members. Useful for huge configs.")
        p.add_option("", "--no-sshkey",
                     action="store_true",
                     help="Don't exchange SSH keys.")
        p.add_option("", "--timeout",
                     default=DEFAULT_TIMEOUT, type="int",
                     help="The SSH timeout. (default: %d)" % DEFAULT_TIMEOUT)
        p.add_option("", "--verbose",
                     action="store_true",
                     help="Debug messages")
        return p

    p = _parser()
    options, args = p.parse_args()

    if options.verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO
        # Shut paramiko's mouth
        logging.getLogger('paramiko.transport').setLevel(logging.ERROR)
        logging.getLogger('f5test').setLevel(logging.ERROR)
        logging.getLogger('f5test.macros').setLevel(logging.INFO)

    LOG.setLevel(level)
    logging.basicConfig(level=level)

    if not args:
        p.print_version()
        p.print_help()
        sys.exit(2)

    cg = ConfigGenerator(options, address=args[0])
    cg.run()

if __name__ == '__main__':
    main()
