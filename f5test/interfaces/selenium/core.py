"""Selenium interface"""

from ..config import ConfigInterface
from .driver import RemoteWrapper
from ...base import Interface
#from ...utils import net
import logging
#import urlparse
from ...base import AttrDict
import httpagentparser

LOG = logging.getLogger(__name__)

class SeleniumHandleError(Exception):
    pass

class SeleniumInterface(Interface):
    """Normally all UI tests share the same selenium handle, which is 
    initialized and torn down by the setUpModule and tearDownModule methods 
    of the 'ui' tests collection.
    """
    def __init__(self, head=None, executor=None, browser=None, platform=None, 
                 *args, **kwargs):
        super(SeleniumInterface, self).__init__()
        self.head = head
        self.executor = executor
        self.browser = browser
        self.platform = platform
        self.device = None
        self.address = None
        self.username = None
        self.password = None
        self.credentials = AttrDict()

    def __str__(self):
        self._get_credentials()
        return self.address or 'selenium-interface'

    @property
    def _current_window(self):
        assert self.is_opened()
        b = self.api
        return b.current_window_handle

    def _set_credentials(self, data, window=None):
        """Set the credentials for the current window"""
        if not window:
            window = self._current_window
        self.credentials[window] = data
        self.device = data.device
        self.address = data.address
        self.username = data.username
        self.password = data.password
        
    def _get_credentials(self, window=None):
        if not window:
            window = self._current_window
        data = self.credentials.get(window)
        if not data:
            LOG.warning('No credentials have been set for this window.')
            data = AttrDict()
        self.device = data.device
        self.address = data.address
        self.username = data.username
        self.password = data.password
        return data

    def _del_credentials(self, window=None):
        if not window:
            window = self._current_window
        return self.credentials.pop(window, None)

#    @property
#    def address(self):
#        assert self.is_opened()
#        b = self.api
#        url = urlparse.urlparse(b.current_url)
#        return net.resolv(url.hostname)
#        
#    @property
#    def device(self):
#        try:
#            cfgifc = ConfigInterface()
#            return cfgifc.get_device_by_address(self.address)
#        except ConfigNotLoaded:
#            LOG.warn("Configuration not available, device information won't be present for this interface.")
#
#    @property
#    def username(self):
#        device = self.device
#        if device:
#            return device.get_admin_creds().username
#        
#    @property
#    def password(self):
#        device = self.device
#        if device:
#            return self.device.get_admin_creds().password

    @property
    def version(self):
        from ...commands.icontrol.system import get_version
        return get_version(device=self.device, address=self.address, 
                           username=self.username, password=self.password)

    @property
    def useragent(self):
        ua = self.api.execute_script("return navigator.userAgent")
        return (ua, httpagentparser.detect(ua))

    def open(self):
        """Returns the handle to a Selenium 2 remote client.

        @param head: the name of the selenium head as defined in the config.
        @type head: str
        @param device: the name of the selenium head as defined in the config.
        @type device: str
        @return: the selenium remote client object.
        @rtype: L{RemoteWrapper}
        """
        if self.api:
            return self.api
        if self.head or not self.address:
            alias, head = ConfigInterface().get_selenium_head(self.head)
            self.head = alias
            executor = head['address']
            browser = head['browser']
            platform = head['platform']
        else:
            executor = self.executor
            browser = self.browser
            platform = self.platform

        self.api = RemoteWrapper(command_executor=executor, 
                                 desired_capabilities=dict(
                                                           #javascriptEnabled=True,
                                                           browserName=browser, 
                                                           platform=platform
                                 ))
        self.window = self.api.current_window_handle
        #self.head = head
        self.executor = executor
        self.browser = browser
        self.platform = platform
        return self.api
    
    def close(self, *args, **kwargs):
        self.api.quit()
        super(SeleniumInterface, self).close()

