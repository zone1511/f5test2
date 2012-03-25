"""Selenium interface"""

from ..config import ConfigInterface, DeviceAccess
from .driver import RemoteWrapper
from ...base import Interface
import logging
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
        self._priority = 1

    @property
    def _current_window(self):
        assert self.is_opened()
        return self.api.current_window_handle

    def set_credentials(self, window=None, device=None, address=None, 
                         username=None, password=None):
        """Set the credentials for the current window"""
        data = AttrDict()
        if device or not address:
            data.device = device if isinstance(device, DeviceAccess) \
                        else ConfigInterface().get_device(device)
            data.address = address or data.device.address
            data.username = username or data.device.get_admin_creds().username
            data.password = password or data.device.get_admin_creds().password
        else:
            data.device = device
            data.address = address
            data.username = username
            data.password = password

        if window is None:
            window = self._current_window

        self.credentials[window] = data

    def get_credentials(self, window=None):
        if window is None:
            window = self._current_window

        data = self.credentials.get(window)
        
        if not data:
            LOG.warning('No credentials have been set for this window.')
            data = AttrDict()
        
        return data

    def del_credentials(self, window=None):
        if window is None:
            window = self._current_window

        return self.credentials.pop(window, None)

#    @property
#    def address(self):
#        window = self._current_window
#        return self._get_credentials(window).address
#        
#    @property
#    def device(self):
#        window = self._current_window
#        return self._get_credentials(window).device
#
#    @property
#    def username(self):
#        window = self._current_window
#        return self._get_credentials(window).username
#        
#    @property
#    def password(self):
#        window = self._current_window
#        return self._get_credentials(window).password

    @property
    def version(self):
        from ...commands.icontrol.system import get_version
        return get_version(device=self.device, address=self.address, 
                           username=self.username, password=self.password)

    @property
    def useragent(self):
        ua = self.api.execute_script("return navigator.userAgent")
        return (ua, httpagentparser.detect(ua))

    def open(self): #@ReservedAssignment
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

