'''
Created on Feb 22, 2012

@author: jono
'''
from restkit import Resource, ResourceError
from restkit.filters import BasicAuth
from restkit.datastructures import MultiDict
import urllib
from ...base import AttrDict
import xmltodict
import logging
try:
    import simplejson as json
except ImportError:
    try:
        import json
    except ImportError:
        json = False


CURL_LOG = "curl -sk {credentials} -X {method} -d '{payload}' '{url}'"
RAW_MIMETYPE = 'application/do-not-parse-this-content'
LOG = logging.getLogger(__name__)
STDOUT = logging.getLogger('stdout')
MAX_LINE_LENGTH = 65536


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


class BaseRestResource(Resource):
    """All requests return a response object """
    trailing_slash = False
    no_keepalive = False
    default_content_type = 'application/json'
    verbose = False

    def __init__(self, *args, **kwargs):
        self.default_params = None
        self.default_params_condition = None
        return super(BaseRestResource, self).__init__(*args, **kwargs)

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
            'multipart/form-data': lambda x: x,
        }
        return common_indent.get(mimetype, str)(data)

    def patch(self, path=None, payload=None, headers=None,
              params_dict=None, **params):
        """HTTP PATCH

        See POST for params description.
        """
        return self.request("PATCH", path=path, payload=payload,
                            headers=headers, params_dict=params_dict, **params)

    def set_default_params(self, condition=None, **params):
        if callable(condition):
            self.default_params_condition = condition
        self.default_params = params

    def request(self, method, path=None, payload=None, headers=None,
                params_dict=None, raw=False, **params):

        headers = MultiDict(headers or {})
        if payload is not None and not headers.iget('content-type'):
            headers.update({'Content-Type': self.default_content_type})

        # Default Keep-Alive is set to 4 seconds in TMOS.
        if self.no_keepalive:
            headers.update({'Connection': 'Close'})

        if path is not None:
            if self.trailing_slash and path[-1] != '/':
                path += '/'

        if payload is not None and headers and headers.iget('Content-Type'):
            mimetype = RAW_MIMETYPE if raw \
                else mimetype_from_headers(headers)
            payload = BaseRestResource._parse(mimetype, payload)

        if self.default_params is not None:
            condition = True
            if self.default_params_condition is not None:
                condition = self.default_params_condition(path)
            if condition:
                params_dict = params_dict or {}
                params_dict.update(self.default_params)

        wrapped_response = response = None
        try:
            response = super(BaseRestResource, self).request(method, path=path,
                                                             payload=payload,
                                                             headers=headers,
                                                             params_dict=params_dict,
                                                             **params)
            wrapped_response = WrappedResponse(response, raw=raw)
        except ResourceError, e:
            response = e.response
            raise e
        finally:
            if self.client.filters:
                credentials = self.client.filters[0].credentials
                credentials = '-u {0[0]}:{0[1]}'.format(credentials)
            else:
                credentials = ''
            log = STDOUT if self.verbose else LOG
            if response is not None:
                if isinstance(response.request.body, (type(None), basestring)):
                    log.debug(CURL_LOG.format(method=method, uri=self.uri,
                                              path=path, url=response.final_url,
                                              credentials=credentials,
                                              payload=(response.request.body or '').replace("'", "\\'"))[:MAX_LINE_LENGTH])
            if wrapped_response is not None:
                log.debug(wrapped_response.body[:MAX_LINE_LENGTH])

        return wrapped_response

    def get_by_id(self, *args):
        slash = '/' if self.trailing_slash else ''
        if len(args) == 1:
            return self.get('{0[0]}{1}'.format(args, slash))
        return self.get('set/{0}{1}'.format(';'.join([str(x) for x in args]),
                                            slash))

    def filter(self, **kwargs):  # @ReservedAssignment
        return self.get(params_dict=kwargs)


class RestResource(BaseRestResource):
    """All requests return a parsed response, based on content-type"""

    def request(self, *args, **kwargs):
        return super(RestResource, self).request(*args, **kwargs).data
