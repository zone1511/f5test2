'''
Created on Feb 25, 2013

@author: jono
'''
from ..base import SeleniumCommand
from ....interfaces.config import ConfigInterface, DeviceAccess
# from ....interfaces.selenium import By
# from ....interfaces.selenium.driver import (NoSuchFrameException,
#                                             NoSuchElementException, ElementWait)
# from .. import common
import logging
# import urlparse

LOG = logging.getLogger(__name__)


# class LicenseExpiredWait(ElementWait):
#
#     def __init__(self, interface, url, *args, **kwargs):
#         self._interface = interface
#         # Find the base URL.
#         # https://1.2.3.4:443/ui/login.jsp -> https://1.2.3.4:443
#         o = urlparse.urlsplit(url)
#         self.url = urlparse.urlunparse((o.scheme, o.netloc, '', '', '', ''))
#         return super(LicenseExpiredWait, self).__init__(interface.api, *args, **kwargs)
#
#     def test_error(self, exc_type, exc_value, exc_traceback):
#         b = self._interface.api
#         try:
#             b.switch_to_frame('contentframe')
#             reactivate_button = b.find_element_by_id('exit_button')
#             LOG.warning('License is about to expire. Attempting to reactivate.')
#             next_button = reactivate_button.click().wait('next')
#             next_button.click()
#             common.wait_for_loading(ifc=self._interface)
#             # Overriding the original result, which is probably None at this point
#             self._result = b.get(self.url).wait('loginDiv')
#             return True
#         except (NoSuchFrameException, NoSuchElementException) as e:
#             LOG.debug('LicenseExpiredWait: %s', e)
#         finally:
#             b.switch_to_default_content()


login = None
class Login(SeleniumCommand):  # @IgnorePep8
    """Log in command.

    @param device: The device.
    @type device: str or DeviceAccess instance
    @param address: The IP or hostname.
    @type address: str
    @param username: The username.
    @type username: str
    @param password: The password.
    @type password: str
    """
    def __init__(self, device=None, address=None, username=None, password=None,
                 port=None, proto='https', timeout=10, *args, **kwargs):
        super(Login, self).__init__(*args, **kwargs)
        self.timeout = timeout
        self.proto = proto
        self.path = '/tmui/login.jsp'
        if device or not address:
            self.device = device if isinstance(device, DeviceAccess) \
                        else ConfigInterface().get_device(device)
            self.address = address or self.device.address
            self.port = port or self.device.ports.get(proto, 443)
            self.username = username or self.device.get_admin_creds().username
            self.password = password or self.device.get_admin_creds().password
        else:
            self.device = device
            self.address = address
            self.port = port
            self.username = username
            self.password = password

    def setup(self):
        b = self.api
        # Set the api login data
        self.ifc.set_credentials(device=self.device, address=self.address,
                                 username=self.username, password=self.password,
                                 port=self.port, proto=self.proto)

        ua, _ = self.ifc.useragent
        LOG.info("Browser: %s", ua)
        LOG.info("Selenium head: (%s) %s", self.ifc.head, self.ifc.executor)

        url = "{0[proto]}://{0[address]}:{0[port]}{0[path]}".format(self.__dict__)
        b.get(url).wait('username')

        e = b.find_element_by_name("username")
        e.click()
        e.send_keys(self.username)

        e = b.find_element_by_id("passwd")
        e.send_keys(self.password)
        e.submit().wait('setup')
        b.maximize_window()
