'''
Created on May 27, 2011

@author: jono
'''
import copy
import types
from decimal import Decimal
import datetime
from urllib import urlencode, quote
try:
    # Python 2.6 and greater
    from urlparse import parse_qsl
except ImportError:
    # Python 2.5, 2.4.  Works on Python 2.6 but raises
    # PendingDeprecationWarning
    from cgi import parse_qsl


def smart_str(s, encoding='utf-8', strings_only=False, errors='strict'):
    """
    Returns a bytestring version of 's', encoded as specified in 'encoding'.

    If strings_only is True, don't convert (some) non-string-like objects.
    """
    if strings_only and isinstance(s, (types.NoneType, int)):
        return s
    if not isinstance(s, basestring):
        try:
            return str(s)
        except UnicodeEncodeError:
            if isinstance(s, Exception):
                # An Exception subclass containing non-ASCII data that doesn't
                # know how to print itself properly. We shouldn't raise a
                # further exception.
                return ' '.join([smart_str(arg, encoding, strings_only,
                        errors) for arg in s])
            return unicode(s).encode(encoding, errors)
    elif isinstance(s, unicode):
        return s.encode(encoding, errors)
    elif s and encoding != 'utf-8':
        return s.decode('utf-8', errors).encode(encoding, errors)
    else:
        return s


def is_protected_type(obj):
    """Determine if the object instance is of a protected type.

    Objects of protected types are preserved as-is when passed to
    force_unicode(strings_only=True).
    """
    return isinstance(obj, (
        types.NoneType,
        int, long,
        datetime.datetime, datetime.date, datetime.time,
        float, Decimal)
    )

def force_unicode(s, encoding='utf-8', strings_only=False, errors='strict'):
    """
    Similar to smart_unicode, except that lazy instances are resolved to
    strings, rather than kept as lazy objects.

    If strings_only is True, don't convert (some) non-string-like objects.
    """
    # Handle the common case first, saves 30-40% in performance when s
    # is an instance of unicode. This function gets called often in that
    # setting.
    if isinstance(s, unicode):
        return s
    if strings_only and is_protected_type(s):
        return s
    try:
        if not isinstance(s, basestring,):
            if hasattr(s, '__unicode__'):
                s = unicode(s)
            else:
                try:
                    s = unicode(str(s), encoding, errors)
                except UnicodeEncodeError:
                    if not isinstance(s, Exception):
                        raise
                    # If we get to here, the caller has passed in an Exception
                    # subclass populated with non-ASCII data without special
                    # handling to display as a string. We need to handle this
                    # without raising a further exception. We do an
                    # approximation to what the Exception's standard str()
                    # output should be.
                    s = ' '.join([force_unicode(arg, encoding, strings_only,
                            errors) for arg in s])
        elif not isinstance(s, unicode):
            # Note: We use .decode() here, instead of unicode(s, encoding,
            # errors), so that if s is a SafeString, it ends up being a
            # SafeUnicode at the end.
            s = s.decode(encoding, errors)
    except UnicodeDecodeError, e:
        if not isinstance(s, Exception):
            raise UnicodeDecodeError(s, *e.args)
        else:
            # If we get to here, the caller has passed in an Exception
            # subclass populated with non-ASCII bytestring data without a
            # working unicode method. Try to handle this without raising a
            # further exception by individually forcing the exception args
            # to unicode.
            s = ' '.join([force_unicode(arg, encoding, strings_only,
                    errors) for arg in s])
    return s

def str_to_unicode(s, encoding):
    """
    Converts basestring objects to unicode, using the given encoding. Illegally
    encoded input characters are replaced with Unicode "unknown" codepoint
    (\ufffd).

    Returns any non-basestring objects without change.
    """
    if isinstance(s, str):
        return unicode(s, encoding, 'replace')
    else:
        return s


class MultiValueDictKeyError(KeyError):
    pass


