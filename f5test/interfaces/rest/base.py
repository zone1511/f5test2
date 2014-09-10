from ...base import AttrDict
from collections import OrderedDict
import json
import xmltodict
import os


class BaseApiObject(AttrDict):

    def from_file(self, directory, name=None, fmt='json'):
        if name is None:
            name = "%s.%s" % (self.get('name', 'default'), fmt)

        if fmt is 'json':
            with file(os.path.join(directory, name)) as f:
                self.update(json.load(f))
        elif fmt is 'xml':
            with file(os.path.join(directory, name)) as f:
                self.update(xmltodict.parse(f))
        else:
            raise NotImplementedError('Unknown format: %s' % fmt)

        return self

    def update(self, *args, **kwargs):
        """
        The update for this type of objects is a little different.
        It expects the object to already have all known attributes predefined,
        then when the current instance is updated the original attribute types
        will be preserved.

        Example:

        class SomeObject(BaseApiObject):
            def __init__(self, *args, **kwargs):
                super(SomeObject, self).__init__(*args, **kwargs)
                self.setdefault('name', '')
                self.setdefault('aReference', Reference())
                self.setdefault('aReferenceList', ReferenceList())

        o = SomeObject()
        o.update({'name': 'foo', 'aReference': {'link': '/some/url'}})

        type(o.aReference) == Reference

        """
        def combine(d, n):

            for k, v in n.items():
                t = type(d[k]) if k in d and d[k] is not None else type(v)
                if t is type(None):
                    t = lambda x: x
                d.setdefault(k, AttrDict())

                if t in (dict, OrderedDict):
                    if not isinstance(d[k], dict):
                        d[k] = AttrDict()
                    combine(d[k], v)
                elif t is list:
                    d[k] = t(v)
                    for i, item in enumerate(v):
                        if isinstance(item, dict):
                            d[k][i] = AttrDict(item)
                else:
                    d[k] = t(v)

        for arg in args:
            if hasattr(arg, 'items'):
                combine(self, arg)
        combine(self, kwargs)
