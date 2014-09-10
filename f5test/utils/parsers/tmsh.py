'''
Created on Apr 03, 2013

Tested on tmsh scf output (or bigip.conf content) starting with 11.0.0.
Bigpipe format are partially supported. See caveats below.

Caveats:
- tmsh one-line output is not supported by the parser
- Comments are not supported by the encoder
- Constructs like following are not supported by the parser:
    order-by {
        {
            measure events_count
            sort-type desc
        }
    }
- Constructs like this are not parsed correctly (workaround: concatenate lines)
   key {
       options
          dont insert empty fragments
       profiles
          clientssl
              clientside

   }

@author: jono
'''
from pyparsing import (Literal, Word, Group, ZeroOrMore, printables, OneOrMore,
    Forward, Optional, removeQuotes, Suppress, QuotedString, ParserElement,
    White, LineEnd, quotedString, delimitedList, nestedExpr, originalTextFor,
    pythonStyleComment, Combine, FollowedBy)
import re
import json
import collections
from fnmatch import fnmatch
from ..decorators import synchronized_with
from . import PYPARSING_LOCK
#from f5test.utils.decorators import synchronized_with
#from f5test.utils.parsers import PYPARSING_LOCK

# This is to support legacy bigpipe output and it should remain disabled.
OLD_STYLE_KEYS = False


class RawString(unicode):
    pass


class RawDict(dict):
    pass


class RawEOL(object):
    class Meta(type):
        def __repr__(self):
            return '<EOL>'
    __metaclass__ = Meta


class GlobDict(collections.OrderedDict):

    def __setitem__(self, key, value):
        super(GlobDict, self).__setitem__(RawString(key), value)

    def rename_key(self, old, **kwargs):
        """Not optimum, but it should work fine for small dictionaries"""
        value = self[old]
        items = [(k % kwargs, v) if k == old else (k, v) for k, v in self.iteritems()]
        self.clear()
        self.update(items)
        return value

    def glob(self, match):
        """@match should be a glob style pattern match (e.g. '*.txt')"""
        return dict([(k, v) for k, v  in self.items() if fnmatch(k, match)])

    def glob_keys(self, match):
        return [k.split(' ')[-1] for k  in self.keys() if fnmatch(k, match)]


