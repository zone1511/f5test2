'''
Created on Feb 26, 2012

@author: jono
'''
from .core import RestInterface
from .driver import BaseRestResource
import urlparse


class IrackRestResource(BaseRestResource):
    api_version = 1
    trailing_slash = True

    @property
    def asset(self):
        uri = urlparse.urljoin(self.uri, '/api/v%s/asset/' % self.api_version)
        return self.__class__(uri, **self.client_opts)

    @property
    def f5asset(self):
        uri = urlparse.urljoin(self.uri, '/api/v%s/f5asset/' % self.api_version)
        return self.__class__(uri, **self.client_opts)

    @property
    def staticbag(self):
        uri = urlparse.urljoin(self.uri, '/api/v%s/staticbag/' % self.api_version)
        return self.__class__(uri, **self.client_opts)

    @property
    def staticaddress(self):
        uri = urlparse.urljoin(self.uri, '/api/v%s/staticaddress/' % self.api_version)
        return self.__class__(uri, **self.client_opts)

    @property
    def staticlicense(self):
        uri = urlparse.urljoin(self.uri, '/api/v%s/staticlicense/' % self.api_version)
        return self.__class__(uri, **self.client_opts)

    @property
    def staticsystem(self):
        uri = urlparse.urljoin(self.uri, '/api/v%s/staticsystem/' % self.api_version)
        return self.__class__(uri, **self.client_opts)

    def from_uri(self, uri):
        uri = urlparse.urljoin(self.uri, uri)
        return self.__class__(uri, **self.client_opts)

class IrackInterface(RestInterface):
    api_class = IrackRestResource

