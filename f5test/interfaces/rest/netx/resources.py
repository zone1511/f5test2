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
CURL_LOG = "curl -sk -u {username}:{password} -X {method} {headers} -d '{payload}' '{url}'"
DEFAULT_CONTENT = {'Content-Type': 'application/xml'}


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


class NetxRestResource(RestResource):
    api_version = 2
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

        if payload is not None and not headers:
            headers.update(DEFAULT_CONTENT)

        if odata_dict:
            dollar_keys = dict(('$%s' % x, y) for x, y in odata_dict.iteritems())
            if params_dict is None:
                params_dict = {}
            params_dict.update(dollar_keys)

        # Strip the schema and hostname part.
        path = urlparse.urlparse(path).path
        response = wrapped_response = None
        try:
            wrapped_response = super(NetxRestResource, self).request(method, path=path,
                                                              payload=payload,
                                                              headers=headers,
                                                              params_dict=params_dict,
                                                              **params)
            response = wrapped_response.response
        except ResourceError, e:
            response = e.response
            raise NetxResourceError(e)
        finally:
            credentials = self.client.filters[0].credentials
            log = STDOUT if self.verbose else LOG
            if response is not None:
                headers = []
                for name, value in response.request.headers.items():
                    if name not in ('Authorization', 'Content-Length'):
                        headers.append('-H "%s: %s"' % (name, value))
                log.debug(CURL_LOG.format(method=method, uri=self.uri,
                                          path=path, url=response.final_url,
                                          headers=' '.join(headers),
                                          username=credentials[0], password=credentials[1],
                                          payload=(response.request.body or '').replace("'", "\\'")))
            if wrapped_response is not None:
                log.debug(wrapped_response.body)

        return wrapped_response.data


class NetxInterface(RestInterface):
    api_class = NetxRestResource