@synchronized_with(PYPARSING_LOCK)
def parser(text):
    cvtTuple = lambda toks: tuple(toks.asList())
    cvtRaw = lambda toks: RawString(' '.join(map(str, toks.asList())))
    #cvtDict = lambda toks: dict(toks.asList())
    cvtGlobDict = lambda toks: GlobDict(toks.asList())
    cvtDict = cvtGlobDict
    extractText = lambda s, l, t: RawString(s[t._original_start:t._original_end])

    def pythonize(toks):
        s = toks[0]
        if s == 'true':
            return True
        elif s == 'false':
            return False
        elif s == 'none':
            return [None]
        elif s.isdigit():
            return int(s)
        elif re.match('(?i)^-?(\d+\.?e\d+|\d+\.\d*|\.\d+)$', s):
            return float(s)
        return toks[0]

    def noneDefault(s, loc, t):
        return t if len(t) else [RawEOL]

    # define punctuation as suppressed literals
    lbrace, rbrace = map(Suppress, "{}")

    identifier = Word(printables, excludeChars='{}"\'')
    quotedStr = QuotedString('"', escChar='\\', multiline=True) | \
                QuotedString('\'', escChar='\\', multiline=True)
    quotedIdentifier = QuotedString('"', escChar='\\', unquoteResults=False) | \
                       QuotedString('\'', escChar='\\', unquoteResults=False)
    dictStr = Forward()
    setStr = Forward()
    objStr = Forward()

    #anyIdentifier = identifier | quotedIdentifier
    oddIdentifier = identifier + quotedIdentifier
    dictKey = dictStr | quotedStr | \
              Combine(oddIdentifier).setParseAction(cvtRaw)
    dictKey.setParseAction(cvtRaw)

    dictValue = quotedStr | dictStr | setStr | \
                Combine(oddIdentifier).setParseAction(cvtRaw)

    if OLD_STYLE_KEYS:
        dictKey |= Combine(identifier + ZeroOrMore(White(' ') + (identifier + ~FollowedBy(Optional(White(' ')) + LineEnd()))))
        dictValue |= identifier.setParseAction(pythonize)
    else:
        dictKey |= identifier
        dictValue |= delimitedList(identifier | quotedIdentifier, delim=White(' '), combine=True).setParseAction(pythonize)

    ParserElement.setDefaultWhitespaceChars(' \t')
    #dictEntry = Group(Combine(OneOrMore(identifier | quotedIdentifier)).setParseAction(cvtRaw) +
    dictEntry = Group(dictKey +
                      Optional(White(' ').suppress() + dictValue).setParseAction(noneDefault) +
                      Optional(White(' ').suppress()) +
                      LineEnd().suppress())
    #dictEntry = Group(SkipTo(dictKey + LineEnd() + dictKey))
    dictStr << (lbrace + ZeroOrMore(dictEntry) + rbrace)
    dictStr.setParseAction(cvtDict)
    ParserElement.setDefaultWhitespaceChars(' \t\r\n')

    setEntry = identifier.setParseAction(pythonize) | quotedString.setParseAction(removeQuotes)
    setStr << (lbrace + delimitedList(setEntry, delim=White()) + rbrace)
    setStr.setParseAction(cvtTuple)

    # TODO: take other literals as arguments
    blobObj = Group(((Literal('ltm') + Literal('rule') + identifier) | \
                     (Literal('rule') + identifier)).setParseAction(cvtRaw) +
                    originalTextFor(nestedExpr('{', '}')).setParseAction(extractText))

    objEntry = Group(OneOrMore(identifier | quotedIdentifier).setParseAction(cvtRaw) +
                     Optional(dictStr).setParseAction(noneDefault))
    objStr << (Optional(delimitedList(blobObj | objEntry, delim=LineEnd())))
    objStr.setParseAction(cvtGlobDict)
    #objStr.setParseAction(cvtTuple)
    objStr.ignore(pythonStyleComment)

    return objStr.parseString(text)[0]
    #return AttrDict(objStr.parseString(text)[0])


def dumps(obj):
    return TMSHEncoder(indent=4).encode(obj)


ESCAPE_DCT = {
    '\\': '\\\\',
    '"': '\\"',
    '\b': '\\b',
    '\f': '\\f',
    '\n': '\n',
    '\r': '\\r',
    '\t': '\t',
}


class TMSHEncoder(json.JSONEncoder):
    item_separator = ''
    key_separator = ' '

    def iterencode(self, o, _one_shot=False):
        """Encode the given object and yield each string
        representation as available.

        For example::

            for chunk in JSONEncoder().iterencode(bigobject):
                mysocket.write(chunk)

        """
        if self.check_circular:
            markers = {}
        else:
            markers = None

        def _encoder(s):
            """Return a JSON representation of a Python string

            """
            def replace(match):
                return ESCAPE_DCT[match.group(0)]
            if not isinstance(s, RawString) and re.search('\s', s):
                return '"' + json.encoder.ESCAPE.sub(replace, s) + '"'
            else:
                #return json.encoder.ESCAPE.sub(replace, s)
                return s

        def floatstr(o, allow_nan=self.allow_nan,
                _repr=json.encoder.FLOAT_REPR, _inf=json.encoder.INFINITY,
                _neginf=-json.encoder.INFINITY):
            # Check for specials.  Note that this type of test is processor
            # and/or platform-specific, so do tests which don't depend on the
            # internals.

            if o != o:
                text = 'NaN'
            elif o == _inf:
                text = 'Infinity'
            elif o == _neginf:
                text = '-Infinity'
            else:
                return _repr(o)

            if not allow_nan:
                raise ValueError(
                    "Out of range float values are not JSON compliant: " +
                    repr(o))

            return text

        _iterencode = _make_iterencode(
            markers, self.default, _encoder, self.indent, floatstr,
            self.key_separator, self.item_separator, self.sort_keys,
            self.skipkeys, _one_shot)
        return _iterencode(o, -1)


