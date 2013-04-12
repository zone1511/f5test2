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
STDOUT = logging.getLogger('stdout')
CURL_LOG = "curl -sk -u {username}:{password} -X {method} -d '{payload}' '{url}'"
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

        if headers is None:
            headers = {}

        if payload and not headers:
            headers.update(CONTENT_JSON)

        if odata_dict:
            dollar_keys = dict(('$%s' % x, y) for x, y in odata_dict.iteritems())
            if params_dict is None:
                params_dict = {}
            params_dict.update(dollar_keys)

        # Strip the schema and hostname part.
        path = urlparse.urlparse(path).path
        try:
            wrapped_response = super(EmapiRestResource, self).request(method, path=path,
                                                              payload=payload,
                                                              headers=headers,
                                                              params_dict=params_dict,
                                                              **params)
            response = wrapped_response.response
        except ResourceError, e:
            wrapped_response = None
            response = e.response
            raise EmapiResourceError(e)
        finally:
            credentials = self.client.filters[0].credentials
            log = STDOUT if self.verbose else LOG
            log.debug(CURL_LOG.format(method=method, uri=self.uri, path=path,
                                      url=response.final_url,
                                      username=credentials[0], password=credentials[1],
                                      payload=(response.request.body or '').replace("'", "\\'")))
            if wrapped_response:
                log.debug(wrapped_response.body)

        return wrapped_response.data


class EmapiInterface(RestInterface):
    api_class = EmapiRestResource
