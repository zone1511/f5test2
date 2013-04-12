'''
Created on Feb 25, 2013

@author: jono
'''
from ..base import SeleniumCommand
from ....interfaces.config import ConfigInterface, DeviceAccess
from ....interfaces.selenium import By, Is
#from ....interfaces.selenium.driver import NoSuchElementException, ElementWait
#from ....base import AttrDict
#from ...base import WaitableCommand, CommandError
#import os
import logging
#import re
#import codecs
UI_CLOUD = 0
UI_SECURITY = 1
UI_TMOS = 2

LOG = logging.getLogger(__name__)


login = None
class Login(SeleniumCommand): #@IgnorePep8
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
                 port=None, proto='https', timeout=120, ui=UI_SECURITY, *args, **kwargs):
        super(Login, self).__init__(*args, **kwargs)
        self.timeout = timeout
        self.proto = proto
        self.path = '/tmui/login.jsp'
        self.ui = ui
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
        # XXX: This needs to go when they fix the UI
        product_picker = e.submit().wait('loginDiv')

        xpaths = {UI_SECURITY: 'a[div="BIG-IQ Security"]',
                  UI_CLOUD: 'a[div="BIG-IQ Cloud"]',
                  UI_TMOS: 'a[div="TMOS"]'
        }

        link = product_picker.find_element_by_xpath(xpaths.get(self.ui))
        link.click()

        if self.ui == UI_SECURITY:
            b.wait('.modal-dialog', negated=True, by=By.CSS_SELECTOR)
        elif self.ui == UI_CLOUD:
            b.wait('pageModal', negated=True)
        elif self.ui == UI_TMOS:
            b.wait('#navbar > #trail span', by=By.CSS_SELECTOR, timeout=30)
        else:
            raise ValueError("Unsupported product")
        b.maximize_window()