class MultiValueDict(dict):
    """
    A subclass of dictionary customized to handle multiple values for the
    same key.

    >>> d = MultiValueDict({'name': ['Adrian', 'Simon'], 'position': ['Developer']})
    >>> d['name']
    'Simon'
    >>> d.getlist('name')
    ['Adrian', 'Simon']
    >>> d.get('lastname', 'nonexistent')
    'nonexistent'
    >>> d.setlist('lastname', ['Holovaty', 'Willison'])

    This class exists to solve the irritating problem raised by cgi.parse_qs,
    which returns a list for every key, even though most Web forms submit
    single name-value pairs.
    """
    def __init__(self, key_to_list_mapping=()):
        super(MultiValueDict, self).__init__(key_to_list_mapping)

    def __repr__(self):
        return "<%s: %s>" % (self.__class__.__name__,
                             super(MultiValueDict, self).__repr__())

    def __getitem__(self, key):
        """
        Returns the last data value for this key, or [] if it's an empty list;
        raises KeyError if not found.
        """
        try:
            list_ = super(MultiValueDict, self).__getitem__(key)
        except KeyError:
            raise MultiValueDictKeyError("Key %r not found in %r" % (key, self))
        try:
            return list_[-1]
        except IndexError:
            return []

    def __setitem__(self, key, value):
        super(MultiValueDict, self).__setitem__(key, [value])

    def __copy__(self):
        return self.__class__([
            (k, v[:])
            for k, v in self.lists()
        ])

    def __deepcopy__(self, memo=None):
        if memo is None:
            memo = {}
        result = self.__class__()
        memo[id(self)] = result
        for key, value in dict.items(self):
            dict.__setitem__(result, copy.deepcopy(key, memo),
                             copy.deepcopy(value, memo))
        return result

    def __getstate__(self):
        obj_dict = self.__dict__.copy()
        obj_dict['_data'] = dict([(k, self.getlist(k)) for k in self])
        return obj_dict

    def __setstate__(self, obj_dict):
        data = obj_dict.pop('_data', {})
        for k, v in data.items():
            self.setlist(k, v)
        self.__dict__.update(obj_dict)

    def get(self, key, default=None):
        """
        Returns the last data value for the passed key. If key doesn't exist
        or value is an empty list, then default is returned.
        """
        try:
            val = self[key]
        except KeyError:
            return default
        if val == []:
            return default
        return val

    def getlist(self, key):
        """
        Returns the list of values for the passed key. If key doesn't exist,
        then an empty list is returned.
        """
        try:
            return super(MultiValueDict, self).__getitem__(key)
        except KeyError:
            return []

    def setlist(self, key, list_):
        super(MultiValueDict, self).__setitem__(key, list_)

    def setdefault(self, key, default=None):
        if key not in self:
            self[key] = default
        return self[key]

    def setlistdefault(self, key, default_list=()):
        if key not in self:
            self.setlist(key, default_list)
        return self.getlist(key)

    def appendlist(self, key, value):
        """Appends an item to the internal list associated with key."""
        self.setlistdefault(key, [])
        super(MultiValueDict, self).__setitem__(key, self.getlist(key) + [value])

    def items(self):
        """
        Returns a list of (key, value) pairs, where value is the last item in
        the list associated with the key.
        """
        return [(key, self[key]) for key in self.keys()]

    def iteritems(self):
        """
        Yields (key, value) pairs, where value is the last item in the list
        associated with the key.
        """
        for key in self.keys():
            yield (key, self[key])

    def lists(self):
        """Returns a list of (key, list) pairs."""
        return super(MultiValueDict, self).items()

    def iterlists(self):
        """Yields (key, list) pairs."""
        return super(MultiValueDict, self).iteritems()

    def values(self):
        """Returns a list of the last value on every key list."""
        return [self[key] for key in self.keys()]

    def itervalues(self):
        """Yield the last value on every key list."""
        for key in self.iterkeys():
            yield self[key]

    def copy(self):
        """Returns a shallow copy of this object."""
        return copy(self)

    def update(self, *args, **kwargs):
        """
        update() extends rather than replaces existing key lists.
        Also accepts keyword args.
        """
        if len(args) > 1:
            raise TypeError("update expected at most 1 arguments, got %d" % len(args))
        if args:
            other_dict = args[0]
            if isinstance(other_dict, MultiValueDict):
                for key, value_list in other_dict.lists():
                    self.setlistdefault(key, []).extend(value_list)
            else:
                try:
                    for key, value in other_dict.items():
                        self.setlistdefault(key, []).append(value)
                except TypeError:
                    raise ValueError("MultiValueDict.update() takes either a MultiValueDict or dictionary")
        for key, value in kwargs.iteritems():
            self.setlistdefault(key, []).append(value)


