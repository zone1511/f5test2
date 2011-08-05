#!/usr/bin/env python
from f5test.interfaces.ssh import SSHInterface
from f5test.interfaces.config import ConfigInterface
from f5test.interfaces.irack import IrackInterface
from f5test.commands.shell import bigpipe as BIGPIPE
from f5test.commands.shell import ssh as SSH
import f5test.commands.shell as SCMD
from f5test.utils.version import Version, Product
from f5test.macros.base import Macro
from f5test.macros.webcert import WebCert
from f5test.base import Options
from f5test.defaults import ROOTCA_STORE, ADMIN_USERNAME, ROOT_USERNAME, ROOT_PASSWORD
from pygraph.algorithms.accessibility import accessibility #@UnresolvedImport
from pygraph.classes.graph import graph #@UnresolvedImport
import logging
import os
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
DEFAULT_NODE_OFFSET = 50
DEFAULT_POOLS = 60
DEFAULT_MEMBERS = 1
DEFAULT_VIPS = 60
DEFAULT_PARTITIONS = 3
DEFAULT_ROOT_PASSWORD = ROOT_PASSWORD
DEFAULT_TIMEOUT = 180
DEFAULT_CONFIG = 'remote_config.yaml'
if os.name == 'nt':
    DEFAULT_ROOTCA_PATH = r'\\wendy\vols\3\share\em-selenium\root_ca'
else:
    DEFAULT_ROOTCA_PATH = '/vol/3/share/em-selenium/root_ca'

__version__ = 1.0


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
        return - 1

    def __repr__(self):
        #if self.data is not None:
        #    return '%s.%d <%s>' % (self._prefix, self.i, self.data)
        return '%s.%d' % (self._prefix, self.i)


def merge(user, default):
    if isinstance(user, dict) and isinstance(default,dict):
        for k,v in default.iteritems():
            if k not in user:
                user[k] = v
            else:
                user[k] = merge(user[k],v)
    return user

def extend(cwd, config):
    if isinstance(config.get('$extends'), list):
        for file in config.get('$extends'):
            file = os.path.join(cwd, file)
            base_config = yaml.load(open(file, 'rb').read())
            config = merge(config, base_config)
    elif isinstance(config.get('$extends'), str):
        file = os.path.join(cwd, config.get('$extends'))
        base_config = yaml.load(open(file, 'rb').read())
        config = merge(config, base_config)
    return config