def _make_iterencode(markers, _default, _encoder, _indent, _floatstr,
        _key_separator, _item_separator, _sort_keys, _skipkeys, _one_shot,
        ## HACK: hand-optimized bytecode; turn globals into locals
        ValueError=ValueError,  # @ReservedAssignment
        basestring=basestring,  # @ReservedAssignment
        dict=dict,  # @ReservedAssignment
        float=float,  # @ReservedAssignment
        id=id,  # @ReservedAssignment
        int=int,  # @ReservedAssignment
        isinstance=isinstance,  # @ReservedAssignment
        list=list,  # @ReservedAssignment
        long=long,  # @ReservedAssignment
        str=str,  # @ReservedAssignment
        tuple=tuple,  # @ReservedAssignment
    ):

    def _iterencode_list(lst, _current_indent_level):
        if not lst:
            yield '{}'
            return
        if markers is not None:
            markerid = id(lst)
            if markerid in markers:
                raise ValueError("Circular reference detected")
            markers[markerid] = lst
        buf = '{'
        if _indent is not None:
            _current_indent_level += 1
            #newline_indent = '\n' + (' ' * (_indent * _current_indent_level))
            newline_indent = ' '
            separator = _item_separator + newline_indent
            buf += newline_indent
        else:
            newline_indent = None
            separator = _item_separator
        first = True
        for value in lst:
            if first:
                first = False
            else:
                buf = separator
            if isinstance(value, basestring):
                yield buf + _encoder(value)
            elif value is None:
                yield buf
            elif value is True:
                yield buf + 'true'
            elif value is False:
                yield buf + 'false'
            elif isinstance(value, (int, long)):
                yield buf + str(value)
            elif isinstance(value, float):
                yield buf + _floatstr(value)
            else:
                yield buf
                if isinstance(value, (list, tuple)):
                    chunks = _iterencode_list(value, _current_indent_level)
                elif isinstance(value, dict):
                    chunks = _iterencode_dict(value, _current_indent_level)
                else:
                    chunks = _iterencode(value, _current_indent_level)
                for chunk in chunks:
                    yield chunk
        if newline_indent is not None:
            _current_indent_level -= 1
            #yield '\n' + (' ' * (_indent * _current_indent_level))
            yield ' '
        yield '}'
        if markers is not None:
            del markers[markerid]

    def _iterencode_dict(dct, _current_indent_level):
        if not dct:
            yield '{}'
            return
        if markers is not None:
            markerid = id(dct)
            if markerid in markers:
                raise ValueError("Circular reference detected")
            markers[markerid] = dct
        if _current_indent_level >= 0:
            if not isinstance(dct, RawDict):
                yield '{'
        if _indent is not None:
            _current_indent_level += 1
            newline_indent = '\n' + (' ' * (_indent * _current_indent_level))
            item_separator = _item_separator + newline_indent
            if _current_indent_level:
                yield newline_indent
        else:
            newline_indent = None
            item_separator = _item_separator
        first = True
        if _sort_keys:
            items = sorted(dct.items(), key=lambda kv: kv[0])
        else:
            items = dct.iteritems()
        for key, value in items:
            if isinstance(key, basestring):
                pass
            # JavaScript is weakly typed for these, so it makes sense to
            # also allow them.  Many encoders seem to do something like this.
            elif isinstance(key, float):
                key = _floatstr(key)
            elif key is True:
                key = 'true'
            elif key is False:
                key = 'false'
            elif key is None:
                key = 'null'
            elif isinstance(key, (int, long)):
                key = str(key)
            elif _skipkeys:
                continue
            else:
                raise TypeError("key " + repr(key) + " is not a string")
            if first:
                first = False
            else:
                yield item_separator
            yield _encoder(key)
            if not value is RawEOL:
                yield _key_separator
            if isinstance(value, basestring):
                yield _encoder(value)
            elif value is None:
                yield 'none'
            elif value is RawEOL:
                yield ''
            elif value is True:
                yield 'true'
            elif value is False:
                yield 'false'
            elif isinstance(value, (int, long)):
                yield str(value)
            elif isinstance(value, float):
                yield _floatstr(value)
            else:
                if isinstance(value, (list, tuple)):
                    chunks = _iterencode_list(value, _current_indent_level)
                elif isinstance(value, dict):
                    chunks = _iterencode_dict(value, _current_indent_level)
                else:
                    chunks = _iterencode(value, _current_indent_level)
                for chunk in chunks:
                    yield chunk
        if newline_indent is not None:
            _current_indent_level -= 1
            yield '\n' + (' ' * (_indent * _current_indent_level))
        if _current_indent_level >= 0:
            if not isinstance(dct, RawDict):
                yield '}'
        if markers is not None:
            del markers[markerid]

    def _iterencode(o, _current_indent_level):
        if isinstance(o, basestring):
            yield _encoder(o)
        elif o is None:
            yield 'null'
        elif o is True:
            yield 'true'
        elif o is False:
            yield 'false'
        elif isinstance(o, (int, long)):
            yield str(o)
        elif isinstance(o, float):
            yield _floatstr(o)
        elif isinstance(o, (list, tuple)):
            for chunk in _iterencode_list(o, _current_indent_level):
                yield chunk
        elif isinstance(o, dict):
            for chunk in _iterencode_dict(o, _current_indent_level):
                yield chunk
        else:
            if markers is not None:
                markerid = id(o)
                if markerid in markers:
                    raise ValueError("Circular reference detected")
                markers[markerid] = o
            o = _default(o)
            for chunk in _iterencode(o, _current_indent_level):
                yield chunk
            if markers is not None:
                del markers[markerid]

    return _iterencode


