"""Selenium interface"""

from ..config import ConfigInterface, DeviceAccess
from ..icontrol import IcontrolInterface
from .driver import RemoteWrapper, Keys
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

    @param head: the name of the selenium head as defined in the config.
    @type head: str
    @param executor: URL of the Selenium server (e.g. http://127.0.0.1:4444/wd/hub)
    @type executor: str
    @param browser: firefox or internetexplorer or htmunit
    @type browser: str
    @param platform: ANY or LINUX or WINDOWS
    @type platform: str
    """
    def __init__(self, head=None, executor=None, browser=None, platform=None,
                 options=None, *args, **kwargs):
        super(SeleniumInterface, self).__init__()

        head, headdict = ConfigInterface().get_selenium_head(head)
        if executor is None:
            executor = headdict.get('address')
        if browser is None:
            browser = headdict.get('browser')
        if platform is None:
            platform = headdict.get('platform', 'ANY')
        if options is None:
            options = headdict.get('options', AttrDict())

        self.head = head
        self.executor = executor
        self.browser = browser
        self.platform = platform
        self.options = options
        self.device = None
        self.address = None
        self.username = None
        self.password = None
        self.credentials = AttrDict()
        self._priority = 1

    def __repr__(self):
        name = self.__class__.__name__
        credentials = self.get_credentials()
        return "<{0}: {1.username}:{1.password}@{1.address}:{1.port}>".format(name, credentials)

    @property
    def _current_window(self):
        assert self.is_opened()
        return self.api.current_window_handle

    def set_credentials(self, window=None, device=None, address=None,
                        username=None, password=None, port=None, proto='https'):
        """Set the credentials for the current window"""
        data = AttrDict()
        data.proto = proto
        if device or not address:
            data.device = device if isinstance(device, DeviceAccess) \
                        else ConfigInterface().get_device(device)
            data.address = address or data.device.address
            data.port = port or data.device.ports.get(proto, 443)
            data.username = username or data.device.get_admin_creds().username
            data.password = password or data.device.get_admin_creds().password
        else:
            data.device = device
            data.address = address
            data.port = port
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

    def get_icontrol_interface(self, timeout=90, debug=False, window=None):
        data = self.get_credentials(window)
        return IcontrolInterface(device=data.device, address=data.address,
                                 username=data.username, password=data.password,
                                 port=data.port, timeout=timeout, debug=debug)

    @property
    def version(self):
        from ...commands import icontrol as ICMD
        icifc = self.get_icontrol_interface()
        return ICMD.system.get_version(ifc=icifc)

    @property
    def useragent(self):
        ua = self.api.execute_script("return navigator.userAgent")
        return (ua, AttrDict(httpagentparser.detect(ua)))

    def _disable_firefox_addon_bar(self):
        # XXX: Workaround for FF Add-on Bar masking page elements making them
        # unclickable. This keyboard shortcut should have no effect on other
        # browsers.
        self.api.switch_to_active_element().send_keys(Keys.CONTROL, '/')

    def open(self):  # @ReservedAssignment
        """Returns the handle to a Selenium 2 remote client.

        @return: the selenium remote client object.
        @rtype: L{RemoteWrapper}
        """
        if self.api:
            return self.api

        executor = self.executor
        browser = self.browser
        platform = self.platform
        self.api = RemoteWrapper(command_executor=executor,
                                 desired_capabilities=dict(
                                                           #javascriptEnabled=True,
                                                           browserName=browser,
                                                           platform=platform
                                 ),
                                 keep_alive=False)

        # Special casing htmlunit which doesn't like to execute JS before a page
        # has been loaded.
        if not self.api.name == 'htmlunit':
            LOG.info("Browser: %s", self.useragent[0])
            LOG.info("Selenium head: (%s) %s", self.head, self.executor)

        self.window = self.api.current_window_handle
        #self._disable_firefox_addon_bar()
        return self.api

    def close(self, *args, **kwargs):
        self.api.quit()
        super(SeleniumInterface, self).close()