class ConfigGenerator(Macro):
    """A macro that's able to configure any TMOS based device. The actual
    configuration is composed off snippets from the config file.
    
    @param options: an Options instance
    @type options: Options
    """
    def __init__(self, options, address=None, *args, **kwargs):
        self.options = Options(options.__dict__)
        
        if not self.options.get('config'):
            provider = get_provider(__package__)
            manager = ResourceManager()
            config_path = provider.get_resource_filename(manager, '')
            config_file = os.path.join(config_path, 'configs', DEFAULT_CONFIG)
            self.options.config = config_file
        self.options.setdefault('nodes', DEFAULT_NODES)
        self.options.setdefault('node_offset', DEFAULT_NODE_OFFSET)
        self.options.setdefault('pools', DEFAULT_POOLS)
        self.options.setdefault('pool_members', DEFAULT_MEMBERS)
        self.options.setdefault('vips', DEFAULT_VIPS)
        self.options.setdefault('partitions', DEFAULT_PARTITIONS)
        self.options.setdefault('password', DEFAULT_ROOT_PASSWORD)
        self.options.setdefault('timeout', DEFAULT_TIMEOUT)
        self.options.setdefault('rootca_path', DEFAULT_ROOTCA_PATH)
        
        cwd = os.path.dirname(os.path.realpath(self.options.config))
        config = yaml.load(file(self.options.config, 'rb').read())
        extend(cwd, config)
        
        if self.options.device:
            device = ConfigInterface().get_device(options.device)
            self.address = device.hostname
        else:
            self.address = address

        if self.options.peer_device:
            peer_device = ConfigInterface().get_device(options.peer_device)
            self.options['peer'] = peer_device.address
            self.options['peerpassword'] = peer_device.get_root_creds().password

        self.config = config
        self.ssh = None
        self.ip_base_int = (0, 0)
        self.ip_base_ext = (0, 0)
        self._peer = {}
        self._hostname = None
        self._platform = None
        self._product = None
        self._version = None
        self._project = None
        self._status = None
        self._modules = {}
        self._features = {}

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

        self.formatter = {}
        self.formatter['VERSION'] = __version__
        super(ConfigGenerator, self).__init__(*args, **kwargs)

    def _find_subgraphs(self, filter_out = [], filter_in = []):
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
        status = SSH.get_prompt(ifc=self.ssh)
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
            subgraphs = self._find_subgraphs([ PREFIX_PARTITION, PREFIX_USER ])
            # Balance by "weight" all subgraphs
            self._link_roots(self._partitions, subgraphs)

            subgraphs = self._find_subgraphs(filter_in = [ PREFIX_USER ])
            self._link_roots([self._partitions[0]], subgraphs)

        else:
            subgraphs = self._find_subgraphs([ PREFIX_PARTITION ])
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
                            password=apikey) as irack:
            params = dict(address_set__address__in=mgmtip)
            # Locate the static bag for the F5Asset with mgmtip
            ret = irack.api.staticbag.filter(asset__type=1, **params)
            
            if ret['meta']['total_count'] == 0:
                raise ConfigGeneratorError("No devices with mgmtip=%s found in iRack." % mgmtip)
            if ret['meta']['total_count'] > 1:
                raise ConfigGeneratorError("More than one device with mgmtip=%s found in iRack." % mgmtip)
            
            bag = ret['objects'][0]
            bagid = bag['id']

            # Get the hostname
            ret = irack.api.staticsystem.filter(bag=bagid)
            assert ret['meta']['total_count'] == 1, "No StaticSystem entries for bagid=%s" % bagid
            hostname = ret['objects'][0]['hostname']
            data['hostname'] = hostname

            # Get all reg_keys
            ret = irack.api.staticlicense.filter(bag=bagid)
            assert ret['meta']['total_count'] >= 1, "No StaticLicense entries for bagid=%s" % bagid
            data['licenses'] = {}
            data['licenses']['reg_key'] = [x['reg_key'] for x in ret['objects']]

            # Get all VLAN -> self IPs pairs
            ret = irack.api.staticaddress.filter(bag=bagid, type=1)
            assert ret['meta']['total_count'] >= 1, "No StaticAddress entries for bagid=%s" % bagid
            data['selfip'] = {}
            for o in ret['objects']:
                vlan = o['vlan'].split('/')[-1]
                data['selfip'][vlan] = dict(address=o['address'], 
                                            netmask=o['netmask'])

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
                            self.irack_provider(address=self.options['irack_address'],
                                                username=self.options['irack_username'],
                                                apikey=self.options['irack_apikey'],
                                                mgmtip=mgmtip)
            )
            LOG.info("iRack query was successful.")

    def prepare(self):
        assert self.options['pool_members'] <= self.options['nodes'], \
               "Pool members > Nodes. Please add more nodes!"
        passwd = self.options['password']
        fqdn, _, ip_list = socket.gethostbyname_ex(self.address)
        ip = ip_list[0]
        ltm_label = ip.split('.')[3]
        
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
            if self.config.get('static') and self.config['static'][ip].get('hostname'):
                self._hostname = self.config['static'][ip]['hostname']
            else:
                self._hostname = 'device%s-%s.test.net' % (ip.split('.')[2], 
                                                           ip.split('.')[3])
        LOG.info('Using hostname: %s', self._hostname)
        
        self.prov = []
        if self.options.get('provision'):
            for prov in self.options['provision'].split(','):
                if prov:
                    bits = prov.split(':', 1)
                    if len(bits) > 1:
                        module, level = bits
                        assert level in ('minimum', 'nominal', 'maximum')
                    else:
                        module = bits[0]
                        level = 'minimum'
                    self.prov.append((module, level))

        if self.options.get('peer'):
            _, _, ip_list = socket.gethostbyname_ex(self.options['peer'])
            peer_ip = ip_list[0]
            peer_ltm_label = peer_ip.split('.')[3]
            peer_passwd = self.options['peerpassword']
    
            # Lookup static values for peer in iRack (if enabled).
            self.try_irack(peer_ip)
            
            p = self._peer
            peer_ssh = SSHInterface(address=peer_ip, password=peer_passwd, 
                               timeout=self.options['timeout'])
            peer_ssh.open()

            ret = BIGPIPE.generic('mgmt list', ifc=peer_ssh)
            
            bits = ret.stdout.split()
            p['ip'] = bits[1]

            if self.options.get('peerbase'):
                p['base_int'] = divmod(int(self.options['peerbase']), 256) 
            else:
                try:
                    tmp = self.config['static'][peer_ip]['selfip']['internal']['address'].split('.')
                    p['base_int'] = (int(tmp[2]), int(tmp[3]))
                except KeyError:
                    raise ValueError("Couldn't find a static entry for '%s'! "
                        "--selfip-internal and --selfip-external must be specified "
                        "or device must be discovered by iRack." % peer_ip)
    
            if self.options.get('unitid'):
                p['unit'] = self.options['unitid']
            else:
                ret = BIGPIPE.generic('db Failover.UnitId', ifc=peer_ssh)
                peer_ssh.close()
                p['unit'] = int(ret.stdout.strip().split('=')[1]) % 2 + 1

            # The device having UnitID=1 will always try to be the Active one.
            if p['unit'] == 1:
                self.formatter['ltm.id'] = int(peer_ltm_label)
                self.formatter['failover.active'] = 'force active enable'
            else:
                self.formatter['ltm.id'] = int(ltm_label)
                self.formatter['failover.active'] = 'force standby enable'
        else:
            self.formatter['ltm.id'] = int(ltm_label)
        
        if self.options.get('mgmtip'):
            self.formatter['ltm.ip'] = self.options['mgmtip']
        else:
            self.formatter['ltm.ip'] = ip

        if (self.options.get('selfip_internal') and 
            self.options.get('selfip_external')):

            tmp = self.options['selfip_internal'].split('.')
            self.ip_base_int = (int(tmp[2]), int(tmp[3]))
            self.formatter['INTERNAL.A'] = int(tmp[0])
            self.formatter['INTERNAL.B'] = int(tmp[1])
            tmp = self.options['selfip_external'].split('.')
            self.ip_base_ext = (int(tmp[2]), int(tmp[3]))
            self.formatter['EXTERNAL.A'] = int(tmp[0])
            self.formatter['EXTERNAL.B'] = int(tmp[1])
            LOG.info('Internal selfIP: %s', self.options['selfip_internal'])
            LOG.info('External selfIP: %s', self.options['selfip_external'])
        else:
            try:
                tmp = self.config['static'][ip]['selfip']['internal']['address'].split('.')
                self.ip_base_int = (int(tmp[2]), int(tmp[3]))
                self.formatter['INTERNAL.A'] = int(tmp[0])
                self.formatter['INTERNAL.B'] = int(tmp[1])
                tmp = self.config['static'][ip]['selfip']['external']['address'].split('.')
                self.ip_base_ext = (int(tmp[2]), int(tmp[3]))
                self.formatter['EXTERNAL.A'] = int(tmp[0])
                self.formatter['EXTERNAL.B'] = int(tmp[1])
                LOG.info('Internal selfIP: %s', self.config['static'][ip]['selfip']['internal']['address'])
                LOG.info('External selfIP: %s', self.config['static'][ip]['selfip']['external']['address'])
            except KeyError:
                raise ValueError("Couldn't find a static entry for '%s'! "
                    "--selfip-internal and --selfip-external must be specified" % ip)

        self.ssh = SSHInterface(address=self.address, password=passwd, 
                               timeout=self.options['timeout'])
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
        if (self._product.is_em and self._version >= 'em 3.0.0' and 
            self._project == 'solstice-em') \
        or (self._product.is_bigip and self._version >= 'bigip 11.0.0'):
            self.can_tmsh = True
            self.can_folders = True
            #raise NotImplementedError('eh...')
        
        # XXX: Temporary workaround before the solstice merges into EM3.0
        #if (self._product.is_em and self._version < 'em 3.0.1'):
        #    self.can_folders = False

        if self._platform in ['A100', 'A101', 'A107', 'A111']:
            self.can_cluster = True

    def pick_configuration(self):
        includes = self.config.get('includes')
        
        if not includes:
            return

        base_dir = os.path.dirname(self.options['config'])
        
        if self.can_tmsh:
            tmsh_config_filename = os.path.join(base_dir, includes.get('tmsh'))
            if not tmsh_config_filename:
                LOG.warning('TMSH target but no TMSH specific configuration '
                            'given. Will use the default one.')
            else:
                config = yaml.load(file(tmsh_config_filename, 'rb').read())
                self.config.update(config)
                LOG.info('Picked configuration: %s' % tmsh_config_filename)
        else:
            default_config_filename = os.path.join(base_dir, 
                                                   includes.get('default'))
            if default_config_filename:
                LOG.info('Using default configuration: %s' % default_config_filename)
                config = yaml.load(file(default_config_filename, 'rb').read())
                self.config.update(config)

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
        base = self.config['provision']['keys base']
        extra = self.config['provision']['keys extra']
        tmpl = self.config['provision']['template']
        product = str(self._product)
        m2l = self.config['provision']['module to license']
        formatter = self.formatter

        licensed_modules = self._modules

        for key, value in base.get(product, {}).items():
            if not licensed_modules.get(m2l[key]):
                LOG.warning('%s not licensed on this target' % m2l[key])
                #continue
            formatter['provision.key'] = key
            formatter['provision.level'] = value
            self.f_base.write(tmpl % formatter)

        if self.prov:
            for module, level in self.prov:
                formatter['provision.key'] = module
                formatter['provision.level'] = level
                self.f_base.write(tmpl % formatter)
        else:
            for item in extra.get(product, []):
                module = item.keys()[0]
                level = item.values()[0]
                if not licensed_modules.get(m2l[module]):
                    LOG.debug('%s not licensed on this target' % m2l[module])
                    continue
                formatter['provision.key'] = module
                formatter['provision.level'] = level
                self.f_base.write(tmpl % formatter)
                break
        
    def print_mgmt(self):
        tmpl = self.config['mgmt']
        formatter = self.formatter
        if self.can_tmsh:
            ret = self.call('tmsh list sys management-ip')
            bits = ret.stdout.split()
            if len(bits) < 2:
                ret = self.call('grep "^sys management-ip" /config/bigip_base.conf')
                bits = ret.stdout.split()
        else:
            ret = self.call('b mgmt list')
            bits = ret.stdout.split()
        
        if not ret or ret.stdout.strip() == 'No Management IP Addresses were found.':
            LOG.warning(ret)
            return
        
        if self.can_tmsh:
            ip, netmask = bits[2].split('/')
        else:
            ip = bits[1]
            netmask = bits[4]
        
        if self.can_tmsh:
            try:
                ret = self.call('tmsh list sys management-route default gateway')
                bits = ret.stdout.split()
            except:
                ret = self.call(' grep -A2 "^sys management-route" /config/bigip_base.conf')
                bits = ret.stdout.split()
            gw = bits[5]
        else:
            ret = self.call('b mgmt route list')
            bits = ret.stdout.split()
            gw = bits[6]
        
        if not ret or ret.stdout.strip() == 'No Management Routes were found.':
            gw = ''

        formatter['ltm.ip'] = ip
        formatter['ltm.netmask'] = netmask
        formatter['ltm.gateway'] = gw

        self.f_base.write(tmpl % formatter)

    def print_vlan(self):
        root = self.config['vlan']
        formatter = self.formatter

        if self.can_cluster:
            tmpl = root['cluster']
        elif self._platform in ['D84']:
            tmpl = root['D84']
        elif self._platform in ['D100', 'D41']:
            tmpl = root['wanjet']
        elif self._platform in ['SKI23']:
            tmpl = root['SKI23']
        else:
            tmpl = root['common']

        self.f_base.write(tmpl % formatter)

    def print_self(self):
        tmpl = self.config['self']
        formatter = self.formatter
        formatter['self.ip_base_int.C'] = self.ip_base_int[0] 
        formatter['self.ip_base_int.D'] = self.ip_base_int[1]
        formatter['self.ip_base_ext.C'] = self.ip_base_ext[0] 
        formatter['self.ip_base_ext.D'] = self.ip_base_ext[1]

        self.f_base.write(tmpl % formatter)

    def print_simple(self, section, dest = 'base', can_print = True):
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
        formatter = self.formatter

        p = self._peer
        formatter['self.ip_base.C'] = self.ip_base_int[0]
        formatter['self.ip_base.D'] = self.ip_base_int[1]
        formatter['peer.ip_base_int.C'] = p['base_int'][0]
        formatter['peer.ip_base_int.D'] = p['base_int'][1]
        formatter['self.unit'] = p['unit']
        formatter['peer.ip'] = p['ip']
        LOG.debug('self.unit = %d', p['unit'])

        if self.can_scf:
            self.f_base.write(tmpl % formatter)
            if self.can_net_failover:
                self.f_base.write(tmpl_nf % formatter)
        else:
            LOG.info('HA not supported on this target')

    def print_system(self):
        root = self.config['system']
        tmpl = root['template']
        formatter = self.formatter
        formatter['gui.setup'] = root['gui setup']
        formatter['system.hostname'] = self._hostname

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
        nodes = self.options['nodes']
        tmpl = self.config['node template'][0]
        node_offset = self.options['node_offset']
        LOG.info('Node offset is: %d (%d.%d)', node_offset,
                 *divmod(node_offset, 256))

        self._nodes = Nodes(3, PREFIX_NODE)
        for i in range(nodes):
            context = {}
            n = self._nodes[i]
            context['node.index'] = i + 1
            context['node.C'], context['node.D'] = \
                divmod(i + node_offset, 256)
            n.data = tmpl
            n.context = context
            self.g.add_node(n)

    def prepare_pool(self):
        if not self.can_pool:
            LOG.debug('Pools not supported on this target')
            return

        nodes = self.options['nodes']
        pools = self.options['pools']
        nodes_per_pool = self.options['pool_members']
        tmpl = self.config['pool template'][0]
        pm_tmpl = self.config['pool member template']
        pm_prots = self.config['pool member protocols']
        pm_prots_count = len(pm_prots)
        local_context = {}
        node_offset = self.options['node_offset']

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

            for _ in range(nodes_per_pool):
                pm_context = {}
                pm_context['node.C'], pm_context['node.D'] = \
                    divmod(j % nodes + node_offset, 256)
                pm_context['pool.proto'] = pm_prots[ j % pm_prots_count ]
                pm_context['pool.monitor'] = pm_context['pool.proto']
                #self.formatter.update(context)
                context['pool.members'] += pm_tmpl % pm_context
                #print pm_tmpl % self.formatter
                j += 1

            n.data = tmpl
            n.context = context
            self.g.add_node(n)

    def prepare_virtual(self):
        if not self.can_virtual:
            LOG.debug('VIPs not supported on this target')
            return

        pools = self.options['pools']
        vips = self.options['vips']
        tmpls = self.config['vip template']
        tmpl_count = len(tmpls)
        vip_offset = self.options.get('vip_offset')
        if not vip_offset:
            vip_offset = 1 + 60 * (self.formatter['ltm.id'] - 1)
        LOG.info('VIP offset is: %d (%d.%d)', vip_offset,
                 *divmod(vip_offset, 256))

        self._vips = Nodes(5, PREFIX_VIP)
        for i in range(vips):
            n = self._vips[i]
            context = {}
            context['pool.index'] = i % pools + 1
            context['vip.index'] = i + 1
            context['vip.C'], context['vip.D'] = \
                divmod(i + vip_offset, 256)
            n.data = tmpls[ i % tmpl_count ]
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
        
        for types in profiles:
            min_ver = Version(profiles[types].get('min version', MIN_VER), 
                              Product.BIGIP)
            max_ver = Version(profiles[types].get('max version', MAX_VER), 
                              Product.BIGIP)
            req_mod = profiles[types].get('require module', None)
            req_feat = profiles[types].get('require feature', None)
            
            # XXX
            #if types == 'iiop':
            #    print licensed_modules, licensed_features
            # END

            if (self._version >= min_ver and
                self._version <= max_ver and
                (req_mod is None or licensed_modules.get(req_mod)) and
                (req_feat is None or licensed_features.get(req_feat))
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
            root = self.config['legacy users']
            if root.get('admin'):
                self.call('f5passwd admin %s' % root['admin'])

            if root.get('root'):
                self.call('f5passwd root %s' % root['root'])

        else:
            root = self.config['default users']
            self.prepare_user()

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
        sp = self.ssh.api

        ip = self.formatter['ltm.ip']
        try:
            license = self.options.get('license') or \
                            self.config['static'][ip]['licenses']['reg_key'][0]
        except:
            license = None
        
        if self._status in ['NO LICENSE'] and not license:
            raise Exception('The box needs to be relicensed first.'
                            'Provide --license <regkey>')

        if license and \
        self._status in ['LICENSE INOPERATIVE', 'NO LICENSE']:
            LOG.info('Licensing...')
            self.call('SOAPLicenseClient --verbose --basekey %s' % license)
            # We need to re-set the modules based on the new license 
            self._set_modules()
            # Tomcat doesn't like the initial licensing through CLI
            if self._product.is_em:
                ret = sp.call('bigstart restart tomcat')

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
        options.admin_username = ADMIN_USERNAME
        options.root_username = ROOT_USERNAME
        options.store = ROOTCA_STORE
        
        if self.options.get('dry_run'):
            LOG.info('Would push key/cert pair')
            return
        
        if not self.options.get('rootca_path'):
            LOG.warning('rootca-path parameter not specified. Skiping key/cert '
                        'update')
            return
        
        LOG.info('Pushing the key/certificate pair')
        
        root = self.config['legacy users']
        if root.get('admin') and root.get('root'):
            options.admin_password = root['admin']
            options.root_password = root['root']
        else:
            LOG.error("admin & root passwords are not present. Skipping "
                      "key/cert update")

        cs = WebCert(options, address=self.address)
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
        LOG.info('Waiting for reconfiguration...')
        SCMD.ssh.FileExists('/var/run/mprov.pid', ifc=self.ssh).run_wait(lambda x:x is False,
                                             progress_cb=lambda x:'mprov still running...',
                                             timeout=180)
#        SCMD.ssh.FileExists('/var/run/grub.conf.lock', ifc=self.ssh).run_wait(lambda x:x is False,
#                                             progress_cb=lambda x:'grub.lock still running...',
#                                             timeout=60)
        if self.can_provision and self._is_asm and self._is_lvm:
            SCMD.ssh.FileExists('/var/lib/mysql/.moved.to.asmdbvol', 
                                ifc=self.ssh).run_wait(lambda x:x,
                                                 progress_cb=lambda x:'ASWADB still not there...',
                                                 timeout=120)
        # Wait for ASM config server to come up.
        if self.can_provision and self._is_asm:
            LOG.info('Waiting for ASM config server to come up...')
            SCMD.ssh.Generic(r'netstat -anp|grep -c "9781.*0\.0\.0\.0:\*.*/perl"', 
                            ifc=self.ssh).run_wait(lambda x:int(x.stdout),
                                                   progress_cb=lambda x:'ASM cfg server not up...',
                                                   timeout=120)

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
            fd, self.f_base_name = tempfile.mkstemp(prefix = 'confgen-',
                                                        text = True)
            self.f_common = self.f_base = os.fdopen(fd, "w")
            LOG.debug('temp filename: %s', self.f_base_name)
        else:
            fd, self.f_base_name = tempfile.mkstemp(prefix = 'confgenb-',
                                                        text = True)
            self.f_base = os.fdopen(fd, "w")
            LOG.debug('base temp filename: %s', self.f_base_name)

            fd, self.f_common_name = tempfile.mkstemp(prefix = 'confgenc-',
                                                        text = True)
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
            if self.can_folders:
                #self.call('bigstart restart devmgmtd')
                self.call('tmsh delete cm trust-domain all')

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

        formatter = optparse.TitledHelpFormatter(max_help_position = 30)
        p = OptionParser(
                usage = usage,
                formatter = formatter,
                version = "LTM config generator %s" % __version__,
        )

        provider = get_provider(__package__)
        manager = ResourceManager()
        config_path = provider.get_resource_filename(manager, '')
        config_file = os.path.join(config_path, 'configs', DEFAULT_CONFIG)

        p.add_option("-c", "--config", metavar="FILE",
                     default=config_file, type="string",
                     help="The templates config. (default: %s)" % DEFAULT_CONFIG)

        p.add_option("", "--partitions", metavar="NUMBER",
                     default=DEFAULT_PARTITIONS, type="int",
                     help="How many partitions. (default: %d)" % DEFAULT_PARTITIONS)
        p.add_option("-n", "--nodes", metavar="NUMBER",
                     default=DEFAULT_NODES, type="int",
                     help="How many nodes. (default: %d)" % DEFAULT_NODES)
        p.add_option("", "--node-offset", metavar="NUMBER",
                     default=DEFAULT_NODE_OFFSET, type="int",
                     help="The start value for nodes. (default: %d)" % DEFAULT_NODE_OFFSET)
        p.add_option("-o", "--pools", metavar="NUMBER",
                     default=DEFAULT_POOLS, type="int",
                     help="How many pools. (default: %d)" % DEFAULT_POOLS)
        p.add_option("", "--pool-members", metavar="NUMBER",
                     default=DEFAULT_MEMBERS, type="int",
                     help="How many pool members per pool. (default: %d)" % DEFAULT_MEMBERS)
        p.add_option("-v", "--vips", metavar="NUMBER",
                     default=DEFAULT_VIPS, type="int",
                     help="How many Virtual IPs. (default: %d)" % DEFAULT_VIPS)
        p.add_option("", "--vip-offset", metavar="NUMBER",
                     type="int",
                     help="The start value for VIPs. "
                     "Default is: 1 + (60 * <ltm_numer> - 1)")
        p.add_option("-p", "--password", metavar="STRING",
                     type="string", default=DEFAULT_ROOT_PASSWORD,
                     help="SSH root Password. (default: %s)" % DEFAULT_ROOT_PASSWORD)
        p.add_option("", "--base", metavar="X",
                     type="int",
                     help="Set the VLANs and Self IPs to 10.[10,11].0.X style")

        p.add_option("", "--peer", metavar="HOST",
                     type="string",
                     help="Make an HA pair with this device")
        p.add_option("", "--peerbase", metavar="X",
                     type="string",
                     help="Peer's base number")
        p.add_option("", "--peerpassword", metavar="STRING",
                     type="string", default=DEFAULT_ROOT_PASSWORD,
                     help="Peer's SSH root password. (default: %s)" % DEFAULT_ROOT_PASSWORD)

        p.add_option("", "--hostname", metavar="HOSTNAME",
                     type="string",
                     help="The device hostname")
        p.add_option("", "--mgmtip", metavar="IP",
                     type="string",
                     help="The device management address (if different from --ltm)")
        p.add_option("", "--selfip-internal", metavar="IP",
                     type="string",
                     help="Self IP address for internal vlan.")
        p.add_option("", "--selfip-external", metavar="IP",
                     type="string",
                     help="Self IP address for external vlan.")
        p.add_option("", "--provision", metavar="MODULE:[LEVEL],[MODULE:LEVEL]",
                     type="string",
                     help="Provision module list")
        p.add_option("", "--license", metavar="REGKEY",
                     type="string",
                     help="Set the license")
        p.add_option("", "--clean",
                     action="store_true",
                     help="Clean vips, pools, nodes on the target")
        p.add_option("-r", "--rootca-path",
                     type="string", default=DEFAULT_ROOTCA_PATH,
                     help="Specify the directory where ROOT CA files are. (default: %s)" % DEFAULT_ROOTCA_PATH)

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
    logging.basicConfig(level = level)
    
    if not args:
        p.print_version()
        p.print_help()
        sys.exit(2)

    cg = ConfigGenerator(options, address=args[0])
    cg.run()

if __name__ == '__main__':
    main()
