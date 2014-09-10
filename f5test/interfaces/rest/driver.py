'''
Created on Feb 22, 2012

@author: jono
'''
from restkit import Resource
from restkit.filters import BasicAuth
import urllib
from ...base import AttrDict
import xmltodict
try:
    import simplejson as json
except ImportError:
    try:
        import json
    except ImportError:
        json = False


RAW_MIMETYPE = 'application/do-not-parse-this-content'


# Monkey patch BasicAuth to handle encoded username and passwords containing
# unsafe characters (such as /$@:)
# https://github.com/benoitc/restkit/issues/128
def patched_constructor(self, username, password):
    username = urllib.unquote_plus(username)
    password = urllib.unquote_plus(password)
    self.credentials = (username, password)
BasicAuth.__init__ = patched_constructor


def mimetype_from_headers(headers):
    ctype = headers.get('Content-Type')
    if not ctype:
        ctype = RAW_MIMETYPE
    try:
        mimetype, _ = ctype.split(";", 1)
    except ValueError:
        mimetype = ctype.split(";")[0]

    return mimetype


class WrappedResponse(object):

    def __init__(self, response, body=None, raw=False):
        self.response = response
        self.body = body if body is not None else response.body_string()
        self._data = None
        self.raw = raw

    @staticmethod
    def _parse_json(data):
        if not json:
            return data
        return AttrDict(json.loads(data))

    @staticmethod
    def _parse_xml(data):
        return AttrDict(xmltodict.parse(data))

    @staticmethod
    def _parse(mimetype, data):
        common_indent = {
            'application/json': WrappedResponse._parse_json,
            'application/xml': WrappedResponse._parse_xml,
        }
        if mimetype in common_indent:
            return common_indent[mimetype](data)
        return data

    @property
    def data(self):
        if self._data:
            return self._data

        mimetype = RAW_MIMETYPE if self.raw \
                                else mimetype_from_headers(self.response.headers)
        # indent body
        body = self.body
        if body:
            self._data = WrappedResponse._parse(mimetype, body)
            return self._data
        return AttrDict()


class RestResource(Resource):
    trailing_slash = False
    no_keepalive = False

    @staticmethod
    def _parse_json(data):
        if not json or isinstance(data, basestring):
            return data
        return json.dumps(data)

    @staticmethod
    def _parse_xml(data):
        if isinstance(data, basestring):
            return data
        return xmltodict.unparse(data)

    @staticmethod
    def _parse(mimetype, data):
        common_indent = {
            'application/json': RestResource._parse_json,
            'application/xml': RestResource._parse_xml,
        }
        if mimetype in common_indent:
            return common_indent[mimetype](data)
        return data

    def request(self, method, path=None, payload=None, headers=None,
                params_dict=None, raw=False, **params):
        if headers is None:
            headers = {}

        # Default Keep-Alive is set to 4 seconds in TMOS.
        if self.no_keepalive:
            headers.update({'Connection': 'Close'})

        if path is not None:
            if self.trailing_slash and path[-1] != '/':
                path += '/'

        if payload is not None and headers and headers.get('Content-Type'):
            mimetype = RAW_MIMETYPE if raw \
                                    else mimetype_from_headers(headers)
            payload = RestResource._parse(mimetype, payload)

        response = super(RestResource, self).request(method, path=path,
                                                     payload=payload,
                                                     headers=headers,
                                                     params_dict=params_dict,
                                                     **params)
        return WrappedResponse(response, raw=raw)

    def get_by_id(self, *args):
        slash = '/' if self.trailing_slash else ''
        if len(args) == 1:
            return self.get('{0[0]}{1}'.format(args, slash))
        return self.get('set/{0}{1}'.format(';'.join([str(x) for x in args]),
                                            slash))

    def filter(self, **kwargs):  # @ReservedAssignment
        return self.get(params_dict=kwargs)
