'''
Created on Feb 26, 2012

@author: jono
'''
from ..core import RestInterface, AUTH
from .objects.system import AuthnLogin
from .objects.shared import DeviceInfo
from ..driver import BaseRestResource, WrappedResponse
from ....utils.querydict import QueryDict
from restkit import ResourceError, RequestError
import urlparse
import logging

LOG = logging.getLogger(__name__)
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
        if self.response.data and isinstance(self.response.data, dict):
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

    def __repr__(self):
        return ("{name}({response.request.method} {response.final_url}) {response.status}"
                .format(response=self.response.response,
                        name=type(self).__name__))


class EmapiRestResource(BaseRestResource):
    api_version = 1
    verbose = False

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

        if odata_dict:
            dollar_keys = dict(('$%s' % x, y) for x, y in odata_dict.iteritems())
            if params_dict is None:
                params_dict = {}
            params_dict.update(dollar_keys)

        if path is not None:
            path = str(path)
            bits = path.split('?', 1)
            if len(bits) > 1:
                path = bits[0]
                query_dict = QueryDict(bits[1])
                if not params_dict:
                    params_dict = {}
                params_dict.update(query_dict)

        # Strip the schema and hostname part.
        path = urlparse.urlparse(path).path
        try:
            wrapped_response = super(EmapiRestResource, self).request(method, path=path,
                                                                      payload=payload,
                                                                      headers=headers,
                                                                      params_dict=params_dict,
                                                                      **params)
        except ResourceError, e:
            raise EmapiResourceError(e)

        return wrapped_response.data


class EmapiInterface(RestInterface):
    """
    @param login_ref: Reference to auth provider
      Ex: {"link": "https://localhost/mgmt/cm/system/authn/providers/radius/5fb32248-722c-4ab4-8e6b-e223027e9d22/login"}
    """
    api_class = EmapiRestResource

    class TokenHeaderFilter(object):
        """ Simple filter to manage iControl REST token authentication"""

        def __init__(self, token):
            self.token = token

        def on_request(self, request):
            request.headers['X-F5-Auth-Token'] = self.token.token

    def __init__(self, device=None, address=None, username=None, password=None,
                 port=None, proto='https', timeout=90, auth=AUTH.BASIC, url=None,
                 login_ref=None, token=None, *args, **kwargs):
        super(EmapiInterface, self).__init__(device, address, username, password,
                                             port, proto, timeout, auth, url)
        self.login_ref = login_ref
        self.token = token

    @property
    def version(self):
        from ....utils.version import Version
        ret = self.api.get(DeviceInfo.URI)
        return Version("{0.product} {0.version} {0.build}".format(ret))

    def open(self):  # @ReservedAssignment
        if self.auth != AUTH.TOKEN:
            return super(EmapiInterface, self).open()
        else:
            url = "{0[proto]}://{0[address]}:{0[port]}".format(self.__dict__)
            self.api = self.api_class(url, timeout=self.timeout)
            if not self.token:
                payload = AuthnLogin()
                payload.username = self.username
                payload.password = self.password
                payload.loginReference = self.login_ref
                ret = self.api.post(AuthnLogin.URI, payload)
                self.token = ret.token
            self.api.client.request_filters.append(self.TokenHeaderFilter(self.token))

    def close(self, *args, **kwargs):  # @ReservedAssignment
        if self.token:
            try:
                self.api.delete(self.token.selfLink)
            except (RequestError, EmapiResourceError), e:
                LOG.debug('Failed to delete token on close: %s', e)
        return super(EmapiInterface, self).close()
