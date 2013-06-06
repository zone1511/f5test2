'''
Created on Apr 12, 2013

@author: jono
'''
import copy
import cStringIO
import logging
import itertools
from ...utils.parsers import tmsh

PARTITION_COMMON = 'Common'
LOG = logging.getLogger(__name__)


def make_partitions(name='Partition{0}', count=0, context=None):
    root = Folder(context=context)
    root.add(PARTITION_COMMON)
    for i in range(1, count + 1):
        root.add(name.format(i))
    return root


def enumerate_stamps(folder, klass, pred=None, include_common=True, cycle=True):
    if not callable(pred):
        pred = lambda x: True

    iterators = []
    if include_common:
        root = folder.partition().parent or folder
        common = root[PARTITION_COMMON]
        iterators.append(common.enumerate())

    iterators.append(folder.enumerate())
    chain = itertools.chain(*iterators)
    if cycle:
        chain = itertools.cycle(chain)
    for folder in chain:
        for stamp in folder.content_map.get(klass, []):
            if pred(stamp):
                yield stamp


class Folder(dict):
    SEPARATOR = '/'

    def __init__(self, name='', context=None):
        self.name = name
        self.index = 0
        self.parent = None
        self.content = []
        self.content_map = {}
        self.context = context

    def __repr__(self):
        dictrepr = dict.__repr__(self)
        return '%s(%s %d)' % (type(self).__name__, dictrepr, self.index)

    def key(self):
        bits = []
        node = self
        while node.parent:
            bits.append(node.name)
            node = node.parent
        bits.append(node.name)
        return Folder.SEPARATOR.join(reversed(bits))

    def is_root(self):
        return self.parent is None

    def add(self, name):
        node = Folder(name)
        node.parent = self
        node.context = self.context
        node.index = len(self)
        self[name] = node
        if self.is_root():
            node.hook(Partition())
        else:
            node.hook(FolderStamp())
        return node

    def hook(self, *args):
        for stamp in args:
            stamp.folder = self
            self.content.append(stamp)
            type_pool = self.content_map.setdefault(type(stamp), [])
            type_pool.append(stamp)

    def root(self):
        partition = self.partition()
        if partition.parent:
            return partition.parent
        return partition

    def partition(self):
        this = self
        while this.parent:
            if this.parent.parent is None:
                break
            this = this.parent
        return this

    def enumerate(self, recursive=True):
        if self.parent:
            yield self
        if self.values():
            for x in self.values():
                if recursive:
                    for y in x.enumerate(recursive):
                        yield y
                else:
                    yield x

    def render(self, recursive=True, stream=None, func=None):
        if stream is None:
            stream = cStringIO.StringIO()
        if func is None:
            func = lambda x: True

        for folder in self.enumerate(recursive):
            for stamp in folder.content:
                if not stamp.built_in and func(stamp):
                    pair = stamp.compile()
                    if pair and pair[1]:
                        stream.write(tmsh.dumps(pair[1]))
        return stream


class Stamp(object):
    built_in = False
    cache = {}

    def __init__(self):
        self.folder = None
        self._key = None
        self._value = None
        self._compiled = False

    def template(self, name):
        klass = type(self)
        key = "_%s_%s" % (klass.__name__, name)
        template = Stamp.cache.get(key)
        if template is None:
            template_text = getattr(klass, name, '')
            template = tmsh.parser(template_text)
            Stamp.cache[key] = template
        return template

    def from_template(self, name):
        return copy.deepcopy(self.template(name))

    def compile(self):
        v = self.folder.context.version
        if (v.product.is_bigip and v >= 'bigip 11.0.0' or
            v.product.is_em and v >= 'em 2.0.0' or
            v.product.is_bigiq):
            obj = self.from_template('TMSH')
            return self.tmsh(obj)
        else:
            obj = self.from_template('BIGPIPE')
            return self.bigpipe(obj)

    def tmsh(self, obj):
        return None, None

    def bigpipe(self, obj):
        return None, None

    def set(self, key, value):
        self._key = key
        self._value = value
        self._compiled = True

    def get(self, reference=False):
        if not self._compiled:
            key, obj = self.compile()
            self.set(key, obj)
        if reference:
            return self._key
        return self._value


class Partition(Stamp):
    TMSH = """
        auth partition %(name)s {
            description "This is partition coke"
        }
        sys folder %(key)s {
#            device-group none
            inherited-devicegroup true
            inherited-traffic-group true
            traffic-group /Common/traffic-group-1
        }
        cli admin-partitions {
            update-partition %(name)s
        }
    """
    BIGPIPE = """
        partition %(name)s {
            description "This is partition number %(partition.index)d"
        }
        shell write partition %(name)s
    """

    def __init__(self, description=None):
        self.description = description or "This is partition {0}"
        super(Partition, self).__init__()

    def compile(self):
        v = self.folder.context.version
        name = self.folder.partition().name
        index = self.folder.partition().index
        if (v.product.is_bigip and v >= 'bigip 11.0.0' or
            v.product.is_em or v.product.is_bigiq):
            obj = self.from_template('TMSH')
            value = obj.rename_key('auth partition %(name)s', name=name)
            value['description'] = self.description.format(index)
            key = self.folder.key()
            obj.rename_key('sys folder %(key)s', key=key)
            value = obj['cli admin-partitions']
            value['update-partition'] = name
        else:
            obj = self.from_template('BIGPIPE')
            value = obj.rename_key('partition %(name)s', name=name)
            value['description'] = self.description.format(index)
            value = obj.rename_key('shell write partition %(name)s', name=name)
        return name, obj


class FolderStamp(Stamp):
    TMSH = """
        sys folder %(key)s {
#            device-group none
            inherited-devicegroup true
            inherited-traffic-group true
            traffic-group /Common/traffic-group-1
        }
    """

    def __init__(self):
        #self.location = location
        super(FolderStamp, self).__init__()

    def compile(self):
        v = self.folder.context.version
        if (v.product.is_bigip and v >= 'bigip 11.0.0' or
            v.product.is_em or v.product.is_bigiq):
            key = self.folder.key()
            obj = self.from_template('TMSH')
            obj.rename_key('sys folder %(key)s', key=key)
        else:
            LOG.debug('Folders not supported')
            key = obj = None
        return key, obj


class Literal(Stamp):
    TMSH = ""
    BIGPIPE = ""

    def __init__(self):
        super(Literal, self).__init__()

    def tmsh(self, obj):
        return None, obj

    def bigpipe(self, obj):
        return None, obj


class Mirror(Stamp):

    def __init__(self, obj, key=None):
        self.obj = obj
        self.key = key
        super(Mirror, self).__init__()

    def compile(self):
        return self.key, self.obj
