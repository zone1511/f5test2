'''
Created on Feb 26, 2012

@author: jono
'''
from ..core import RestInterface
from ..driver import RestResource, WrappedResponse
from restkit import ResourceError
import urlparse
import logging

LOG = logging.getLogger(__name__)

# XXX: Monkey patch workaround for BZ410289
import restkit.util
from restkit.util import encode
import urllib

def url_encode(obj, charset="utf8", encode_keys=False):
    items = []
    if isinstance(obj, dict):
        for k, v in list(obj.items()):
            items.append((k, v))
    else:
        items = list(items)

    tmp = []
    for k, v in items:
        if encode_keys:
            k = encode(k, charset)

        if not isinstance(v, (tuple, list)):
            v = [v]

        for v1 in v:
            if v1 is None:
                v1 = ''
            elif callable(v1):
                v1 = encode(v1(), charset)
            else:
                v1 = encode(v1, charset)
            tmp.append('%s=%s' % (urllib.quote(k, safe='/$'), urllib.quote_plus(v1)))
    return '&'.join(tmp)
restkit.util.url_encode = url_encode
# END.

CONTENT_JSON = {'Content-Type': 'application/json'}
LOCALHOST_URL_PREFIX = 'http://localhost:8100'


def localize_uri(uri):
    if hasattr(uri, 'selfLink'):
        uri = uri.selfLink
    return urlparse.urljoin(LOCALHOST_URL_PREFIX, uri)


class EmapiResourceError(ResourceError):
    """Includes a parsed java traceback as returned by the server."""

    def __init__(self, e):
        response = WrappedResponse(e.response, e.msg)
        super(EmapiResourceError, self).__init__(msg=e.msg,
                                                 http_code=e.status_int,
                                                 response=response)

    def __str__(self):
        MAX_BODY_LENGTH = 1024
        if self.response.data:
            return ("{response.request.method} {response.final_url} failed:\n"
                   "{tb}\n"
                   "Operation ID: {data.restOperationId}\n"
                   "Code: {data.code}\n"
                   "Message: {data.message}\n"
                   "".format(tb='  \n'.join(map(lambda x: "  " + x,
                                                self.response.data.errorStack)),
                             data=self.response.data,
                             response=self.response.response))
        else:
            return ("{response.request.method} {response.final_url} failed:\n"
                   "{body}\n"
                   "Status: {response.status}\n"
                   "".format(response=self.response.response,
                             body=self.response.body[:MAX_BODY_LENGTH]))


class EmapiRestResource(RestResource):
    api_version = 1
    trailing_slash = False

    def patch(self, path=None, payload=None, headers=None,
              params_dict=None, **params):
        """HTTP PATCH

        See POST for params description.
        """
        return self.request("PATCH", path=path, payload=payload,
                        headers=headers, params_dict=params_dict, **params)

    def request(self, method, path=None, payload=None, headers=None,
                params_dict=None, odata_dict=None, **params):
        """Perform HTTP request.

        Returns a parsed JSON object (dict).

        :param method: The HTTP method
        :param path: string additionnal path to the uri
        :param payload: string or File object passed to the body of the request
        :param headers: dict, optionnal headers that will be added to HTTP
                        request.
        :param params_dict: Options parameters added to the request as a dict
        :param odata_dict: Similar to params_dict but keys will have a '$' sign
                           automatically prepended.
        :param params: Optionnal parameterss added to the request
        """

        if payload and headers is None:
            headers = CONTENT_JSON

        if odata_dict:
            dollar_keys = dict(('$%s' % x, y) for x, y in odata_dict.iteritems())
            if params_dict is None:
                params_dict = {}
            params_dict.update(dollar_keys)

        path = urlparse.urlparse(path).path
        LOG.debug("%s %s", method, path)
        if payload:
            LOG.debug(">>> %s", payload)
        try:
            response = super(EmapiRestResource, self).request(method, path=path,
                                                              payload=payload,
                                                              headers=headers,
                                                              params_dict=params_dict,
                                                              **params)
        except ResourceError, e:
            raise EmapiResourceError(e)

        LOG.debug("<<< %s", response.body)
        return response.data


class EmapiInterface(RestInterface):
    api_class = EmapiRestResource