if __name__ == '__main__':
    import pprint

    test = r"""
    key /Common/address {
        a-set {
            a1
            b1
            c2
            d2
            TCP::UDP
        }
        q-string "Multiline \"
        quoted string"
        single-line 'foo \' baz bar'
        subkey value
        a-none none
        number 100
        enabled 1
        ipv4 201.2.33.1
        ipv4-mask 10.10.2.3/24
        ipv6 2002:89f5::1
        number-alpha 1a
        one-line-set { a b c 1.1 2.3.4 600 none }
        ssl-ciphersuite ALL:!ADH:!EXPORT:!eNULL:!MD5:!DES:RC4+RSA:+HIGH:+MEDIUM:+LOW:+SSLv2
        subsub {
            boom blah
            alpha beta
            underscore in_value
            space after-value 
            another value
            gah
              test 123
            enabled
            child {
                okay
            }
        }
        "spaced key" {
            a value
        }
        just-one {
            key some-value
        }
        special:"key space" {}
        bool true
        empty { }
    }
    bigpipe keys {
        this is a long whitespaced key-value "with quotes"
        this is another long whitespaced key-value
    }
    ltm node node1 {}
    ltm node node2 {}

    #---------------
    ltm rule my-irule {
        # My irule
        partition Common
        if {not [info exists tmm_auth_http_collect_count]} {
            HTTP::collect
            set tmm_auth_http_successes 0
            set tmm_auth_http_collect_count 1
        } else {
            incr tmm_auth_http_collect_count
        }
    }

    mgmt 172.27.66.162 {
       netmask 255.255.255.128
    }
    """

    #test = file('/tmp/profile_base.conf').read()
    #test = file('/tmp/wam_base.conf').read()
    #test = file('/tmp/bp946.conf').read()
    #test = file('/tmp/pme.conf').read()
    #test = file('/tmp/a.conf').read()
    #print "Input:", test.strip()
    result = parser(test)
    print "Result:"
    pprint.pprint(dict(result))

    print "Encoded:"
    print dumps(result)

    print "Filter:"
    print dumps(result.glob('ltm rule *'))
    #print result.glob_keys('mgmt*')[0]