class QueryDict(MultiValueDict):
    """
    A specialized MultiValueDict that takes a query string when initialized.
    This is immutable unless you create a copy of it.

    Values retrieved from this class are converted from the given encoding
    (DEFAULT_CHARSET by default) to unicode.
    """
    # These are both reset in __init__, but is specified here at the class
    # level so that unpickling will have valid values
    _mutable = True
    _encoding = 'utf-8'

    def __init__(self, query_string, mutable=False, encoding='utf-8'):
        MultiValueDict.__init__(self)
        self.encoding = encoding
        for key, value in parse_qsl((query_string or ''), True): # keep_blank_values=True
            self.appendlist(force_unicode(key, encoding, errors='replace'),
                            force_unicode(value, encoding, errors='replace'))
        self._mutable = mutable

    def _get_encoding(self):
        return self._encoding

    def _set_encoding(self, value):
        self._encoding = value

    encoding = property(_get_encoding, _set_encoding)

    def _assert_mutable(self):
        if not self._mutable:
            raise AttributeError("This QueryDict instance is immutable")

    def __setitem__(self, key, value):
        self._assert_mutable()
        key = str_to_unicode(key, self.encoding)
        value = str_to_unicode(value, self.encoding)
        MultiValueDict.__setitem__(self, key, value)

    def __delitem__(self, key):
        self._assert_mutable()
        super(QueryDict, self).__delitem__(key)

    def __copy__(self):
        result = self.__class__('', mutable=True, encoding=self.encoding)
        for key, value in dict.items(self):
            dict.__setitem__(result, key, value)
        return result

    def __deepcopy__(self, memo):
        result = self.__class__('', mutable=True, encoding=self.encoding)
        memo[id(self)] = result
        for key, value in dict.items(self):
            dict.__setitem__(result, copy.deepcopy(key, memo), copy.deepcopy(value, memo))
        return result

    def setlist(self, key, list_):
        self._assert_mutable()
        key = str_to_unicode(key, self.encoding)
        list_ = [str_to_unicode(elt, self.encoding) for elt in list_]
        MultiValueDict.setlist(self, key, list_)

    def setlistdefault(self, key, default_list=()):
        self._assert_mutable()
        if key not in self:
            self.setlist(key, default_list)
        return MultiValueDict.getlist(self, key)

    def appendlist(self, key, value):
        self._assert_mutable()
        key = str_to_unicode(key, self.encoding)
        value = str_to_unicode(value, self.encoding)
        MultiValueDict.appendlist(self, key, value)

    def update(self, other_dict):
        self._assert_mutable()
        f = lambda s: str_to_unicode(s, self.encoding)
        if hasattr(other_dict, 'lists'):
            for key, valuelist in other_dict.lists():
                for value in valuelist:
                    MultiValueDict.update(self, {f(key): f(value)})
        else:
            d = dict([(f(k), f(v)) for k, v in other_dict.items()])
            MultiValueDict.update(self, d)

    def pop(self, key, *args):
        self._assert_mutable()
        return MultiValueDict.pop(self, key, *args)

    def popitem(self):
        self._assert_mutable()
        return MultiValueDict.popitem(self)

    def clear(self):
        self._assert_mutable()
        MultiValueDict.clear(self)

    def setdefault(self, key, default=None):
        self._assert_mutable()
        key = str_to_unicode(key, self.encoding)
        default = str_to_unicode(default, self.encoding)
        return MultiValueDict.setdefault(self, key, default)

    def copy(self):
        """Returns a mutable copy of this object."""
        return self.__deepcopy__({})

    def urlencode(self, safe=None):
        """
        Returns an encoded string of all query string arguments.

        :arg safe: Used to specify characters which do not require quoting, for
            example::

                >>> q = QueryDict('', mutable=True)
                >>> q['next'] = '/a&b/'
                >>> q.urlencode()
                'next=%2Fa%26b%2F'
                >>> q.urlencode(safe='/')
                'next=/a%26b/'

        """
        output = []
        if safe:
            encode = lambda k, v: '%s=%s' % ((quote(k, safe), quote(v, safe)))
        else:
            encode = lambda k, v: urlencode({k: v})
        for k, list_ in self.lists():
            k = smart_str(k, self.encoding)
            output.extend([encode(k, smart_str(v, self.encoding))
                           for v in list_])
        return '&'.join(output)
