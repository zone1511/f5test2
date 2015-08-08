'''
Created on Mar 9, 2015

@author: jwong (Based off of rest/netx/resources.py)
'''
from ..core import RestInterface, AUTH
from ..driver import BaseRestResource, WrappedResponse
from ...config import ADMIN_ROLE
from f5test.interfaces.rest.apic.objects.system import aaaLogin
from restkit import ResourceError
import urlparse
import logging

LOG = logging.getLogger(__name__)


class ApicResourceError(ResourceError):
    """Includes a parsed traceback as returned by the server."""

    def __init__(self, e):
        response = WrappedResponse(e.response, e.msg)
        super(ApicResourceError, self).__init__(msg=e.msg,
                                                http_code=e.status_int,
                                                response=response)

    def __str__(self):
        MAX_BODY_LENGTH = 1024
        if self.response.data and isinstance(self.response.data, dict):
            return ("{response.request.method} {response.final_url} failed:\n"
                    "Code: {data.imdata.error.@code}\n"
                    "Message: {data.imdata.error.@text}\n"
                    "".format(data=self.response.data,
                              response=self.response.response))
        else:
            return ("{response.request.method} {response.final_url} failed:\n"
                    "{body}\n"
                    "Status: {response.status}\n"
                    "".format(response=self.response.response,
                              body=self.response.body[:MAX_BODY_LENGTH]))


class ApicRestResource(BaseRestResource):
    api_version = 1
    default_content_type = 'application/xml'

    def request(self, method, path=None, payload=None, headers=None,
                params_dict=None, odata_dict=None, **params):
        """Perform HTTP request.

        Returns a parsed JSON object (dict).

        :param method: The HTTP method
        :param path: string additional path to the uri
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

        # Strip the schema and hostname part.
        path = urlparse.urlparse(path).path

        # Add .xml to path if it is not already there.
        if not path.endswith('.xml'):
            path += '.xml'

        try:
            wrapped_response = super(ApicRestResource, self).request(method, path=path,
                                                                     payload=payload,
                                                                     headers=headers,
                                                                     params_dict=params_dict,
                                                                     **params)
        except ResourceError, e:
            raise ApicResourceError(e)

        return wrapped_response.data


class ApicInterface(RestInterface):
    api_class = ApicRestResource
    creds_role = ADMIN_ROLE

    class CookieHeaderFilter(object):
        """ Simple filter to manage cookie authentication"""

        def __init__(self, token):
            self.token = token

        def on_request(self, request):
            request.headers['Cookie'] = "APIC-Cookie=%s" % self.token

    def __init__(self, device=None, address=None, username=None, password=None,
                 port=None, proto='https', timeout=90, url=None, token=None,
                 *args, **kwargs):
        super(ApicInterface, self).__init__(device, address, username, password,
                                            port, proto, timeout, AUTH.TOKEN,
                                            url)
        self.token = token

    def open(self):  # @ReservedAssignment
        url = "{0[proto]}://{0[address]}:{0[port]}".format(self.__dict__)
        self.api = self.api_class(url, timeout=self.timeout)
        if not self.token:
            payload = aaaLogin()
            payload.aaaUser['@name'] = self.username
            payload.aaaUser['@pwd'] = self.password
            ret = self.api.post(aaaLogin.URI, payload)
            self.token = ret.imdata.aaaLogin['@token']
        self.api.client.request_filters.append(self.CookieHeaderFilter(self.token))
