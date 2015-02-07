'''
Created on Feb 26, 2012

@author: jono
'''
from ..core import RestInterface
from .objects.nsx import HeartBeat
from ..driver import BaseRestResource, WrappedResponse
from restkit import ResourceError
import urlparse
import logging

LOG = logging.getLogger(__name__)


class NetxResourceError(ResourceError):
    """Includes a parsed java traceback as returned by the server."""

    def __init__(self, e):
        response = WrappedResponse(e.response, e.msg)
        super(NetxResourceError, self).__init__(msg=e.msg,
                                                http_code=e.status_int,
                                                response=response)

    def __str__(self):
        MAX_BODY_LENGTH = 1024
        if self.response.data and isinstance(self.response.data, dict):
            return ("{response.request.method} {response.final_url} failed:\n"
                    "Code: {data.error.errorCode}\n"
                    "Message: {data.error.details}\n"
                    "Details: {data.error.rootCauseString}\n"
                    "".format(data=self.response.data,
                              response=self.response.response))
        else:
            return ("{response.request.method} {response.final_url} failed:\n"
                    "{body}\n"
                    "Status: {response.status}\n"
                    "".format(response=self.response.response,
                              body=self.response.body[:MAX_BODY_LENGTH]))


class NetxRestResource(BaseRestResource):
    api_version = 2
    verbose = False
    default_content_type = 'application/xml'

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

        # Strip the schema and hostname part.
        path = urlparse.urlparse(path).path
        try:
            wrapped_response = super(NetxRestResource, self).request(method, path=path,
                                                                     payload=payload,
                                                                     headers=headers,
                                                                     params_dict=params_dict,
                                                                     **params)
        except ResourceError, e:
            raise NetxResourceError(e)

        return wrapped_response.data


class NetxInterface(RestInterface):
    api_class = NetxRestResource

    @property
    def version(self):
        from ....utils.version import Version, Product
        ret = self.api.get(HeartBeat.URI)
        return Version(ret.vsmGlobalConfig.versionInfo, Product.NSX)
