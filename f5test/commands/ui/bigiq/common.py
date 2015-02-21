'''
Created on Feb 25, 2013

@author: (Class: Login/Navigate) jono
@author: (Class: Logout/SeeBlade/ExpandBlade/ExpandBladeOnThisText
                /RetractBlade/SaveRetract/DeleteObjectOnText
                /DragAndDrop/ExpandGroup) Andrei Dobre
@author: (Class: BrushOnText) dhandapani
'''
from ..base import SeleniumCommand
from ....interfaces.config import ConfigInterface, DeviceAccess
from ....interfaces.selenium import By, Is
import logging
import time
from itertools import izip
from f5test.utils.wait import wait, WaitTimedOut
from selenium.common.exceptions import (NoSuchElementException,
                                        StaleElementReferenceException,
                                        ElementNotVisibleException)
from f5test.commands.ui.uiutils import (webel_grab, webel_click,
                                        wait_for_text_in_webel as wait_ftw)
from f5test.interfaces.selenium import ActionChains

LOG = logging.getLogger(__name__)


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
                 port=None, proto='https', timeout=15, ver=None, *args, **kwargs):
        super(Login, self).__init__(*args, **kwargs)
        self.timeout = timeout
        self.proto = proto
        self.path = '/ui/login/'
        if device or not address:
            self.device = device if isinstance(device, DeviceAccess) else ConfigInterface().get_device(device)
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
        self.ver = ver

    def setup(self):
        b = self.api

        # Set the api login data
        self.ifc.set_credentials(device=self.device, address=self.address,
                                 username=self.username, password=self.password,
                                 port=self.port, proto=self.proto)
        if not self.ver:
            self.ver = self.ifc.version

        url = "{0[proto]}://{0[address]}:{0[port]}{0[path]}".format(self.__dict__)
        b.get(url)
        # The login page might be outdated (from an old version)
        b.refresh().wait('username', timeout=self.timeout)

        e = b.find_element_by_name("username")
        e.click()
        e.send_keys(self.username)

        e = b.find_element_by_id("passwd")
        e.send_keys(self.password)
        if self.ver >= 'bigiq 4.1':
            e.submit().wait('navMenu', timeout=self.timeout)
        elif self.ifc.version < 'bigiq 4.1':
            e.submit().wait('loginDiv', timeout=self.timeout)

        b.maximize_window()


navigate = None
class Navigate(SeleniumCommand):  # @IgnorePep8
    """Navigate to another BIGIQ module.

    @param module: The navMenu path (e.g. Cloud, System|Users)
    @type module: str
    @return: The navLink element
    """
    def __init__(self, module=None, timeout=15, *args, **kwargs):
        super(Navigate, self).__init__(*args, **kwargs)
        self.module = module
        self.timeout = timeout
        self.ver = self.ifc.version

    def setup(self):
        b = self.api
        LOG.info("Navigate to [{0}]...".format(self.module))
        bits = self.module.split('|')
        if self.ver >= 'bigiq 4.5':
            navmenu_xpath = "//div[@id='navMenu']"
            link_xpath = "%s/ul//li/a[text()='%s']" % (navmenu_xpath, bits[0])
            wait_xpath = "%s//div[@id='navMenuCurrentLink' and text()='%s']" % (navmenu_xpath, bits[0])
            e = b.wait(link_xpath, By.XPATH, it=Is.PRESENT, timeout=self.timeout)
            # Click on Product
            e.jquery_click()
            if len(bits) > 1:
                tail = "//a[text()='%s']" % bits[1]
                link_xpath = "%s/div[@id='navMenuSublinks']%s" % (navmenu_xpath, tail)
                tail2 = '//*[contains(concat(" ", normalize-space(@class), " ")," active ")][contains(., "%s")]' % bits[1]
                wait_xpath = "%s/div[@id='navMenuSublinks']%s" % (navmenu_xpath, tail2)
                e = b.wait(link_xpath, By.XPATH, it=Is.PRESENT, timeout=self.timeout)
                e.jquery_click()
                if len(bits) == 3:
                    b.wait(wait_xpath, By.XPATH, timeout=self.timeout)
                    if bits[1] in ['Web Application Security']:
                        tail = tail + '//a[text()="%s"]' % bits[2]
                        link_xpath = "%s/div[@id='navMenuSublinks']%s" % (navmenu_xpath, tail)
                        tail2 = tail + '[contains(concat(" ", normalize-space(@class), " ")," active ")]'
                        wait_xpath = "%s/div[@id='navMenuSublinks']%s" % (navmenu_xpath, tail2)
                        e = b.wait(link_xpath, By.XPATH, it=Is.PRESENT, timeout=self.timeout)
                        e.jquery_click()
                    else:
                        tail = '//div[a[text()="{0}"]][div[a[text()="{1}"]]]//a[text()="{1}"]'.format(bits[1], bits[2])
                        link_xpath = "%s/div[@id='navMenuSublinks']%s" % (navmenu_xpath, tail)
                        tail2 = ''
                        if bits[1] in ["Network Security"] and bits[2] in ["Audit Log", "Reporting", ]:
                            tail = "//a[text()='%s']//a[text()='%s']" % (bits[1], bits[2])
                            tail2 = tail + '[contains(concat(" ", normalize-space(@class), " ")," active ")]'
                        else:
                            tail2 = '//div[a[text()="{0}"]][div[a[text()="{1}"]]]//*[contains(concat(" ", normalize-space(@class), " ")," active ")][contains(., "{1}")]'.format(bits[1], bits[2])
                        wait_xpath = "%s/div[@id='navMenuSublinks']%s" % (navmenu_xpath, tail2)

                        e = b.wait(link_xpath, By.XPATH, it=Is.PRESENT, timeout=self.timeout)
                        e.jquery_click()
        elif self.ver >= 'bigiq 4.4' and self.ver < 'bigiq 4.5':
            navmenu_xpath = "//div[@id='navMenu']"
            if len(bits) > 1:
                link_xpath = "%s/ul//li/a[text()='%s']" % (navmenu_xpath, bits[0])
                wait_xpath = "%s//div[@id='navMenuCurrentLink' and text()='%s']" % (navmenu_xpath, bits[0])
                e = b.wait(link_xpath, By.XPATH, it=Is.PRESENT, timeout=self.timeout)
                # Click on Module
                e.jquery_click()
                # artifice until angular is in place for all modules
                if bits[1] != 'Network Security':
                    tail = ''
                    tail2 = ''
                    for i in range(1, len(bits)):
                        tail = tail + "//a[text()='%s']" % bits[i]
                        link_xpath = "%s/div[@id='navMenuSublinks']%s" % (navmenu_xpath, tail)
                        tail2 = tail2 + '//*[contains(concat(" ", normalize-space(@class), " ")," active ")][contains(., "%s")]' % bits[i]
                        wait_xpath = "%s/div[@id='navMenuSublinks']%s" % (navmenu_xpath, tail2)
                        e = b.wait(link_xpath, By.XPATH, it=Is.PRESENT, timeout=self.timeout)
                        e.jquery_click()
                else:
                    tail = "//a[text()='%s']" % bits[-1]
                    link_xpath = "%s/div[@id='navMenuSublinks']%s" % (navmenu_xpath, tail)
                    tail2 = '//*[contains(concat(" ", normalize-space(@class), " ")," active ")][contains(., "%s")]' % bits[-1]
                    wait_xpath = "%s/div[@id='navMenuSublinks']%s" % (navmenu_xpath, tail2)
                    e = b.wait(link_xpath, By.XPATH, it=Is.PRESENT, timeout=self.timeout)
                    e.jquery_click()
            else:
                link_xpath = "%s/ul//li/a[text()='%s']" % (navmenu_xpath, bits[0])
                wait_xpath = "%s//div[@id='navMenuCurrentLink'][contains(., '%s')]" % (navmenu_xpath, bits[0])
                e = b.wait(link_xpath, By.XPATH, it=Is.PRESENT, timeout=self.timeout)
                e.jquery_click()
        elif self.ver >= 'bigiq 4.2' and self.ver < 'bigiq 4.4':
            if bits[0] == 'System':
                navmenu_xpath = "//div[@id='systemMenu']"
                if len(bits) > 1:
                    link_xpath = "%s/div/a[text()='%s']" % (navmenu_xpath, bits[1])
                    wait_xpath = "%s/div/a[contains(@class, 'active') and text()='%s']" % (navmenu_xpath, bits[1])
                else:
                    link_xpath = "%s/a[text()='%s']" % (navmenu_xpath, bits[0])
                    wait_xpath = "%s/a[contains(@class, 'active') and text()='%s']" % (navmenu_xpath, bits[0])
            else:
                navmenu_xpath = "//div[@id='navMenu']"
                if len(bits) > 1:
                    link_xpath = "%s/ul/li/a[text()='%s']" % (navmenu_xpath, bits[0])
                    wait_xpath = "%s//div[@id='navMenuCurrentLink' and text()='%s']" % (navmenu_xpath, bits[0])
                    e = b.wait(link_xpath, By.XPATH, it=Is.PRESENT, timeout=self.timeout)
                    e.jquery_click()
                    tail = ''.join(map(lambda x: "//a[text()='%s']" % x, bits[1:]))
                    link_xpath = "%s/div[@id='navMenuSublinks']%s" % (navmenu_xpath, tail)
                    tail = ''.join(map(lambda x: "//a[contains(@class, 'active') and text()='%s']" % x, bits[1:]))
                    wait_xpath = "%s/div[@id='navMenuSublinks']%s" % (navmenu_xpath, tail)
                else:
                    link_xpath = "%s/ul/li/a[text()='%s']" % (navmenu_xpath, bits[0])
                    wait_xpath = "%s//div[@id='navMenuCurrentLink' and text()='%s']" % (navmenu_xpath, bits[0])
            e = b.wait(link_xpath, By.XPATH, it=Is.PRESENT, timeout=self.timeout)
            e.jquery_click()
        else:  # bigiq 4.1/4.0
            navmenu_xpath = "//div[@id='navMenu']/div[descendant::div[text()='%s']]" % bits[0]
            if len(bits) > 1:
                link_xpath = "%s/div/a[text()='%s']" % (navmenu_xpath, bits[1])
                wait_xpath = "%s/div/a[contains(@class, 'current') and text()='%s']" % (navmenu_xpath, bits[1])
            else:
                link_xpath = "%s/a/div[@class='navLinkText']" % navmenu_xpath
                wait_xpath = "//div[@id='navMenu']/div[contains(@class, 'current')]/a/div[text()='%s']" % bits[0]
            e = b.wait(link_xpath, By.XPATH, it=Is.PRESENT, timeout=self.timeout)
            e.jquery_click()

        b = b.wait(wait_xpath, By.XPATH, timeout=self.timeout)
        # wait for all blades for some angular UI:
        waitforspinners = True
        waitforspinners_x = '//*[contains(concat(normalize-space(@class), " "),"spinner ") and not(contains(concat(" ", @class, " "), " cell-spinner ")) and not(contains(concat(" ", @class, " "), " security-spinner ")) and not(contains(concat(" ", @class, " "), " loading-spinner "))]'
        if len(webel_grab(xpath=waitforspinners_x, ifc=self.ifc)) == 0:
            waitforspinners = False
        if waitforspinners:
            self.api.wait(waitforspinners_x, By.XPATH, negated=True, timeout=60)
            wait_ftw(text='ng-hide',
                     xpath=waitforspinners_x,
                     textineach=True,
                     attr=['class'],  # prop=["is_displayed"],
                     ifc=self.ifc, timeout=60,
                     usedin='Navigate[{0}]/WaitForSpinners'.format(self.module))

        popup_error_check(negative=True, ifc=self.ifc, ver=self.ver)
        return b


logout = None
class Logout(SeleniumCommand):  # @IgnorePep8
    """Log out from UI. Requires that someone is logged in already.

    @param timeout: default timeout to wait for this action.
    @type timeout: int
    @param jclick: default True: Use a javascript click (for not displayed els)
    @type jclick: bool
    """
    def __init__(self, timeout=20, jclick=True, *args, **kwargs):
        super(Logout, self).__init__(*args, **kwargs)
        self.timeout = timeout
        self.jclick = jclick
        # self.user_d = "userName"
        self.logout_link_d = "logOutLink"
        self.logo_d = "logo"

    def setup(self):
        LOG.info("Logging out of UI...")
        s = self.api

        # also accounting for some weird refresh while performing this:
        def do_log_out():
            bee = True
            # Is it already logged out?
            try:
                s.find_element_by_id(self.logo_d)
            except (ElementNotVisibleException, NoSuchElementException):
                bee = False
                try:
                    # s.wait(self.user_d)
                    # current_user = s.find_element_by_id(self.user_d)
                    # ActionChains(s).move_to_element(current_user).perform()
                    # s.wait(self.logout_link_d)
                    btn = s.find_element_by_id(self.logout_link_d)
                    # sometimes element is found before it can be clicked.
                    time.sleep(1)
                    if not self.jclick:
                        btn.click()
                    else:
                        s.execute_script("return arguments[0].click()", btn)
                except (ElementNotVisibleException, NoSuchElementException):
                    bee = False
            return bee
        wait(do_log_out, interval=1, timeout=self.timeout)
        return s.wait(self.logo_d, timeout=self.timeout)


def wait_for_brush_to_disappear(blade, ifc=None, timeout=20,
                                usedin=None, ver=None, interval=1):
    """Function waits for all blade spinners to disappear
    """
    if not ifc:
        raise NoSuchElementException(msg="/wait_for_brush_to_disappear/ifc parameter - mandatory")
    if not ver:
        ver = ifc.version
    usedin = "{0}[{1}]".format(usedin + "/wait_for_brush_to_disappear/" if usedin else "/wait_for_brush_to_disappear/",
                               blade)
    if blade is not None:
        if ver >= 'bigiq 4.4':
            xpath = '//panel[@id="{0}"]//*[contains(concat(" ", normalize-space(@class), " "),"spinner ")]'.format(blade)
            ifc.api.wait(xpath, By.XPATH, negated=True, timeout=timeout, interval=interval)
            wait_ftw(text='ng-hide', xpath=xpath, textineach=True,
                     attr=['class'],  # prop=["is_displayed"],
                     ifc=ifc, timeout=timeout, usedin=usedin)
            # ifc.api.wait(xpath, By.XPATH, negated=True, timeout=timeout, interval=interval)
        else:  # ver < 4.4
            xpath = '//*[@id="{0}_panel"]/div[1]/div[1]/span'.format(blade)
            # angular: //*[@id="tenants"]/div[3]/div[1]/span[2]
            # angular class: spinner ng-isolate-scope ng-hide
            # toggle: class: spinner ng-isolate-scope ng-show
            wait_ftw(text='display: inline-block', xpath=xpath,
                     attr=['style'], negated=True, ifc=ifc, timeout=timeout,
                     usedin=usedin)

    else:
        raise NoSuchElementException(msg="/wait_for_brush_to_disappear/Blade Name is mandatory and needs to be a string")


popup_error_check = None
class PopupErrorCheck(SeleniumCommand):  # @IgnorePep8
    """Checks for popup errors using a list of xpaths

    @param negative: default False (expects to find an error), set True for negative
    @type negative: negative
    @param xpathlist: a list of xpaths to wait for, if not the default.
    @type xpathlist: list of strings
    @param timeout: default timeout to wait for this action.
    @type timeout: int

    @return: The (first) error element (dialog) if there [else the selenium ifc api]
    """
    def __init__(self, xpathlist=None, negative=False, timeout=14,
                 ver=None,
                 *args, **kwargs):
        super(PopupErrorCheck, self).__init__(*args, **kwargs)
        self.timeout = timeout
        if not ver:
            ver = self.ifc.version
        self.ver = ver
        if not xpathlist:
            if self.ver >= "bigiq 4.4":
                xpathlist = ['//*[@id="errorDialog"][contains(@show, "true")]',
                             ]
            else:  # all versions prior ro 4.4
                xpathlist = ['/html/body/div[3][contains(concat(" ", normalize-space(@class), " ")," error-dialog ")]',
                             ]
        self.xpathlist = xpathlist
        self.negative = negative

    def setup(self):
        LOG.debug("/PopupErrorCheck/Check for error popups...")
        s = self.api
        foundone = False
        for xpath in self.xpathlist:
            if not foundone:
                s.wait(xpath, By.XPATH, negated=self.negative,
                       interval=4,
                       timeout=self.timeout)
                if not self.negative:
                    s = s.find_element_by_xpath(xpath)
                    LOG.info("/PopupErrorCheck/Error dialog found on xpath '{0}'".format(xpath))
                    foundone = True
        LOG.debug("/PopupErrorCheck/Done check for popup errors...")
        return s


see_blade = None
class SeeBlade(SeleniumCommand):  # @IgnorePep8
    """Brings a Blade into view.

    @param blade: The panel id (example: "devices")
    @type blade: str

    Optional parameters:
    @param jclick: True by default, using forced javascript click on blade
    @type jclick: bool
    @param timeout: how long to wait for that xpath
    @type timeout: int
    @param ver: None. bq version. Ex: 'bigiq 4.3'.
                Defaults to None and ver is determined automatically.
    @type ver: string

    @return: The Selenium object on that blade.
    """
    def __init__(self, blade,
                 waitforxpath=None,
                 jclick=True,
                 timeout=20,
                 ver=None,
                 *args, **kwargs):
        super(SeeBlade, self).__init__(*args, **kwargs)
        if blade:
            self.blade = blade
        else:
            LOG.error("Blade Name is mandatory and needs to be a string")
            raise NoSuchElementException(msg="/see_blade/Blade Name is mandatory and needs to be a string.")
        if not ver:
            ver = self.ifc.version
        self.ver = ver
        self.jclick = jclick
        self.timeout = timeout
        self.stabilize = 1
        if self.ver >= 'bigiq 4.4':
            self.blade_x = '//*[(@id="{0}") and not(@type)]'.format(self.blade)
            self.waitfor_c = '#{0} .panelLabelText'.format(self.blade)
        else:  # bigiq 4.3 and lower
            self.blade_docked_c = '#{0}_blade .bladeHeader'.format(self.blade)
            self.blade_x = '//*[@id="{0}_blade"]'.format(self.blade)
            self.waitfor_c = '#{0}.innerContainer'.format(self.blade)

    def setup(self):
        s = self.api
        LOG.debug("Try to See Blade '{0}'".format(self.blade))
        if self.ver >= "bigiq 4.4":
            s.wait(self.blade_x, By.XPATH, timeout=self.timeout)
            dockedblade = s.find_element_by_xpath(self.blade_x)
        else:
            s.wait(self.blade_docked_c, By.CSS_SELECTOR, timeout=self.timeout)
            dockedblade = s.find_element_by_css_selector(self.blade_docked_c)

        if not self.jclick:
            dockedblade.click()
        else:
            s.execute_script("return arguments[0].click()", dockedblade)
        # regain
        blade = s.find_element_by_xpath(self.blade_x)
        if self.ver >= "bigiq 4.4":
            pass
        else:  # vor old versions: and click again
            s.execute_script("return arguments[0].click()", blade)

        blade.wait(self.waitfor_c, By.CSS_SELECTOR, stabilize=self.stabilize)
        # wait for the brush to go away if there.
        wait_for_brush_to_disappear(self.blade, ifc=self.ifc, timeout=self.timeout,
                                    ver=self.ver, usedin="/see_blade")
        # popup_error_check(negative=True, ifc=self.ifc, ver=self.ver)
        return blade


expand_blade = None
class ExpandBlade(SeleniumCommand):  # @IgnorePep8
    """Expand and use a blade (new item on that blade) with the ability
        to wait for an element, give the blade top id

    @param blade: The ID of the blade (or name if older versions)
                    (example: "devices" as from devices_blade)
    @type blade: str

    Optional parameters:
    @param group: For a blade with groups. Give the group name
    @type group: str
    @param use_this_x_button, use_this_d_button: an xpath or an ID to expand on
    @type use_this_x_button, use_this_d_button: str
    @param use_this_c_button: css to expand on (if not the default)
    @type timeout: str
    @param visible: True by default to also see_blade first (if blade is docked)
    @type timeout: boolean
    @param ver: None. bq version. Ex: 'bigiq 4.3'.
                Defaults to None and ver is determined automatically.
    @type ver: string

    @return: The Selenium object on that blade.
    """
    def __init__(self, blade, menutext=None, visible=True,
                 use_this_x_button=None, use_this_c_button=None, use_this_d_button=None,
                 group=None,
                 ver=None, timeout=20,
                 *args, **kwargs):
        super(ExpandBlade, self).__init__(*args, **kwargs)
        if blade:
            self.blade = blade
        else:
            raise NoSuchElementException(msg="/expand_blade/Blade Id is mandatory and needs to be a string.")
        if not ver:
            ver = self.ifc.version
        self.ver = ver
        self.visible = visible
        self.use_this_x_button = use_this_x_button
        self.use_this_d_button = use_this_d_button
        self.group = group
        if self.ver >= 'bigiq 4.4':  # used with angular (BQ>=4.4) by default:
            self.menu_x = '//panel[@id="{0}"]/div/div[contains(@class, "panelHeader")]/span[contains(@class, "addBtn")]/ul[contains(@class, "dropdown-menu")]'.format(self.blade)
            if menutext:
                # choose the default link.
                self.menu_item_x = '{0}/li/a[contains(.,"{1}")]'.format(self.menu_x, menutext)
            else:
                self.menu_item_x = '{0}/li/a[contains(@class,"fntSemibold")]'.format(self.menu_x)
            self.blade_top_css_c = '#{0} .panelHeader'.format(self.blade)
            if not use_this_c_button:
                use_this_c_button = '#{0} .panelAddButton'.format(self.blade)
            self.blade_x = '//panel[@id="{0}"]'.format(self.blade)
            self.waitfor_c = "#{0} .panelSubHeader".format(self.blade)
            self.stabilize = 0
            self.fly_innercontainer_x = '//panel[@id="{0}"]/flyout/div[contains(@class, "innerContainer")]/*'.format(self.blade)
        else:  # version  < 'bigiq 4.4':
            self.blade_top_css_c = '#{0}_blade .bladeHeader'.format(self.blade)
            if not use_this_c_button:
                use_this_c_button = '#{0}_blade .bladeAddButton'.format(self.blade)
            self.blade_x = '//*[@id="{0}_blade"]'.format(self.blade)
            self.waitfor_c = "#{0}_blade .bladeSub".format(self.blade)
            self.stabilize = 1

        self.use_this_c_button = use_this_c_button
        self.menutext = menutext
        self.timeout = timeout

    def setup(self):
        s = self.api
        LOG.info("ExpandBlade/{0}{1}/ ...".format(self.blade,
                                                  "/" + self.menutext if self.menutext else "/DefaultNew"))
        if self.visible:
            blade = see_blade(blade=self.blade, ifc=self.ifc, ver=self.ver, timeout=self.timeout)
        else:
            blade = s.find_element_by_xpath(self.blade_x)
        LOG.debug("ExpandBlade/Fetched the blade. Now expanding for new element...")
        if self.ver >= "bigiq 4.6":
            ie_r = webel_grab(xpath=self.fly_innercontainer_x, ifc=self.ifc)
            if ie_r == []:
                the_plus_class = webel_grab(xpath=self.use_this_x_button,
                                            css=self.use_this_c_button,
                                            did=self.use_this_d_button,
                                            attr=["class"],
                                            ifc=self.ifc)[0]["class"]
                webel_click(xpath=self.use_this_x_button,
                            css=self.use_this_c_button,
                            did=self.use_this_d_button,
                            jsclick=True, ifc=self.ifc)
                if (self.menutext) or ("single" not in the_plus_class and "multiple" in the_plus_class):
                    webel_click(xpath=self.menu_item_x, jsclick=True, ifc=self.ifc)
            else:
                LOG.info("ExpandBlade/{0}/Found Blade already expanded. No action!".format(self.blade))
        elif self.ver >= "bigiq 4.4" and self.ver < "bigiq 4.6":
            ie_r = webel_grab(xpath=self.fly_innercontainer_x, ifc=self.ifc)
            if ie_r == []:
                webel_click(xpath=self.use_this_x_button,
                            css=self.use_this_c_button,
                            did=self.use_this_d_button,
                            jsclick=True, ifc=self.ifc)
                webel_click(xpath=self.menu_item_x, jsclick=True, ifc=self.ifc)
            else:
                LOG.info("ExpandBlade/{0}/Found Blade already expanded. No action!".format(self.blade))
        else:  # for all prior to bq 4.4 versions
            if self.use_this_x_button is not None:
                newitembtn = blade.find_element_by_xpath(self.use_this_x_button)
            elif self.use_this_d_button is not None:
                newitembtn = blade.find_element_by_id(self.use_this_d_button)
            else:
                newitembtn = blade.find_element_by_css_selector(self.use_this_c_button)
            s.execute_script("return arguments[0].click()", newitembtn)
        blade.wait(self.waitfor_c, By.CSS_SELECTOR, stabilize=self.stabilize)
        wait_for_brush_to_disappear(self.blade, ifc=self.ifc, ver=self.ver,
                                    usedin="ExpandBlade", timeout=self.timeout)
        popup_error_check(negative=True, ifc=self.ifc, ver=self.ver)
        return blade


expand_group = None
class ExpandGroup(SeleniumCommand):  # @IgnorePep8
    """Expand a group on a blade

    @param blade: The ID of the blade (or name if older versions)
                    (example: "devices" as from devices_blade)
    @type blade: str
    @param group: The group name
    @type group: str

    Optional parameters:

    @param visible: True by default to also see_blade first (if blade is docked)
    @type visible: boolean
    @param ver: None. bq version. Ex: 'bigiq 4.3'.
                Defaults to None and ver is determined automatically.
    @type ver: string

    @return: The Selenium object on that blade.
    """
    def __init__(self, blade, group, directions=None, menutext=None,
                 visible=True,
                 ver=None,
                 usedin=None, timeout=15,
                 *args, **kwargs):
        super(ExpandGroup, self).__init__(*args, **kwargs)
        if blade:
            self.blade = blade
        else:
            LOG.error("Blade Id is mandatory and needs to be a string.")
            raise NoSuchElementException(msg="/expand_group/Blade Id is mandatory and needs to be a string.")
        if blade:
            self.group = group
        else:
            LOG.error("Group Name is mandatory and needs to be a string.")
            raise NoSuchElementException(msg="/expand_group/Group Name is mandatory and needs to be a string.")
        if not ver:
            ver = self.ifc.version
        if not directions:
            directions = ["right", "down"]
        self.directions = directions
        self.ver = ver
        self.visible = visible
        self.usedin = "{0}ExpandGroup/{1}/{2}/{3}/".format(usedin + "/" if usedin else "",
                                                           self.blade, self.directions,
                                                           menutext if menutext else "DefaultNew")

        if self.ver >= 'bigiq 4.6':  # used with angular (BQ>=4.4) by default:
            # self.menu_x = '//panel[@id="{0}"]/div/div[contains(@class, "panelHeader")]/span[contains(@class, "addBtn")]/ul[contains(@class, "dropdown-menu")]'.format(self.blade)
            self.menu_x = '//panel[@id="{0}"]/div/panel-group-dropdown//span[contains(@class, "groupHeader")]/ul[contains(@class, "dropdown-menu")]'.format(self.blade)
            if menutext:
                # choose the default link.
                self.menu_item_x = '{0}/li/a[contains(.,"{1}")]'.format(self.menu_x, menutext)
            else:
                self.menu_item_x = '{0}/li/a[contains(@class,"fntSemibold")]'.format(self.menu_x)
            self.blade_x = '//panel[@id="{0}"]'.format(self.blade)
            self.fly_innercontainer_x = '//panel[@id="{0}"]/flyout/div[contains(@class, "innerContainer")]/*'.format(self.blade)
            self.panelbase = '//panel[@id="{0}"]/div[contains(@class,"panelMain")]/div[contains(@class,"innerContainer")]'.format(self.blade)
            self.thisgroup_x = '{0}//li/div[a[contains(., "{1}")]]'.format(self.panelbase, self.group)
            self.thisgroup_div_x = '{0}//li[div/a[contains(., "{1}")]]/div[contains(@class, "treePanelItems")]'.format(self.panelbase, self.group)
            self.group_link_x = '{0}//a[contains(., "{1}")]'.format(self.panelbase, self.group)
            self.icon_down_x = '{0}/a[contains(@class, "expandIconWrapper")]'.format(self.thisgroup_x)
            self.icon_down_span_x = '{0}/a[contains(@class, "expandIconWrapper")]/span'.format(self.thisgroup_x)
            self.icon_right_x = '{0}//div[contains(@class,"sprite propertiesIcon")]'.format(self.thisgroup_x)
            self.highlight_c = "highlight"
            self.carrot_down_expanded_c = "carrot-down-light-gray"
            self.carrot_down_retracted_c = "carrot-up-light-gray"
        elif self.ver >= 'bigiq 4.4':  # used with angular (BQ>=4.4) by default:
            # self.menu_x = '//panel[@id="{0}"]/div/div[contains(@class, "panelHeader")]/span[contains(@class, "addBtn")]/ul[contains(@class, "dropdown-menu")]'.format(self.blade)
            self.menu_x = '//panel[@id="{0}"]/div/panel-group-dropdown//span[contains(@class, "groupHeader")]/ul[contains(@class, "dropdown-menu")]'.format(self.blade)
            if menutext:
                # choose the default link.
                self.menu_item_x = '{0}/li/a[contains(.,"{1}")]'.format(self.menu_x, menutext)
            else:
                self.menu_item_x = '{0}/li/a[contains(@class,"fntSemibold")]'.format(self.menu_x)
            self.blade_x = '//panel[@id="{0}"]'.format(self.blade)
            self.fly_innercontainer_x = '//panel[@id="{0}"]/flyout/div[contains(@class, "innerContainer")]/*'.format(self.blade)
            self.panelbase = '//panel[@id="{0}"]/div[contains(@class,"panelMain")]/div[contains(@class,"innerContainer")]' \
                             .format(self.blade)
            self.thisgroup_x = '{0}//li[contains(., "{1}")]'.format(self.panelbase, self.group)
            self.thisgroup_div_x = '{0}//li[contains(., "{1}")]/div'.format(self.panelbase, self.group)
            self.group_link_x = '{0}//a[contains(., "{1}")]'.format(self.thisgroup_x, self.group)
            self.icon_down_x = '{0}//div/a[contains(@class,"expandIconWrapper")]/span'.format(self.thisgroup_x)
            self.icon_down_span_x = '{0}//div/a[contains(@class,"expandIconWrapper")]/span'.format(self.thisgroup_x)
            self.icon_right_x = '{0}//div[contains(@class,"sprite propertiesIcon")]'.format(self.thisgroup_x)
            self.highlight_c = "highlight"
            self.carrot_down_expanded_c = "carrot-down-light-gray"
            self.carrot_down_retracted_c = "carrot-down-up-gray"
        else:  # version  < 'bigiq 4.4':
            LOG.error("Expand Group Method not supported for this version.")
            raise NoSuchElementException(msg="/expand_group/Expand Group Method not supported for this version.")
        self.menutext = menutext
        self.timeout = timeout

    def setup(self):
        s = self.api
        LOG.info("{0}...".format(self.usedin))
        if self.visible:
            blade = see_blade(blade=self.blade, ifc=self.ifc, ver=self.ver)
        else:
            blade = s.find_element_by_xpath(self.blade_x)
        LOG.debug("{0}Fetched the blade. Now expanding group...".format(self.usedin))
        # find group
        s.wait(self.group_link_x, By.XPATH)
        group_el = s.find_element_by_xpath(self.group_link_x)

        # expand right
        if "right" in self.directions:
            # is blade expanded to the right?
            ie_r = webel_grab(xpath=self.fly_innercontainer_x, ifc=self.ifc)
            if ie_r == []:
                action = ActionChains(self.api)
                # double click to expand if nothing was given as a menu item
                if not self.menutext:
                    action.double_click(group_el)
                    action.perform()
                    # alterantivelly, one can use the same method of expansion on the default menu item:
                    # action.move_to_element(group_el)
                    # action.perform()
                    # webel_click(xpath=self.icon_right_x, jsclick=True, ifc=self.ifc)
                    # webel_click(xpath=self.menu_item_x, jsclick=True, ifc=self.ifc)
                # or press the exact menu expansion
                else:
                    action.move_to_element(group_el)
                    action.perform()
                    webel_click(xpath=self.icon_right_x, jsclick=True, ifc=self.ifc)
                    webel_click(xpath=self.menu_item_x, jsclick=True, ifc=self.ifc)
            else:
                # make sure the expansion is of this group and not something else
                # is element highlighted?
                el_class = webel_grab(xpath=self.thisgroup_div_x, attr=["class"],
                                      ifc=self.ifc)
                if self.highlight_c not in el_class[0].get("class"):
                    group_el.click()
                    LOG.info("{0}Click Group, blade already expanded right.".format(self.usedin))
                else:
                    LOG.info("{0}Found Group already expanded right.".format(self.usedin))
            s.wait(self.fly_innercontainer_x, By.XPATH)
        # expand down
        if "down" in self.directions:
            is_expanded = None
            iec = webel_grab(xpath=self.icon_down_span_x, attr=["class"], ifc=self.ifc)
            if iec:
                if self.carrot_down_retracted_c in iec[0].get('class'):
                    is_expanded = False
                elif self.carrot_down_expanded_c in iec[0].get('class'):
                    is_expanded = True
            if is_expanded is False:
                webel_click(xpath=self.icon_down_x, ifc=self.ifc)
                # no way of knowing  if there is any el in this group to wait for
                time.sleep(1)
                # wait for spinners
                wait_for_brush_to_disappear(self.blade, ifc=self.ifc, ver=self.ver,
                                            usedin="ExpandGroup", timeout=self.timeout)
                # no way of knowing  if there is any el in this group to wait for
                time.sleep(1)
            elif is_expanded is True:
                LOG.info("{0}Found Group already expanded down.".format(self.usedin))
            else:
                raise NoSuchElementException(msg="/expand_group/error.")
        wait_for_brush_to_disappear(self.blade, ifc=self.ifc, ver=self.ver,
                                    usedin="ExpandGroup", timeout=self.timeout)
        popup_error_check(negative=True, ifc=self.ifc, ver=self.ver)
        return blade


count_on_blade = None
class CountOnBlade(SeleniumCommand):  # @IgnorePep8
    """Return the Number of cells on a blade (or whtihin a group on a blade)

    @param blade: The panel id of the blade (example: "device" as from Devices blade)
    @type blade: str

    Optional parameters:

    @param group: For a blade with a Group, give the Group Name (EXACT TEXT).
                 It will count items inside that group. EG: "Firewall Group"
    @type group: str

    @param visible: True by default to also see_blade first (if blade is docked)
    @type visible: bool
    @param ui_inner_cell_height: Defaults to None.Version specific, can be enforced.
                                 Exact style value for 2nd EL from Top of Blade.
    @type ui_inner_cell_height: int
    @param ver: None. bq version. Ex: 'bigiq 4.3'.(Use to force a version)
                Defaults to None and ver is determined automatically.
    @type ver: string

    @return: The Number of cells found on the blade
    """
    def __init__(self, blade, group=None, visible=True,
                 ui_inner_cell_height=None,
                 ver=None, timeout=15, usedin=None,
                 *args, **kwargs):
        super(CountOnBlade, self).__init__(*args, **kwargs)
        if blade:
            self.blade = blade
        else:
            raise NoSuchElementException(msg="/count_on_blade/Blade ID is mandatory and needs to be a string.")
        if not ver:
            ver = self.ifc.version
        self.ver = ver
        self.visible = visible
        self.group = group
        # //*[@id="device"]/div[4]/div[3]/div/ul/div/li/div[1]/a
        self.usedin = "{0}CountOnBlade/{1}{2}{3}/".format(usedin + "/" if usedin else "",
                                                          self.blade, ">" if self.group else "",
                                                          self.group if self.group else "",)

        if self.ver >= 'bigiq 4.4':
            self.panelbase = '//panel[@id="{0}"]/div[contains(@class,"panelMain")]/div[contains(@class,"innerContainer")]' \
                             .format(self.blade)
            if self.group:
                self.all_els_x = self.panelbase + \
                    '//li[contains(., "{0}")]/div[2]/ul/li[*]/div'.format(self.group)
            else:
                self.all_els_x = self.panelbase + \
                    '//div[contains(@class,"panelListContainer")]/ul/li[*]'
            if not ui_inner_cell_height:
                ui_inner_cell_height = 47
        else:  # all versions prior to 4.4
            self.blade_d = '{0}_blade'.format(self.blade)
            self.bladecont_c = '#{0}.innerContainer'.format(self.blade)
            self.incss = "#{0} .listCell".format(self.blade)
            if not ui_inner_cell_height:
                ui_inner_cell_height = 46
        self.ui_inner_cell_height = ui_inner_cell_height
        self.timeout = timeout

    def setup(self):
        finalcount = 0
        s = self.api

        # failsafe needed in case a blade has no elements: (it will infinite loop otherwise)
        blade = None
        bladeisblank = False
        max_inview_no = 0

        if self.visible:
            blade = see_blade(blade=self.blade, ifc=self.ifc, ver=self.ver)
        else:
            blade = s.find_element_by_id(self.blade_d)

        if self.group:
            expand_group(blade=self.blade, group=self.group,
                         directions=["down"],
                         visible=False,  # already determined state of blade
                         usedin="CountOnBlade",
                         ifc=self.ifc,
                         ver=self.ver)

        if self.ver >= "bigiq 4.4":
            allels = s.find_elements_by_xpath(self.all_els_x)
            max_inview_no = len(allels)
            if max_inview_no == 0:
                LOG.info("{0}No elements found on this blade. Final Count: {1}"
                         .format(self.usedin, finalcount))
                bladeisblank = True
            else:
                LOG.info("{0}Max In View Els at once is: {1}"
                         .format(self.usedin, max_inview_no))
            finalcount = max_inview_no
            if not bladeisblank:
                LOG.debug("{0}Warning: Counted on Blade - But - No Scroll Yet!"
                          .format(self.usedin))
                pass
#                 bladewebel = s.find_element_by_id(self.blade_d)
#                 inner_container = bladewebel.find_element_by_css_selector(self.bladecont_c)
#                 scroll_height = s.execute_script('return arguments[0].scrollHeight',
#                                                       inner_container)
#                 if scroll_height <= 0:
#                     LOG.error("{0}/ScrollHeight was: {1}".format(self.usedin, scroll_height))
#                     raise NoSuchElementException
#                 LOG.debug("{0}Scroll Height found: {1}"
#                              .format(self.usedin, scroll_height))
#                 finalcount = int(scroll_height / self.ui_inner_cell_height)
#                 # if the no of els is smaller than the scroll:
#                 if finalcount > max_inview_no:
#                     finalcount = max_inview_no
        else:  # all versions prior to 4.4
            # Remember Autorefresh and disable it:
            js_no_autorefresh = s.execute_script('return window._debug_disable_autorefresh;')
            if js_no_autorefresh is None:
                js_no_autorefresh = "null"
                # Disable Autorefresh:
                s.execute_script('window._debug_disable_autorefresh=true;')
            elif js_no_autorefresh:
                js_no_autorefresh = "true"
            elif js_no_autorefresh is False:
                js_no_autorefresh = "false"
                # Disable Autorefresh:
                s.execute_script('window._debug_disable_autorefresh=true;')
            allels = blade.find_elements_by_css_selector(self.incss)
            max_inview_no = len(allels)
            if max_inview_no == 0:
                LOG.debug("{0}No elements found on this blade. Final Count: {1}"
                          .format(self.usedin, finalcount))
                bladeisblank = True
            else:
                LOG.debug("{0}Max In View Els at once is: {1}"
                          .format(self.usedin, max_inview_no))
            if not bladeisblank:
                bladewebel = s.find_element_by_id(self.blade_d)
                inner_container = bladewebel.find_element_by_css_selector(self.bladecont_c)
                scroll_height = s.execute_script('return arguments[0].scrollHeight',
                                                 inner_container)
                if scroll_height <= 0:
                    raise NoSuchElementException(msg="{0}/ScrollHeight was: {1}".format(self.usedin, scroll_height))
                LOG.debug("{0}Scroll Height found: {1}".format(self.usedin, scroll_height))
                finalcount = int(scroll_height / self.ui_inner_cell_height)
                # if the no of els is smaller than the scroll:
                if finalcount > max_inview_no:
                    finalcount = max_inview_no

            if js_no_autorefresh != "true":
                s.execute_script('window._debug_disable_autorefresh={0};'
                                 .format(js_no_autorefresh))
                LOG.debug("{0}Returned _debug_disable_autorefresh={1}"
                          .format(self.usedin, js_no_autorefresh))
        wait_for_brush_to_disappear(self.blade, ifc=self.ifc, ver=self.ver,
                                    usedin="/count_on_blade/", timeout=self.timeout)
        popup_error_check(negative=True, ifc=self.ifc, ver=self.ver)
        return finalcount


click_blade_on_text = None
class ClickBladeOnText(SeleniumCommand):  # @IgnorePep8
    """Find the first element that matches a given text (with Scroll on any blade)
        and clicks on it (leaves the blade expanded if already expanded)

    @param blade: The name of the blade (example: "devices" as from devices_blade)
    @type blade: str
    @param text: the text to search on the blade for.
    @type text: str

    Optional parameters:
    @param group: For a blade with groups - the group exact name.
    @type group: str

    @param usedin: Adds this "usedin" string in front of all LOG sent calls
    @type usedin: str
    @param visible: if see_blade should be used first. Defaults on True.
    @type visible: bool
    @param expandit: Defaults to False. If also expand when finding the el.
    @type expandit: bool
    @param expect_none: Defaults to False. Used in Delete Method.
            It will not raise exceptions if the blade is blank or the object is not found.
    @type expect_none: bool
    @param ui_cell_height: Defaults to None. Version Specific. Used in scrolling blade.
    @type ui_cell_height: int
    @param threshold: Defaults to 0 if not explicit.
                        Used on border scroll cases to center the found element
    @type threshold: int
    @param ui_inner_cell_height: Defaults to None (version specific). Can be enforced.
                                 Exact style value for 2nd EL from Top of Blade.
    @type ui_inner_cell_height: int
    @param center_el_on_blade: Default on True. Center element on blade. Border case.
                                Just a bit faster if False, however Drag&Drop needs it,
                                also better True for visibility if fails)
    @type center_el_on_blade: bool
    @param enforce_scroll_only: False by default. DO NOT SET TRUE. Used mainly in
                                delete method, only when verifying blade after the fact
    @type enforce_scroll_only: bool

    @param remember_jsrefresh: Default on False. Does not modify the jsrefresh during test.
                              Used with Drag and Drop.
    @type remember_jsrefresh: bool

    @param ver: None. bq version. Ex: 'bigiq 4.3'.(Use to force a version)
                Defaults to None and ver is determined automatically.
    @type ver: string

    @return: The Selenium object of that blade element on that text.
    """
    def __init__(self, blade, text, group=None,
                 expandit=False,
                 menutext=None,
                 usedin=None, visible=True,
                 expect_none=False,
                 ui_cell_height=None, threshold=None,
                 center_el_on_blade=False,
                 ui_inner_cell_height=None,  # not use if version >= 4.4
                 enforce_scroll_only=False,
                 dontscroll=False,
                 remember_jsrefresh=False,
                 ver=None, timeout=30,
                 *args, **kwargs):
        super(ClickBladeOnText, self).__init__(*args, **kwargs)
        if blade:
            self.blade = blade
        else:
            raise NoSuchElementException(msg="/ClickBladeObj/Blade ID is mandatory and needs to be a string.")
        if (text is not None):
            self.text = text
        else:
            raise NoSuchElementException(msg="/ClickBladeObj/text is mandatory and needs to be a string.")
        if not ver:
            ver = self.ifc.version
        self.ver = ver
        self.group = group

        if threshold is None:
            threshold = 0  # was int(self.CH / 2)
        usedin = "{0}ClickBladeObj/{1}{2}{3}/".format((usedin + "/") if usedin else "",
                                                      self.blade,
                                                      ">" if self.group else "",
                                                      self.group if self.group else "")
        if expandit:  # enforce centering element if trying to expand blade
            center_el_on_blade = True

        if self.ver >= 'bigiq 4.4':
            if not ui_cell_height:
                ui_cell_height = 47
            self.blade_x = '//panel[@id="{0}"]'.format(self.blade)
            self.panelbase = '//panel[@id="{0}"]/div[contains(@class,"panelMain")]/div[contains(@class,"innerContainer")]' \
                             .format(self.blade)
            if self.group:
                self.innercontainer_x = '{0}//li[contains(., "{1}")]//ul' \
                                        .format(self.panelbase, self.group)
                self.all_els_x = '{0}/li[*]/div'.format(self.innercontainer_x)
                self.myel_x = '{0}/li[contains(concat(" ", normalize-space(), " "),"{1}")]/div' \
                              .format(self.innercontainer_x, self.text)
                self.mygear_el_x = '{0}/div[contains(concat(" ", normalize-space(@class), " ")," sprite propertiesIcon ")]' \
                                   .format(self.myel_x)
            else:
                self.innercontainer_x = '{0}//div[contains(@class,"panelListContainer")]' \
                                        .format(self.panelbase)
                self.all_els_x = '{0}/ul/li[*]'.format(self.innercontainer_x)
                self.myel_x = '{0}/ul/li[contains(concat(" ", normalize-space(), " "),"{1}")]' \
                              .format(self.innercontainer_x, self.text)
                self.mygear_el_x = '{0}/ul/li[contains(concat(" ", normalize-space(), " "), "{1}")]/div[contains(concat(" ", normalize-space(@class), " ")," sprite propertiesIcon ")]' \
                                   .format(self.innercontainer_x, self.text)
            self.menu_x = '//panel[@id="{0}"]/div/panel-{1}-dropdown//span[contains(@class, "{2}")]/ul[contains(@class, "dropdown-menu")]' \
                          .format(self.blade, "item", "itemHeader")
            if menutext:
                # choose the default link.
                self.menu_item_x = '{0}/li/a[contains(.,"{1}")]'.format(self.menu_x, menutext)
            else:
                self.menu_item_x = '{0}/li/a[contains(@class,"fntSemibold")]'.format(self.menu_x)
            self.selectedcss_c = "highlight"
            self.fly_header_c = "#{0} .panelSubHeader".format(self.blade)
            self.fly_innercontainer_x = '//panel[@id="{0}"]/flyout/div[contains(@class, "innerContainer")]/*'.format(self.blade)
            self.bladelist_cells_x = '//panel[@id="{0}"]/div/div[contains(@class, "innerContainer")]/panel-list/div[contains(@class, "panelListContainer")]/ul/li[*]'.format(self.blade)
            self.blade_d = self.blade
        elif self.ver < 'bigiq 4.4':
            if not ui_cell_height:
                ui_cell_height = 56
            if not ui_inner_cell_height:
                ui_inner_cell_height = 56
            self.blade_d = '{0}_blade'.format(self.blade)
            self.blade_x = '//div[@id="{0}"]'.format(self.blade_d)
            self.all_els_x = '{0}/div[*]'.format(self.blade_x)
            self.blade_panel_d = '{0}_panel'.format(self.blade)
            self.bladesub_c = self.waitfor_c = "#{0} .bladeSub".format(self.blade_d)
            self.bladesubhead_c = '#{0} .bladeSubHeader'.format(self.blade_d)
            self.bladecont_c = '#{0}.innerContainer'.format(self.blade)
            self.bladelist_cells_x = '//div[@id="{0}"]/div/div[*]'.format(self.blade)
            self.incss = "#{0}_blade .listCell".format(self.blade)
            self.selectedcss_c = "brushSource highlight"
            self.bladelist_gearbtns_x = '{0}//div[contains(concat(" ", normalize-space(@class), " ")," propertiesIcon ")]' \
                                        .format(self.bladelist_cells_x)
            self.ui_inner_cell_height = ui_inner_cell_height

        self.center_el_on_blade = center_el_on_blade
        self.remember_jsrefresh = remember_jsrefresh
        self.threshold = threshold
        self.CH = ui_cell_height
        self.usedin = usedin
        self.visible = visible
        self.expandit = expandit
        self.expect_none = expect_none
        self.enforce_scroll_only = enforce_scroll_only
        self.dontscroll = dontscroll
        self.menutext = menutext
        self.timeout = timeout

    def setup(self):
        s = self.api
        js_no_autorefresh = False
        if not self.remember_jsrefresh and self.ver <= "bigiq 4.3":
            # Remember Autorefresh and disable it:
            js_no_autorefresh = s.execute_script('return window._debug_disable_autorefresh;')
            if js_no_autorefresh is None:
                js_no_autorefresh = "null"
                # Disable Autorefresh:
                s.execute_script('window._debug_disable_autorefresh=true;')
            elif js_no_autorefresh:
                js_no_autorefresh = "true"
            elif js_no_autorefresh is False:
                js_no_autorefresh = "false"
                # Disable Autorefresh:
                s.execute_script('window._debug_disable_autorefresh=true;')

        webel = None

        LOG.debug("{0}'{1}'_Start_ClickBladeOnText...".format(self.usedin, self.text))

        def do_scroll_element_to(element, position, tsleep=1):
            s.execute_script('arguments[0].scrollTop = arguments[1]', element, position)
            # Sleep is to cover the UI animation.
            time.sleep(tsleep)

        blade = None

        if self.visible:
            blade = see_blade(blade=self.blade, ifc=self.ifc, ver=self.ver,
                              timeout=self.timeout)
        else:
            blade = s.find_element_by_id(self.blade_d)

        if self.group:
            expand_group(blade=self.blade, group=self.group,
                         directions=["down"],
                         visible=False,  # already determined state of blade
                         usedin=self.usedin,
                         ifc=self.ifc,
                         ver=self.ver)

        # determine if blade has elements or not
        bladeisblank = False
        allels = webel_grab(xpath=self.all_els_x, prop=["text"], attr=["style"], ifc=self.ifc)
        if len(allels) == 0:
            LOG.info("{0}Elements found: 0. Blank Selection.".format(self.usedin))
            bladeisblank = True

        # determine if blade is expanded or not
        is_expanded = False

        if not bladeisblank:  # if blade is not blank
            if self.ver >= "bigiq 4.4":
                if self.expandit:
                    # Determine if the blade is already expanded (only if needed).
                    # In order to expandit, need to center element
                    iec = webel_grab(xpath=self.fly_innercontainer_x, ifc=self.ifc)
                    if iec != []:
                        is_expanded = True
                    if is_expanded:
                        LOG.info("{0}Found Blade Expanded Already...".format(self.usedin))
                    else:
                        LOG.info("{0}Found Blade Retracted...".format(self.usedin))
                    # finished, now we know if it is expanded

                already_found_and_clicked = False
                # ##################### Optimization ###############################
                if not self.enforce_scroll_only:
                    # LOG.info("{0}Try with NO Scroll first...".format(self.usedin))
                    # See if element was in the current display and calculate position
                    to_position = 0
                    element_found = False
                    for gr in allels:
                        received_text = gr.text
                        if self.text in received_text:
                            if not self.group:
                                toppos = ((gr.style).split(";"))[0]
                                if "top" in toppos:
                                    pos = int(''.join(x for x in toppos if x.isdigit()))
                                else:
                                    LOG.warning("No Pos in styles>In using groups")
                                    pos = self.CH
                                LOG.debug("{0}Style position got: {1}".format(self.usedin, pos))
                                pos = int(pos / self.CH)
                                to_position = pos * self.CH + self.threshold
                            element_found = True
                            LOG.info("{0}Found webel...".format(self.usedin))
                            break
                    if element_found:  # if the element was found on this display
                        try:  # will center the element and regain blade and the element
                            if self.center_el_on_blade and not self.group:
                                inner_container = s.find_element_by_xpath(self.innercontainer_x)
                                LOG.debug("{0}Will scroll to: {1}".format(self.usedin, to_position))
                                do_scroll_element_to(inner_container, to_position)
                                LOG.info("{0}Centered to position '{1}' on blade.(No Scroll)"
                                         .format(self.usedin, to_position))
                                wait_for_brush_to_disappear(self.blade, ifc=self.ifc,
                                                            ver=self.ver, usedin=self.usedin,
                                                            timeout=self.timeout)
                            element_found = False
                            s.wait(self.myel_x, By.XPATH)
                            webel = s.find_element_by_xpath(self.myel_x)
                            element_found = True
                            LOG.info("{0}Gained webel...".format(self.usedin))
                            # check if is not already highlighted and clik it
                            # only if I don't want to expand it or if I want to expand it
                            # and is already expanded
                            if (not self.expandit) or (self.expandit and is_expanded):
                                if (self.selectedcss_c not in webel.get_attribute('class')):
                                    # s.execute_script("return arguments[0].click()", webel)
                                    webel.click()
                                    LOG.info("{0}Clicked directly to show el on "
                                             "'{1}'. (wait to be highlighted)"
                                             .format(self.usedin, self.text))
                                    wait_ftw(xpath=self.myel_x, text=self.selectedcss_c,
                                             attr=["class"], ifc=self.ifc, usedin=self.usedin)
                                else:
                                    LOG.info("{0}Found element clicked and higlighted already:  '{1}'"
                                             .format(self.usedin, self.text))
                            # if want blade to expand on el
                            if self.expandit and not is_expanded:
                                webel = s.find_element_by_xpath(self.myel_x)
                                action = ActionChains(self.api)
                                action.move_to_element(webel)
                                if not self.menutext:
                                    # use double_click
                                    action.double_click(webel)
                                    action.perform()
                                    LOG.info("{0}Double Clicked item to expand el for "
                                             "'{1}'".format(self.usedin, self.text))
                                    # alternative (click default menu item on gear menu):
                                    # action.move_to_element(webel)
                                    # action.perform()
                                    # webel_click(xpath=self.mygear_el_x, jsclick=True,
                                    #            timeout=10,
                                    #            ifc=self.ifc)
                                    # webel_click(xpath=self.menu_item_x, jsclick=True,
                                    #            timeout=10,
                                    #            ifc=self.ifc)
                                    # LOG.info("{0}Clicked Default GEAR/Menu item to expand el for "
                                    #      "'{1}'".format(self.usedin, self.text))
                                else:
                                    # click exact menu item on gear menu:
                                    action.perform()
                                    webel_click(xpath=self.mygear_el_x, jsclick=True,
                                                timeout=10,
                                                ifc=self.ifc)
                                    webel_click(xpath=self.menu_item_x, jsclick=True,
                                                timeout=10,
                                                ifc=self.ifc)
                                    LOG.info("{0}Clicked GEAR/Menu '{2}' item to expand el for "
                                             "'{1}'".format(self.usedin, self.text, self.menutext))
                            already_found_and_clicked = True
                            LOG.debug("{0}Webel after actions: {1}. already_found_and_clicked = {2}"
                                      .format(self.usedin, webel, already_found_and_clicked))
                        except StaleElementReferenceException, e:
                            if already_found_and_clicked:
                                LOG.error("{0}Already found and clicked, but got Stale."
                                          " Moving on...".format(self.usedin))
                                pass  # blade refreshed itself or something
                            elif self.expect_none:
                                pass
                            else:
                                raise StaleElementReferenceException(msg="{0} Got Stale.".format(self.usedin))
                        except NoSuchElementException, e:
                            if already_found_and_clicked:
                                LOG.error("{0}Already found and clicked, but got NoSuch."
                                          "Moving on...".format(self.usedin))
                                pass
                            elif self.expect_none:
                                pass
                            else:
                                raise NoSuchElementException(msg="{0} Got Stale.".format(self.usedin))
#                         except Exception, e:
#                             raise e

#                 ###################### Finished Optimization ######################
#                 # and now with scroll (the hard way):
#                 if not already_found_and_clicked and not self.dontscroll:
#                     LOG.info("{0}Try with Scroll Now...".format(self.usedin))
#                     # Scroll to top ?
#                     # find top (for groups is not the same top)
#                     inner_container = s.find_element_by_xpath(self.innercontainer_x)
#                     if self.group:
#                         # to do
#                         LOG.warning("No Scroll Yet for Groups...")
#                         scroll_height = self.CH
#                         top = 0
#                     else:  # blade with no groups (regular)
#                         scroll_height = s.execute_script('return arguments[0].scrollHeight',
#                                                           inner_container)
#                         top = 0
#                     # always scroll to top before anything
#                     do_scroll_element_to(inner_container, top)
#                     # regain innercontainer after scroll to top:
#                     inner_container = s.find_element_by_xpath(self.innercontainer_x)
#
#                     # calculate max scroll height
#                     max_scroll_height = scroll_height + self.CH
#                     # fail in case we can't get the height
#                     if scroll_height <= 0:
#                         raise NoSuchElementException(msg="{0}/ScrollHeight was: {1}".format(self.usedin, scroll_height))
#
#                     count = int(scroll_height / self.CH)
#
#                     #print count
#
#                     rlist = []
#                     at_least_one_was_found = False
#                     all_texts = []
#                     for pos in range(count):
#                         reach = pos * self.CH
#                         do_scroll_element_to(inner_container, reach)
#                         xpath_row = self.innercontainer_x + \
#                                     '/ul/li[contains(concat(" ", normalize-space(@style), " "),"top: {0}px; ")]'.format(reach)
#                         this_text = webel_grab(xpath=xpath_row, ifc=self.ifc)
#                         this_text[0]["pos"] = reach
#                         all_texts.append(this_text[0])
#
#                     for text in self.text:  # for each text to compare to
#                         dic_per_tag = {"text": text, "pos": []}
#                         cell_count_on_this_text = 0
#                         for cell in all_texts:  # for each element from UI
#                             received_text_cell = cell.get("text")
#                             if text in received_text_cell:
#                                 cell_count_on_this_text += 1
#                                 at_least_one_was_found = True
#                                 dic_per_tag["pos"].append(cell.get("pos"))
#                         dic_per_tag["found"] = cell_count_on_this_text
#                         rlist.append(dic_per_tag)
#                     if at_least_one_was_found:  # if none was found, retun None
#                         returnlist = rlist

            else:  # all prior to 4.4 versions
                # Determine if the blade is already expanded. Look for the Head Text
                wait_for_brush_to_disappear(self.blade, ifc=self.ifc, ver=self.ver,
                                            usedin=self.usedin, timeout=self.timeout)
                is_expanded = True
                headtext = None
                try:
                    vis = webel_grab(xpath=self.all_els_x, prop=["is_displayed"],
                                     ifc=self.ifc)
                    for el in vis:
                        if (not el.get("is_displayed")) and (is_expanded):
                            is_expanded = False
                    headtext = None
                    if is_expanded:
                        blade = s.find_element_by_id(self.blade_d)
                        container = blade.find_element_by_css_selector(self.bladesub_c)
                        headtext = container.find_element_by_css_selector(self.bladesubhead_c)
                    if headtext is None:
                        is_expanded = False
                    else:
                        try:
                            htxt = headtext.text
                            if (htxt == ''):
                                is_expanded = False
                        except AttributeError:
                            is_expanded = False
                except NoSuchElementException:
                    is_expanded = False
                except StaleElementReferenceException:
                    is_expanded = False

                bladewebel = s.find_element_by_id(self.blade_d)
                all_blade_els = bladewebel.find_elements_by_css_selector(self.incss)
                # allgearbtns = bladewebel.find_elements_by_xpath(self.bladelist_gearbtns_x)
                inner_container = bladewebel.find_element_by_css_selector(self.bladecont_c)
                scroll_height = s.execute_script('return arguments[0].scrollHeight',
                                                 inner_container)
                do_scroll_element_to(inner_container, 0)
                bladewebel = s.find_element_by_id(self.blade_d)
                all_blade_els = bladewebel.find_elements_by_css_selector(self.incss)
                # allgearbtns = bladewebel.find_elements_by_xpath(self.bladelist_gearbtns_x)
                inner_container = bladewebel.find_element_by_css_selector(self.bladecont_c)
                scroll_height = s.execute_script('return arguments[0].scrollHeight',
                                                 inner_container)
                max_scroll_height = scroll_height + self.CH

                if is_expanded:
                    LOG.info("{0}Found Blade Expanded Already...".format(self.usedin))
                else:
                    LOG.info("{0}Found Blade Retracted...".format(self.usedin))
                already_found_and_clicked = False

                # ##################### Optimization ###############################
                # beleive it or not, this is quicker than scroll and mostly accurate
                # try a quicker approach before scroll in hope it works
                if not self.enforce_scroll_only:
                    LOG.info("{0}Try with NO Scroll first...".format(self.usedin))

                    all_styles_and_texts = webel_grab(css=self.incss,
                                                      prop=["text"],
                                                      attr=["style"],
                                                      ifc=self.ifc)
                    to_position = 0
                    element_found = False
                    for gr in all_styles_and_texts:
                        received_text = gr.get("text")
                        if self.text in received_text:
                            pos = int(''.join(x for x in gr.style if x.isdigit()))
                            LOG.debug("{0}Style position got: {1}".format(self.usedin, pos))
                            pos = int(pos / self.ui_inner_cell_height)
                            to_position = pos * self.CH + self.threshold
                            # to_position = pos * self.ui_inner_cell_height  # + self.threshold
                            LOG.debug("{0}Will scroll to: {1}".format(self.usedin, to_position))
                            element_found = True

                if element_found:  # if the element was found on this flyout
                    try:  # will center the element and regain blade and the element
                        if self.center_el_on_blade:
                            do_scroll_element_to(inner_container, to_position)
                            LOG.info("{0}Centered to position '{1}' on blade.(No Scroll)"
                                     .format(self.usedin, to_position))
                            # regain all the blade elements after scroll
                            bladewebel = s.find_element_by_id(self.blade_d)
                            all_blade_els = bladewebel.find_elements_by_css_selector(self.incss)
                            inner_container = bladewebel.find_element_by_css_selector(self.bladecont_c)
                        else:  # should be used in Save Retarct Verify - only
                            LOG.info("{0}Not Centering El on blade. (No Scroll)"
                                     .format(self.usedin))
                        allgearbtns = bladewebel.find_elements_by_xpath(self.bladelist_gearbtns_x)
                        element_found = False
                        for el, gearel in izip(all_blade_els, allgearbtns):
                            received_text = el.text
                            if self.text in received_text:
                                element_found = True
                                webel = el
                                # what to do with this element
                                if is_expanded:
                                    # taking care of the case where blade is already expanded
                                    # on that particular element that we are looking for
                                    if (self.selectedcss_c not in webel.get_attribute('class')):
                                        s.execute_script("return arguments[0].click()", webel)
                                        LOG.info("{0}Clicked directly to show el on "
                                                 "'{1}'. (blade was expanded)"
                                                 .format(self.usedin, self.text))
                                # case where blade is retracted
                                else:
                                    # if want blade to expand on el
                                    if self.expandit:  # click gear btn to expand it
                                        s.execute_script("return arguments[0].click()", gearel)
                                        LOG.info("{0}Clicked GEAR btn to show el on "
                                                 "'{1}'".format(self.usedin, self.text))
                                    # click only on el on retracted blade, no expand
                                    else:  # we only want click/ no expand here/ only if not highlighted already
                                        if (self.selectedcss_c not in webel.get_attribute('class')):
                                            s.execute_script("return arguments[0].click()", webel)
                                            LOG.info("{0}Clicked CELL to highlight el on '{1}'"
                                                     .format(self.usedin, self.text))
                                        else:
                                            LOG.info("{0}Found element clicked and higlighted already:  '{1}'"
                                                     .format(self.usedin, self.text))
                                already_found_and_clicked = True
                                LOG.debug("{0}Webel after actions: {1}. already_found_and_clicked = {2}"
                                          .format(self.usedin, webel, already_found_and_clicked))
                                break
                    except StaleElementReferenceException, e:
                        if already_found_and_clicked:
                            LOG.debug("{0}Already found and clicked, but got Stale."
                                      " Moving on...".format(self.usedin))
                            pass
                        elif self.expect_none:
                            pass
                        else:
                            LOG.debug("{0}Not Already found and clicked, but got Stale. "
                                      "Blade or element refreshed itself. "
                                      "Moving on to scroll...E was: {1}".format(self.usedin, e))
                            # raise e
                            pass  # blade refreshed itself
                    except NoSuchElementException, e:
                        if already_found_and_clicked:
                            LOG.debug("{0}Already found and clicked, but got NoSuch."
                                      "Moving on...".format(self.usedin))
                            pass
                        elif self.expect_none:
                            pass
                        else:
                            LOG.debug("{0}Not Already found and clicked, but got NoSuch."
                                      " Not Moving on...E was: {1}".format(self.usedin, e))
                            raise e
                    except Exception, e:
                        raise e

                # ##################### Finished Optimization ######################
                # and now with scroll (the hard way):
                if not already_found_and_clicked and not self.dontscroll:
                    # fail in case we can't get the height
                    if scroll_height <= 0:
                        raise NoSuchElementException(msg="{0}/ScrollHeight was: {1}".format(self.usedin, scroll_height))
    #                 # if alraedy tried with NO Scroll, el not found and
    #                 #  there are no elements outside (down more) of this screen
    #                 if not self.enforce_scroll_only and \
    #                         scroll_height + self.threshold <= last_el_scroll:
    #                     # no need for scroll either.
    #                     pass
                    i = 0
                    reach = 0
                    elfound = False
                    LOG.info("{0}Try with Scroll; height is '{1}' with a MAX of '{2}'"
                             .format(self.usedin, scroll_height, max_scroll_height))
                    blade_has_elements = True

                    while (reach <= scroll_height) and (not elfound) and blade_has_elements:
                        LOG.info('{0}Scroll at: {1}'.format(self.usedin, reach))
                        do_scroll_element_to(inner_container, reach)
                        # go around the Selenium Stale parent issue and regain the inner
                        bladewebel = s.find_element_by_id(self.blade_d)
                        inner_container = bladewebel.find_element_by_css_selector(self.bladecont_c)
                        wait_for_brush_to_disappear(self.blade, ifc=self.ifc,
                                                    ver=self.ver,
                                                    usedin=self.usedin, timeout=self.timeout)

                        curels = inner_container.find_elements_by_css_selector(self.incss)
                        row_count = len(curels)
                        if row_count == 0:
                            blade_has_elements = False
                            LOG.info("{0}Blade is empty!".format(self.usedin))

                        j = 1
                        LOG.info("{0}Searching for text '{1}'... ".format(self.usedin, self.text))
                        while (j <= row_count) and (not elfound):
                            # Delay 0.1 because the blade cells get regenerated after save.
                            time.sleep(0.1)
                            wait_for_brush_to_disappear(self.blade, ifc=self.ifc,
                                                        ver=self.ver, usedin=self.usedin,
                                                        timeout=self.timeout)

                            xpathrow = '//div[@id="{1}"]/div/div[{0}]'.format(j, self.blade)
                            try:
                                row = bladewebel.find_element_by_xpath(xpathrow)
                                LOG.debug("{0}Looking in row with text: "
                                          "'{1}'".format(self.usedin, row.text))
                                if self.text in row.text:
                                    LOG.info("{0}Found El. with '{1}'; Pos: {2}"
                                             .format(self.usedin, self.text, j))
                                    if self.center_el_on_blade:
                                        do_scroll_element_to(inner_container, reach + self.threshold)
                                        # go around the Selenium Stale parent issue and regain the inner
                                        bladewebel = s.find_element_by_id(self.blade_d)
                                        inner_container = bladewebel.find_element_by_css_selector(self.bladecont_c)
                                    # regain and return this element
                                    xpath_with_text = '//div[@id="{0}"]/div/div[contains(concat(" ", normalize-space(), " ")," {1} ")]'.format(self.blade, self.text)
                                    # webel = bladewebel.find_element_by_xpath(xpathrow)
                                    webel = s.find_element_by_xpath(xpath_with_text)
                                    if is_expanded:
                                        # taking care of the case where blade is already expanded
                                        # on that particular element that we are looking for
                                        if (self.selectedcss_c not in webel.get_attribute('class')):
                                            s.execute_script("return arguments[0].click()", webel)
                                            LOG.info("{0}Clicked directly to show el on "
                                                     "'{1}'".format(self.usedin, self.text))
                                    # case where blade is retracted
                                    else:
                                        # if want blade to expand on el
                                        if self.expandit:
                                            # the xpath of the gear button for this blade
                                            xpathgear = '{0}//div' \
                                                        '[contains(concat(" ", normalize-space(@class), " ")," propertiesIcon ")]' \
                                                        .format(xpath_with_text)
                                            btn = s.find_element_by_xpath(xpathgear)
                                            s.execute_script("return arguments[0].click()", btn)
                                            LOG.info("{0}Clicked gear btn to show el on "
                                                     "'{1}'".format(self.usedin, self.text))
                                            LOG.debug("{0}Clicked gear btn to show el on "
                                                      "'{1}'; xpath was: {2}"
                                                      .format(self.usedin, self.text, xpathgear))
                                        # click only on el on retracted blade, no expand
                                        else:
                                            if (self.selectedcss_c not in webel.get_attribute('class')):
                                                s.execute_script("return arguments[0].click()", webel)
                                                LOG.info("{0}Clicked CELL to highlight el on '{1}'"
                                                         .format(self.usedin, self.text))
                                            else:
                                                LOG.info("{0}Found element clicked and higlighted already:  '{1}'"
                                                         .format(self.usedin, self.text))
                                    elfound = True
                                    LOG.debug("{0}Scroll Reach on found element was: "
                                              "'{1}'".format(self.usedin, reach))
                            # this is because DOM sometimes changes after fist click on a found el
                            except StaleElementReferenceException, e:
                                if elfound:
                                    pass
                                elif self.expect_none:
                                    pass
                                else:
                                    raise e
                            except NoSuchElementException, e:
                                if elfound:
                                    pass
                                elif self.expect_none:
                                    pass
                                else:
                                    raise e
                            except Exception, e:
                                raise e
                            i += 1
                            # reach = i * self.CH
                            reach = i * self.ui_inner_cell_height
                            # boundary case:
                            if (reach < max_scroll_height) and (reach > scroll_height):
                                scroll_height = max_scroll_height
                                reach = scroll_height
                            j += 1
                            LOG.debug("{0}New Formed Reach is: '{1}'".format(self.usedin, reach))
        # if blade was blank
        else:
            if not self.expect_none:
                msg = "{0}Did not expect blade '{1}' to be blank!".format(self.usedin, self.blade)
                raise NoSuchElementException(msg=msg)
            else:
                LOG.info("{0}Blade was found blank. expect_none={1}".format(self.usedin, self.expect_none))
        if (self.expandit or is_expanded) and (webel) and (not self.expect_none) \
           and (not bladeisblank):
            LOG.info("{0}Waiting for Blade to be properly expanded...".format(self.usedin))
            if self.ver >= "bigiq 4.4":
                s.wait(self.fly_innercontainer_x, By.XPATH, stabilize=1.5, timeout=self.timeout)
            else:  # prior to 4.4
                bladewebel.wait(self.waitfor_c, By.CSS_SELECTOR, stabilize=1.5)
        LOG.info("{0}Wait for brush and error check...".format(self.usedin))
        if self.ver <= "bigiq 4.3" and not self.remember_jsrefresh and js_no_autorefresh != "true":
            s.execute_script('window._debug_disable_autorefresh={0};'
                             .format(js_no_autorefresh))
            LOG.debug("{0}Returned _debug_disable_autorefresh={1}"
                      .format(self.usedin, js_no_autorefresh))
        wait_for_brush_to_disappear(self.blade, ifc=self.ifc, ver=self.ver,
                                    usedin=self.usedin, timeout=self.timeout)
        popup_error_check(negative=True, ifc=self.ifc, ver=self.ver)
        LOG.info("{0}Done...".format(self.usedin))
        return webel


expand_blade_on_this_text = None
class ExpandBladeOnThisText(SeleniumCommand):  # @IgnorePep8
    """Expand and use a blade (on a text on that blade) with the default ability
        to wait for expansion, give the blade top id

    @param blade: The ID of the blade (example: "device" as from devices blade)
    @type blade: str
    @param text: The text to identify an object on a blade (any text from the cell)
    @type text: str

    Optional Params:
    @param group: For a blade with groups - the group exact name.
    @type group: str

    @param ui_cell_height: Defaults to None. Used in scrolling blade.
    @type ui_cell_height: int
    @param threshold: Defaults to None if not explicit.
                        Used on border scroll cases to center the found element
    @type threshold: int
    @param center_el_on_blade: Default on True. Center element on blade. Border case.
                            Faster if False, leave True for better visibility if it fails
    @type center_el_on_blade: bool
    @param visible: True by default to also see_blade first
    @type visible: bool
    @param usedin: Adds this "usedin" string in front of all LOG sent calls
    @type usedin: str

    @param ver: None. bq version. Ex: 'bigiq 4.3'.(Use to force a version)
                Defaults to None and ver is determined automatically.
    @type ver: string

    @return: The Selenium object on that blade.
    """
    def __init__(self, blade, text, group=None,
                 menutext=None,
                 visible=True,
                 center_el_on_blade=True,
                 ui_cell_height=None,
                 threshold=None,
                 ver=None, timeout=30,
                 *args, **kwargs):
        super(ExpandBladeOnThisText, self).__init__(*args, **kwargs)
        if blade:
            self.blade = blade
        else:
            raise NoSuchElementException(msg="/ExpandBladeOnText/Blade Name is mandatory and needs to be a string")
        self.text = text

        self.group = group
        self.visible = visible
        self.center_el_on_blade = center_el_on_blade

        if not ver:
            ver = self.ifc.version
        self.ver = ver
        self.ui_cell_height = ui_cell_height
        self.threshold = threshold

        if self.ver >= "bigiq 4.4":
            self.blade_x = '//panel[@id="{0}"]'.format(self.blade)
        else:  # versions prior to 4.4
            self.blade_x = '//*[@id="{0}_blade"]'.format(self.blade)
        self.menutext = menutext
        self.timeout = timeout

    def setup(self):

        click_blade_on_text(blade=self.blade, text=self.text,
                            group=self.group,
                            menutext=self.menutext,
                            usedin="ExpandBladeOnText",
                            expandit=True,
                            visible=self.visible,
                            ui_cell_height=self.ui_cell_height,
                            threshold=self.threshold,
                            center_el_on_blade=self.center_el_on_blade,
                            ver=self.ver, timeout=self.timeout,
                            ifc=self.ifc)
        # gain blade to return it
        s = self.api
        blade = s.find_element_by_xpath(self.blade_x)
        popup_error_check(negative=True, ifc=self.ifc, ver=self.ver)
        return blade


retract_blade = None
class RetractBlade(SeleniumCommand):  # @IgnorePep8
    """Retract a blade. Can wait for something to appear or disappear.

    @param blade: The ID of the blade (example: "device" as from devices blade)
    @type blade: str
    @param use_this_x_button, use_this_d_button: an xpath or an ID to expand on
    @type use_this_x_button, use_this_d_button: str
    @param use_this_c_button: css to expand on (default)
    @param ver: version, default: None (on the fly)
    @type ver: str
    @param timeout: int
    @type timeout: int

    @return: The Selenium object on that blade.
    """
    def __init__(self, blade,
                 timeout=20,
                 use_this_c_button=None, use_this_d_button=None, use_this_x_button=None,
                 ver=None,
                 *args, **kwargs):
        super(RetractBlade, self).__init__(*args, **kwargs)
        if blade:
            self.blade = blade
        else:
            raise NoSuchElementException(msg="/retract_blade/Blade ID is mandatory and needs to be a string")
        if not ver:
            ver = self.ifc.version
        self.ver = ver
        if self.ver >= "bigiq 4.4":
            self.blade = blade
            if not use_this_x_button and not use_this_d_button and not use_this_c_button:
                use_this_x_button = '//panel[@id="{0}"]//button[contains(@id,"closeFlyout") or (normalize-space()="Cancel") or (normalize-space()="Close")]'.format(self.blade)
            self.fly_innercontainer_x = '//panel[@id="{0}"]/flyout/div[contains(@class, "innerContainer")]/*'.format(self.blade)
        else:
            self.blade_d = '{0}_blade'.format(self.blade)
            self.bladesub_c = "#{0} .bladeSub".format(self.blade_d)
            self.bladesubhead_c = '#{0} .bladeSubHeader'.format(self.blade_d)
            self.bladecont_c = '#{0}.innerContainer'.format(self.blade)
        if not use_this_c_button:
            use_this_c_button = ".subBladeBtn1"
        if use_this_d_button or use_this_x_button:
            use_this_c_button = None

        self.cancel_btn_c = use_this_c_button
        self.cancel_btn_x = use_this_x_button
        self.cancel_btn_d = use_this_d_button
        self.timeout = timeout

    def setup(self):
        s = self.api
        LOG.debug("Retracting the Blade '{0}'...".format(self.blade))
        if self.ver >= "bigiq 4.4":
            # Determine if the blade is expanded. Look for the Head Text
            is_expanded = True
            iec = webel_grab(xpath=self.fly_innercontainer_x, ifc=self.ifc)
            if iec == []:
                is_expanded = False
            if is_expanded:
                if self.cancel_btn_c:
                    cancelbtn = s.find_element_by_css_selector(self.cancel_btn_c)
                elif self.cancel_btn_d:
                    cancelbtn = s.find_element_by_id(self.cancel_btn_d)
                elif self.cancel_btn_x:
                    cancelbtn = s.find_element_by_xpath(self.cancel_btn_x)
                s = cancelbtn.click().wait(self.fly_innercontainer_x, By.XPATH,
                                           negated=True,
                                           stabilize=1,
                                           timeout=self.timeout)
            else:
                LOG.debug("/RetractBlade/{0}/Found Blade Retracted...".format(self.blade))
                pass
        else:  # all smaller than 4.4 versions
            blade = s.find_element_by_id(self.blade_d)
            try:
                subheader = blade.find_element_by_css_selector(self.bladesubhead_c)
                s.wait(self.bladecont_c, By.CSS_SELECTOR)
            except NoSuchElementException as e:
                LOG.error("Blade Does not appear to be expanded. Can't retract!")
                raise e
            except StaleElementReferenceException as e:
                LOG.error("Blade Does not appear to be expanded. Can't retract!")
                raise e
            if self.cancel_btn_c:
                cancelbtn = subheader.find_element_by_css_selector(self.cancel_btn_c)
            elif self.cancel_btn_d:
                cancelbtn = subheader.find_element_by_id(self.cancel_btn_d)
            elif self.cancel_btn_x:
                cancelbtn = subheader.find_element_by_xpath(self.cancel_btn_x)
            s = cancelbtn.click().wait(self.bladesub_c, By.CSS_SELECTOR,
                                       negated=True, timeout=self.timeout, stabilize=1)
        # wait for animation to rearrange blades after some retracts (IE 9 mostly).
        time.sleep(1)
        # wait for the brush to go away if there.
        wait_for_brush_to_disappear(self.blade, ifc=self.ifc, ver=self.ver,
                                    usedin="/retract_blade/", timeout=self.timeout)

        popup_error_check(negative=True, ifc=self.ifc, ver=self.ver)
        LOG.info("/RetractBlade/{0}/Done.".format(self.blade))
        return s


save_retract = None
class SaveRetract(SeleniumCommand):  # @IgnorePep8
    """Save and Retract a blade. Can wait for something to appear or disappear.
    General usage: give blade alias, waitfortext = {your saving element name}
    Example: save_retract(blade="users", waitfortext="my new saved user")

    @param blade: The name of the blade (example: "devices" as from devices_blade)
    @type blade: str

    Optional parameters:

    @param waitfortext: the text to wait for after clicking save.
    @type waitfortext: str
    @param waittoverify: Defaults to 0.2 seconds. Used to delay between action and
                         reaction. Will wait after save and before verifying the blade
    @type waittoverify: int
    @param with_verify: True by default. Will verify the blade for that name.
    @type with_verify: bool

    @param use_this_x_button, use_this_d_button: an xpath or id of the button (if not default)
    @param use_this_c_button: css of the button (default, already there)
    @type use_this_x_button, use_this_d_button, use_this_c_button: str
    @param jsclick: False by default to not force click on the button
    @type jsclick: bool

    @param timeout; How long to wait for each action (element to appear, retract)
    @type timeout: int

    @param withrefresh: Default on False. Refresh after save and retract,
                        before searching blade for the saved element.
    @type withrefresh: bool
    @param ver: None. bq version. Ex: 'bigiq 4.3'.(Use to force a version)
                Defaults to None and ver is determined automatically.
    @type ver: string

    @return: The Selenium object on that retracted blade.
    """
    def __init__(self, blade, group=None,
                 use_this_c_button=None,
                 use_this_d_button=None,
                 use_this_x_button=None,
                 with_verify=True, waitfortext=None, waittoverify=None,
                 ui_cell_height=None, threshold=None,
                 jsclick=False, withrefresh=False, timeout=15,
                 ver=None,
                 *args, **kwargs):
        super(SaveRetract, self).__init__(*args, **kwargs)
        if blade:
            self.blade = blade
        else:
            raise NoSuchElementException(msg="/save_retract/Blade ID is mandatory and needs to be a string")
        if not ver:
            ver = self.ifc.version

        if ver >= "bigiq 4.4":
            self.blade_d = self.blade
            if not use_this_x_button and not use_this_d_button and not use_this_c_button:
                use_this_x_button = '//panel[@id="{0}"]//button[contains(@id,"save") or contains(@id,"add") or (normalize-space()="Save")]'.format(self.blade)
            self.fly_innercontainer_x = '//panel[@id="{0}"]/flyout/div[contains(@class, "innerContainer")]/*'.format(self.blade)
            if not waittoverify:
                waittoverify = 1
        else:
            self.blade_d = '{0}_blade'.format(self.blade)
            use_this_c_button = '.subBladeBtn3'
            self.waitfor_c = "#{0} .bladeSub".format(self.blade_d)
            self.bladesubhead_c = '#{0} .bladeSubHeader'.format(self.blade_d)
            self.bladecont_c = '#{0}.innerContainer'.format(self.blade)
            if not waittoverify:
                waittoverify = 0.2
        if use_this_d_button or use_this_x_button:
            use_this_c_button = None

        self.btn_c = use_this_c_button
        self.btn_x = use_this_x_button
        self.btn_d = use_this_d_button

        self.jsclick = jsclick

        self.with_verify = with_verify
        self.waittoverify = waittoverify
        self.waitfortext = waitfortext

        self.timeout = timeout
        self.withrefresh = withrefresh
        self.ui_cell_height = ui_cell_height
        self.threshold = threshold
        self.ver = ver
        self.group = group

    def setup(self):
        s = self.api
        js_no_autorefresh = False
        if self.ver <= "bigiq 4.3":
            # Remember Autorefresh and disable it:
            js_no_autorefresh = s.execute_script('return window._debug_disable_autorefresh;')
            if js_no_autorefresh is None:
                js_no_autorefresh = "null"
                # Disable Autorefresh:
                s.execute_script('window._debug_disable_autorefresh=true;')
            elif js_no_autorefresh:
                js_no_autorefresh = "true"
            elif js_no_autorefresh is False:
                js_no_autorefresh = "false"
                # Disable Autorefresh:
                s.execute_script('window._debug_disable_autorefresh=true;')

        LOG.info("SaveRetract/Blade '{0}'...".format(self.blade))
        blade = s.find_element_by_id(self.blade_d)
        if self.ver >= "bigiq 4.4":
            # Determine if the blade is expanded. Look for the Head Text
            is_expanded = True
            iec = webel_grab(xpath=self.fly_innercontainer_x, ifc=self.ifc)
            if iec == []:
                is_expanded = False
            if is_expanded:
                if self.btn_c:
                    btn = s.find_element_by_css_selector(self.btn_c)
                elif self.btn_d:
                    btn = s.find_element_by_id(self.btn_d)
                elif self.btn_x:
                    btn = s.find_element_by_xpath(self.btn_x)
                if not self.jsclick:
                    btn.click()
                else:
                    s.execute_script("return arguments[0].click()", btn)
                wait_for_brush_to_disappear(self.blade, ifc=self.ifc, ver=self.ver,
                                            usedin="SaveRetract", timeout=self.timeout)
                popup_error_check(negative=True, ifc=self.ifc, ver=self.ver)
                s.wait(self.fly_innercontainer_x, By.XPATH,
                       negated=True, timeout=self.timeout)
            else:
                LOG.error("SaveRetract/{0}/Blade Does not appear to be expanded. Can't Save!".format(self.blade))
                raise NoSuchElementException(msg="SaveRetract/{0}/Blade Does not appear to be expanded. Can't Save!".format(self.blade))
        else:  # for all smaller than 4.4
            try:
                s.wait(self.bladecont_c, By.CSS_SELECTOR)
                subheader = blade.find_element_by_css_selector(self.bladesubhead_c)
            except NoSuchElementException as e:
                LOG.error("SaveRetract/Blade Does not appear to be expanded. Can't Save!")
                raise e
            except StaleElementReferenceException as e:
                LOG.error("SaveRetract/Blade Does not appear to be expanded. Can't Save!")
                raise e
            if self.btn_c:
                btn = subheader.find_element_by_css_selector(self.btn_c)
            elif self.btn_d:
                btn = subheader.find_element_by_id(self.btn_d)
            elif self.btn_x:
                btn = subheader.find_element_by_xpath(self.btn_x)
            # click and wait to retract:
            if not self.jsclick:
                btn.click()
                s.wait(self.waitfor_c, By.CSS_SELECTOR,
                       negated=True, timeout=self.timeout, stabilize=1)
            else:
                s.execute_script("return arguments[0].click()", btn)
                s.wait(self.waitfor_c, By.CSS_SELECTOR,
                       negated=True, timeout=self.timeout, stabilize=1)
            if self.withrefresh:
                s = self.api
                s.refresh()
                see_blade(blade=self.blade, ifc=self.ifc, ver=self.ver)

        if self.with_verify:
            if self.ver <= "bigiq 4.3":
                if js_no_autorefresh != "true":
                    s.execute_script('window._debug_disable_autorefresh={0};'
                                     .format(js_no_autorefresh))
                    LOG.debug("SaveRetract/Returned _debug_disable_autorefresh={0}"
                              .format(js_no_autorefresh))
            # wait some time before verifying the blade:
            if self.waittoverify > 0:
                LOG.info("/SaveRetractVerify/Waiting {0}s before verify. ..."
                         .format(self.waittoverify))
                time.sleep(self.waittoverify)

            webel = click_blade_on_text(blade=self.blade,
                                        group=self.group,
                                        visible=False,
                                        text=self.waitfortext,
                                        usedin="SaveRetractVerify",
                                        ui_cell_height=self.ui_cell_height,
                                        threshold=self.threshold,
                                        center_el_on_blade=False,
                                        ver=self.ver,
                                        ifc=self.ifc)
            if webel is None:
                raise NoSuchElementException(msg="/SaveRetractVerify/Could Not Verify that the el is there.")

        wait_for_brush_to_disappear(self.blade, ifc=self.ifc, ver=self.ver,
                                    usedin="SaveRetract", timeout=self.timeout)
        # regain control of the same blade and return it
        blade = s.find_element_by_id(self.blade_d)
        if self.ver <= "bigiq 4.3":
            if js_no_autorefresh != "true":
                s.execute_script('window._debug_disable_autorefresh={0};'
                                 .format(js_no_autorefresh))
                LOG.debug("SaveRetract/Returned _debug_disable_autorefresh={0}"
                          .format(js_no_autorefresh))
        popup_error_check(negative=True, ifc=self.ifc, ver=self.ver)
        return blade

search_blade = None
class SearchBlade(SeleniumCommand):  # @IgnorePep8
    """Find all elements that match a given text/regex (with Scroll on any blade).
    Returns what elements were found, scroll position for each and how many of each

    @param blade: The name of the blade (example: "devices" as from devices_blade)
    @type blade: str
    @param text: the text/regex or texts/regexes list to search on the blade for.
    @type text: str or list of str

    Optional parameters:

    @param usedin: Adds this "usedin" string in front of all LOG sent calls
    @type usedin: str
    @param visible: if see_blade should be used first. Defaults on True.
    @type visible: bool

    @param ui_inner_cell_height: Defaults to 56. < bq 4.3 or 47 for bq >= 4.4
                                 Exact style value for 2nd EL from Top of Blade.
    @type ui_inner_cell_height: int

    @param dontscroll: False by default. Use no scroll.
    @type dontscroll: bool

    @param remember_jsrefresh: Default on False. Does not modify the jsrefresh during test.
    @type remember_jsrefresh: bool

    @param ver: None. bq version. Ex: 'bigiq 4.3'.(Use to force a version)
                Defaults to None and ver is determined automatically.
    @type ver: string

    @return: List of Dicts if elements were found or None.
    """
    def __init__(self, blade, text=None, group=None,
                 usedin=None, visible=True,
                 ui_inner_cell_height=None,
                 dontscroll=False,
                 remember_jsrefresh=False,
                 ver=None, timeout=15,
                 *args, **kwargs):
        super(SearchBlade, self).__init__(*args, **kwargs)
        if blade:
            self.blade = blade
        else:
            raise NoSuchElementException(msg="/SearchBlade/Blade ID is mandatory and needs to be a string")
        if (text is not None):
            if isinstance(text, basestring):
                text = [text]
            self.text = text
        else:
            raise NoSuchElementException(msg="/SearchBlade/text is mandatory and needs to be a string")
        if not ver:
            ver = self.ifc.version
        self.ver = ver
        self.group = group
        if self.ver >= 'bigiq 4.4':
            if not ui_inner_cell_height:
                ui_inner_cell_height = 47
            self.blade_d = '{0}'.format(self.blade)
            self.blade_x = '//panel[@id="{0}"]'.format(self.blade)
            self.blade_panel_d = '{0}_panel'.format(self.blade)
            self.bladesub_c = self.waitfor_c = "#{0} .bladeSub".format(self.blade_d)
            self.bladesubhead_c = '#{0} .bladeSubHeader'.format(self.blade_d)
            self.bladecont_c = '#{0}.innerContainer'.format(self.blade)
            self.bladelist_cells_x = '//div[@id="{0}"]/div/div[*]'.format(self.blade)
            self.incss = None
            self.blade_x = '//panel[@id="{0}"]'.format(self.blade)
            self.panelbase = '//panel[@id="{0}"]/div[contains(@class,"panelMain")]/div[contains(@class,"innerContainer")]' \
                             .format(self.blade)
            if self.group:
                self.innercontainer_x = '{0}//li[contains(., "{1}")]//ul'.format(self.panelbase, self.group)
                self.all_els_x = '{0}/li[*]/div'.format(self.innercontainer_x)
            else:
                self.innercontainer_x = '{0}//div[contains(@class,"panelListContainer")]'.format(self.panelbase)
                self.all_els_x = '{0}/ul/li[*]'.format(self.innercontainer_x)
            self.selectedcss_c = "highlight"
            self.fly_header_c = "#{0} .panelSubHeader".format(self.blade)
            self.fly_innercontainer_x = '//panel[@id="{0}"]/flyout/div[contains(@class, "innerContainer")]/*'.format(self.blade)
            self.bladelist_cells_x = '//panel[@id="{0}"]/div/div[contains(@class, "innerContainer")]/panel-list/div[contains(@class, "panelListContainer")]/ul/li[*]'.format(self.blade)
        elif self.ver < 'bigiq 4.4':
            if not ui_inner_cell_height:
                ui_inner_cell_height = 56
            self.blade_d = '{0}_blade'.format(self.blade)
            self.blade_x = '//div[@id="{0}"]'.format(self.blade_d)
            self.blade_panel_d = '{0}_panel'.format(self.blade)
            self.bladesub_c = self.waitfor_c = "#{0} .bladeSub".format(self.blade_d)
            self.bladesubhead_c = '#{0} .bladeSubHeader'.format(self.blade_d)
            self.bladecont_c = '#{0}.innerContainer'.format(self.blade)
            self.bladelist_cells_x = '//div[@id="{0}"]/div/div[*]'.format(self.blade)
            self.selectedcss_c = "brushSource highlight"
            self.incss = "#{0}_blade .listCell".format(self.blade)
        self.ui_inner_cell_height = ui_inner_cell_height
        usedin = "{0}SearchBlade/{1}/".format(usedin + "/" if usedin else "",
                                              self.blade)
        self.usedin = usedin
        self.visible = visible
        self.dontscroll = dontscroll
        self.remember_jsrefresh = remember_jsrefresh
        self.timeout = timeout

    def setup(self):
        s = self.api
        js_no_autorefresh = None
        if not self.remember_jsrefresh and self.ver <= "bigiq 4.3":
            # Remember Autorefresh and disable it:
            js_no_autorefresh = s.execute_script('return window._debug_disable_autorefresh;')
            if js_no_autorefresh is None:
                js_no_autorefresh = "null"
                # Disable Autorefresh:
                s.execute_script('window._debug_disable_autorefresh=true;')
            elif js_no_autorefresh:
                js_no_autorefresh = "true"
            elif js_no_autorefresh is False:
                js_no_autorefresh = "false"
                # Disable Autorefresh:
                s.execute_script('window._debug_disable_autorefresh=true;')

        returnlist = None

        LOG.debug("{0}'{1}'_Start_SearchBlade...".format(self.usedin, self.text))

        def do_scroll_element_to(element, position, tsleep=1):
            s.execute_script('arguments[0].scrollTop = arguments[1]', element, position)
            # Sleep is to cover the UI animation.
            time.sleep(tsleep)

        count = count_on_blade(blade=self.blade, group=self.group,
                               visible=self.visible,
                               ui_inner_cell_height=self.ui_inner_cell_height,
                               usedin=self.usedin, ifc=self.ifc, ver=self.ver)
        if count >= 0:
            wait_for_brush_to_disappear(self.blade, ifc=self.ifc, ver=self.ver,
                                        usedin=self.usedin, timeout=self.timeout)

            if self.ver >= "bigiq 4.4":
                if self.group:
                    # to do
                    LOG.info("{0}...No Scroll Yet for Groups...".format(self.usedin))
                    # inner_container = s.find_element_by_xpath(self.innercontainer_x)
                    # scroll_height = self.ui_inner_cell_height
                else:  # blade with no groups (regular)
                    inner_container = s.find_element_by_xpath(self.innercontainer_x)
                    scroll_height = s.execute_script('return arguments[0].scrollHeight',
                                                     inner_container)
                if self.dontscroll or self.group:
                    LOG.info("{0}Searching with NO Scroll ...".format(self.usedin))
                    rlist = []
                    at_least_one_was_found = False
                    all_texts = webel_grab(xpath=self.all_els_x, ifc=self.ifc)
                    for text in self.text:  # for each text to compare to
                        dic_per_tag = {"text": text}
                        cell_count_on_this_text = 0
                        for cell in all_texts:  # for each element from UI
                            received_text_cell = cell.get("text")
                            if text in received_text_cell:
                                cell_count_on_this_text += 1
                                at_least_one_was_found = True
                        dic_per_tag["found"] = cell_count_on_this_text
                        rlist.append(dic_per_tag)
                    if at_least_one_was_found:  # if none was found, retun None
                        returnlist = rlist

                # and now with scroll (the hard should way):
                else:
                    # fail in case we can't get the height
                    if scroll_height <= 0:
                        raise NoSuchElementException(msg="{0}/ScrollHeight was: {1}".format(self.usedin, scroll_height))
                    LOG.info("{0}Searching with Scroll ...".format(self.usedin))
                    # scroll to top first:
                    do_scroll_element_to(inner_container, 0)
                    rlist = []
                    at_least_one_was_found = False
                    all_texts = []
                    for pos in range(count):
                        reach = pos * self.ui_inner_cell_height
                        do_scroll_element_to(inner_container, reach)
                        xpath_row = '{0}/ul/li[contains(concat(" ", normalize-space(@style), " "),"top: {1}px; ")]'.format(self.innercontainer_x, reach)
                        this_text = webel_grab(xpath=xpath_row, ifc=self.ifc)
                        this_text[0]["pos"] = reach
                        all_texts.append(this_text[0])
                    for text in self.text:  # for each text to compare to
                        dic_per_tag = {"text": text, "pos": []}
                        cell_count_on_this_text = 0
                        for cell in all_texts:  # for each element from UI
                            received_text_cell = cell.get("text")
                            if text in received_text_cell:
                                cell_count_on_this_text += 1
                                at_least_one_was_found = True
                                dic_per_tag["pos"].append(cell.get("pos"))
                        dic_per_tag["found"] = cell_count_on_this_text
                        rlist.append(dic_per_tag)
                    if at_least_one_was_found:  # if none was found, retun None
                        returnlist = rlist
            else:  # all smaller than 4.4 versions
                bladewebel = s.find_element_by_id(self.blade_d)
                inner_container = bladewebel.find_element_by_css_selector(self.bladecont_c)
                scroll_height = s.execute_script('return arguments[0].scrollHeight',
                                                 inner_container)
                if self.dontscroll:
                    LOG.info("{0}Searching with NO Scroll ...".format(self.usedin))
                    rlist = []
                    at_least_one_was_found = False
                    all_texts = webel_grab(css=self.incss, ifc=self.ifc)
                    for text in self.text:  # for each text to compare to
                        dic_per_tag = {"text": text}
                        cell_count_on_this_text = 0
                        for cell in all_texts:  # for each element from UI
                            received_text_cell = cell.get("text")
                            if text in received_text_cell:
                                cell_count_on_this_text += 1
                                at_least_one_was_found = True
                        dic_per_tag["found"] = cell_count_on_this_text
                        rlist.append(dic_per_tag)
                    if at_least_one_was_found:  # if none was found, retun None
                        returnlist = rlist

                # and now with scroll (the hard should way):
                else:
                    # fail in case we can't get the height
                    if scroll_height <= 0:
                        raise NoSuchElementException(msg="{0}/ScrollHeight was: {1}".format(self.usedin, scroll_height))
                    LOG.info("{0}Searching with Scroll ...".format(self.usedin))
                    rlist = []
                    at_least_one_was_found = False
                    all_texts = []
                    for pos in range(count):
                        reach = pos * self.ui_inner_cell_height
                        do_scroll_element_to(inner_container, reach)
                        xpath_row = '//div[@id="{0}"]/div//div' \
                                    '[contains(concat(" ", normalize-space(@style), " "),' \
                                    '" {1}px; ")]'.format(self.blade, reach)
                        this_text = webel_grab(xpath=xpath_row, ifc=self.ifc)
                        this_text[0]["pos"] = reach
                        all_texts.append(this_text[0])

                    for text in self.text:  # for each text to compare to
                        dic_per_tag = {"text": text, "pos": []}
                        cell_count_on_this_text = 0
                        for cell in all_texts:  # for each element from UI
                            received_text_cell = cell.get("text")
                            if text in received_text_cell:
                                cell_count_on_this_text += 1
                                at_least_one_was_found = True
                                dic_per_tag["pos"].append(cell.get("pos"))
                        dic_per_tag["found"] = cell_count_on_this_text
                        rlist.append(dic_per_tag)
                    if at_least_one_was_found:  # if none was found, retun None
                        returnlist = rlist
        # if blade was blank
        else:
            LOG.info("{0}Blade was found blank.".format(self.usedin))
        if self.ver <= "bigiq 4.3" and not self.remember_jsrefresh and js_no_autorefresh != "true":
            s.execute_script('window._debug_disable_autorefresh={0};'
                             .format(js_no_autorefresh))
            LOG.debug("{0}Returned _debug_disable_autorefresh={1}"
                      .format(self.usedin, js_no_autorefresh))
        wait_for_brush_to_disappear(self.blade, ifc=self.ifc, ver=self.ver,
                                    usedin=self.usedin, timeout=self.timeout)
        popup_error_check(negative=True, ifc=self.ifc, ver=self.ver)
        return returnlist

delete_object_on_text = None
class DeleteObjectOnText(SeleniumCommand):  # @IgnorePep8
    """Deletes one object or a list of objects identified by regex,
        on a blade and verifies that the object(s) is/are not on the
        retracted blade anymore.

    @param blade: The name of the blade (example: "devices" as from devices_blade)
    @type blade: str
    @param text: text/regex or list of texts/tegexes to identify the object(s)
                    to delete from the list on the blade
    @type text: str or list of str

    Optional Params:

    @param with_verify: True by default. Will verify the blade for that name.
            Usefull to set on False in case there are objects with the same text.
    @type with_verify: bool
    @param waittoverify: Defaults to 0.2 seconds. Used to delay between action and
                         reaction. Will wait after delete and before verifying the blade
    @type waittoverify: int

    @param ui_cell_height: Defaults to None. Used in scrolling blade.
    @type ui_cell_height: int
    @param threshold: Defaults to None if not explicit.
                        Used on border scroll cases to center the found element
    @type threshold: int

    @param use_this_c_button: css of the delete button, if not the default
    @type use_this_c_button: str
    @param use_this_x/d_button: xpath/did of the delete button,
                                        if not using the default css
    @type use_this_x/d_button: str

    @param visible: True by default to also see_blade before delete (if docked)
    @type visible: bool

    @param with_widget: True by default. No popup confirmation used if False.
    @type with_widget: bool
    @param widget_title_c, widget_delete_btn_c: css used for the widget confirm delete,
                                                if not using the default ones.
    @type widget_title_c, widget_delete_btn_c: str

    @param ver: None. bq version. Ex: 'bigiq 4.3'.(Use to force a version)
                Defaults to None and ver is determined automatically.
    @type ver: string

    @return: The Selenium object on that blade.
    """
    def __init__(self, blade, text, group=None, menutext=None,
                 center_el_on_blade=True,
                 with_verify=True, waittoverify=None,
                 with_widget=True,
                 visible=True,
                 widget_title_c=None,
                 widget_title_x=None,
                 widget_delete_btn_c=None,
                 widget_delete_btn_x=None,
                 use_this_c_button=None,
                 use_this_d_button=None,
                 use_this_x_button=None,
                 ui_cell_height=None, threshold=None,
                 timeout=90,
                 dontscroll=False,
                 ver=None,
                 *args, **kwargs):
        super(DeleteObjectOnText, self).__init__(*args, **kwargs)
        if blade and text:
            self.blade = blade
        else:
            raise NoSuchElementException(msg="/DeleteObj/Blade Name and 'text' to delete are mandatory.")
        if isinstance(text, basestring):
            text = [text]
        self.text = text
        self.visible = visible
        if not ver:
            ver = self.ifc.version
        self.ver = ver

        if self.ver >= "bigiq 4.4":
            self.blade_d = '{0}'.format(self.blade)
            if not ui_cell_height:
                ui_cell_height = 47
            if not waittoverify:
                waittoverify = 1
            if not widget_title_x and not widget_title_c:
                widget_title_x = '//dialog[@show="true"][contains(@title, "Delete") or contains(@title, "Remove")]//span[contains(., "Delete") or contains(., "Remove")]'
            if not widget_delete_btn_x and not widget_delete_btn_c:
                widget_delete_btn_x = '//dialog[@show="true"][contains(@title, "Delete") or contains(@title, "Remove")]//button[(normalize-space()="Delete") or (normalize-space()="Remove")]'
            if not use_this_x_button and not use_this_d_button and not use_this_c_button:
                use_this_x_button = '//panel[@id="{0}"]//button[contains(@id,"delete") or (normalize-space()="Delete")]'.format(self.blade)
        else:  # all version before 4.4
            self.blade_d = '{0}_blade'.format(self.blade)
            if not ui_cell_height:
                ui_cell_height = 56
            if not waittoverify:
                waittoverify = 0.2
            if not use_this_c_button:
                use_this_c_button = '#{0} .subBladeBtn2'.format(self.blade_d)
            if not widget_title_c:
                widget_title_c = ".ui-dialog-title"
            if not widget_delete_btn_c:
                widget_delete_btn_c = ".confirm_delete.headerButton"

        self.group = group
        self.menutext = menutext
        self.with_widget = with_widget
        self.timeout = timeout
        self.waittoverify = waittoverify

        self.use_this_c_button = use_this_c_button
        self.use_this_x_button = use_this_x_button
        self.use_this_d_button = use_this_d_button
        self.center_el_on_blade = center_el_on_blade
        self.with_verify = with_verify
        self.widget_title_c = widget_title_c
        self.widget_delete_btn_c = widget_delete_btn_c
        self.widget_title_x = widget_title_x
        self.widget_delete_btn_x = widget_delete_btn_x
        self.ui_cell_height = ui_cell_height
        self.threshold = threshold
        self.dontscroll = dontscroll

    def setup(self):
        s = self.api
        js_no_autorefresh = None
        if self.ver <= "bigiq 4.3":
            # Remember Autorefresh and disable it:
            js_no_autorefresh = s.execute_script('return window._debug_disable_autorefresh;')
            if js_no_autorefresh is None:
                js_no_autorefresh = "null"
                # Disable Autorefresh:
                s.execute_script('window._debug_disable_autorefresh=true;')
            elif js_no_autorefresh:
                js_no_autorefresh = "true"
            elif js_no_autorefresh is False:
                js_no_autorefresh = "false"
                # Disable Autorefresh:
                s.execute_script('window._debug_disable_autorefresh=true;')

        LOG.info("DeleteObj/Will Delete: '{0}' on blade '{1}'..."
                 .format(self.text, self.blade))
        for text in self.text:
            LOG.info("DeleteObj/Deleting object with text '{0}' on blade '{1}'..."
                     .format(text, self.blade))
            click_blade_on_text(blade=self.blade, text=text, group=self.group,
                                menutext=self.menutext,
                                usedin="DeleteObj",
                                expandit=True,
                                visible=self.visible,
                                ui_cell_height=self.ui_cell_height,
                                threshold=self.threshold,
                                center_el_on_blade=self.center_el_on_blade,
                                ver=self.ver,
                                timeout=self.timeout,
                                ifc=self.ifc)
            wait_for_brush_to_disappear(self.blade, ifc=self.ifc, ver=self.ver,
                                        timeout=self.timeout)

            # if using the confirm widget:
            if self.with_widget:
                # click delete on blade and wait for widget title to appear
                webel_click(css=self.use_this_c_button,
                            xpath=self.use_this_x_button,
                            did=self.use_this_d_button,
                            waitforcss=self.widget_title_c,
                            waitforxpath=self.widget_title_x,
                            timeout=self.timeout, ifc=self.ifc)
                LOG.info("DeleteObj/Deleted object...Confirming Widget...")

                # click widget delete btn
                webel_click(css=self.widget_delete_btn_c,
                            xpath=self.widget_delete_btn_x,
                            timeout=self.timeout, ifc=self.ifc)
                # wait for the dialog to dissapear
                if self.widget_title_c:
                    s.wait(self.widget_title_c, By.CSS_SELECTOR, negated=True,
                           timeout=self.timeout)
                if self.widget_title_x:
                    s.wait(self.widget_title_x, By.XPATH, negated=True,
                           timeout=self.timeout)
                wait_for_brush_to_disappear(self.blade, ifc=self.ifc, ver=self.ver,
                                            usedin="DeleteObj", timeout=self.timeout)
                LOG.debug("DeleteObj/Delete Confirm Widget disappeared...")
            # if not using the confirm widget at all (blade requires no confirm del):
            else:
                # click delete on blade and Done.
                webel_click(css=self.use_this_c_button,
                            xpath=self.use_this_x_button,
                            did=self.use_this_d_button,
                            timeout=self.timeout, ifc=self.ifc)
                LOG.debug("DeleteObj/Deleted object...Done. ")

        # Thoroughly Verify of this blade if needed (by default)
        # also means unique text identifier for the ui cell of the obj:

        # wait some time before verifying the blade:
        if self.with_verify:
            if self.ver <= "bigiq 4.3":
                if js_no_autorefresh != "true":
                    s.execute_script('window._debug_disable_autorefresh={0};'
                                     .format(js_no_autorefresh))
                    LOG.debug("DeleteObj/Returned _debug_disable_autorefresh={0}"
                              .format(js_no_autorefresh))
            if self.waittoverify > 0:
                LOG.info("DeleteObjVerify/{1}/Obj: {2}; Waiting {0}s before verify. ..."
                         .format(self.waittoverify, self.blade, self.text))
                time.sleep(self.waittoverify)
            wait_for_brush_to_disappear(self.blade, ifc=self.ifc, ver=self.ver,
                                        usedin="DeleteObjVerify", timeout=self.timeout)

            self.result = [""]

            def is_el_removed_from_blade():
                self.result = search_blade(blade=self.blade, text=self.text, group=self.group,
                                           usedin="DeleteObjVerify",
                                           ui_inner_cell_height=self.ui_cell_height,
                                           ver=self.ver,
                                           dontscroll=self.dontscroll,
                                           ifc=self.ifc)
                if self.result is None:
                    return True
            wait(is_el_removed_from_blade, interval=10, timeout=self.timeout,
                 timeout_message="DeleteObjVerify/%s/After {0}s, Objects: '%s' were still "
                 "found after delete. (Use with_verify=False if multiple "
                 "objects same name.)" % (self.blade, self.result))

        LOG.info("DeleteObj/Deleted object(s) with text(s) '{0}' on blade '{1}'..."
                 .format(self.text, self.blade))
        if self.ver <= "bigiq 4.3":
            if js_no_autorefresh != "true":
                s.execute_script('window._debug_disable_autorefresh={0};'
                                 .format(js_no_autorefresh))
                LOG.debug("DeleteObj/Returned _debug_disable_autorefresh={0}"
                          .format(js_no_autorefresh))
        popup_error_check(negative=True, ifc=self.ifc, ver=self.ver)
        return s

drag_and_drop = None
class DragAndDrop(SeleniumCommand):  # @IgnorePep8
    """Drags and Drops from one blade to another based on text

    @param fromblade: The name of the from blade (example: "devices" as from devices_blade)
    @param toblade: The name of the to blade (example: "devices" as from devices_blade)
    @type fromblade, toblade: str

    @param fromtext: The text of an element on the from blade
    @param totext: The text of an element on the to blade
    @type fromblade, toblade: str

    Optional Parameters:
    @param withrefresh: Default on False. Refresh UI before trying to find the elemnts,
                        (before searching blades for the two elements).
    @type withrefresh: bool

    @param withconfirmdialog: Is there a confirm dialog afterwards? True by default
    @type withconfirmdialog: bool
    @param use_this_x_button, use_this_d_button: an xpath or id of the
                                        Confirm dialog button (if not default)
    @param use_this_c_button: css of the same button (if not default, already there)
    @type use_this_x_button, use_this_d_button, use_this_c_button: str
    @param ui_cell_height: Defaults to None. Used in scrolling blade.
    @type ui_cell_height: int
    @param threshold: Defaults to None if not explicit.
                        Used on border scroll cases to center the found element
    @type threshold: int

    @param ver: None. bq version. Ex: 'bigiq 4.3'.(Use to force a version)
                Defaults to None and ver is determined automatically.
    @type ver: string

    @param timeout: how long to wait for action to complete
    @type timeout: int

    @return: The Selenium object on that blade.
    """
    def __init__(self,
                 fromblade, toblade,
                 fromtext, totext,
                 ui_cell_height=None, threshold=None,
                 use_this_c_button=None, use_this_d_button=None, use_this_x_button=None,
                 finxpath=None, fattr=None, fincss=None, findid=None,
                 tinxpath=None, tattr=None, tincss=None, tindid=None,
                 withconfirmdialog=True, withrefresh=False,
                 timeout=15, dead_timeout=180,
                 ver=None,
                 *args, **kwargs):
        super(DragAndDrop, self).__init__(*args, **kwargs)
        if fromblade and toblade and fromtext and totext:
            self.fromblade = fromblade
            self.toblade = toblade
            self.fromtext = fromtext
            self.totext = totext
        else:
            raise NoSuchElementException(msg="/Drag&Drop/Blades and texts are mandatory!")
        if not ver:
            ver = self.ifc.version
        self.ver = ver
        self.dialogtitle_c = ""
        if self.ver >= 'bigiq 4.5':
            if not use_this_c_button and not use_this_x_button and not use_this_d_button:
                use_this_x_button = "//*[@id='confirmdeleteuser']//button[contains(., 'Confirm')]"
            if not fincss and not finxpath and not findid:
                finxpath = '//*[@id="{0}"]//panel-list//ul/li[div[contains(concat(" ", normalize-space(), " ")," {1} ")]]' \
                           .format(self.fromblade, self.fromtext)
            if not tincss and not tinxpath and not tindid:
                tinxpath = '//*[@id="{0}"]//panel-list//ul/li[div[contains(concat(" ", normalize-space(), " ")," {1} ")]]' \
                           .format(self.toblade, self.totext)
            self.dialogtitle_c = "#confirmdeleteuser .dialogTitle"
        else:  # older than 4.5
            if not use_this_c_button and not use_this_x_button and not use_this_d_button:
                use_this_c_button = '.confirm_save'
            if not fincss and not finxpath and not findid:
                fincss = "#{0} .listCell".format(self.fromblade)
            if not tincss and not tinxpath and not tindid:
                tincss = "#{0} .listCell".format(self.toblade)
            self.dialogtitle_c = ".ui-dialog-title"
        self.finxpath = finxpath
        self.fattr = fattr
        self.fincss = fincss
        self.findid = findid
        self.tinxpath = tinxpath
        self.tattr = tattr
        self.tincss = tincss
        self.tindid = tindid
        self.withconfirmdialog = withconfirmdialog
        self.use_this_x_button = use_this_x_button
        self.use_this_c_button = use_this_c_button
        self.use_this_d_button = use_this_d_button
        self.timeout = timeout
        self.withrefresh = withrefresh
        self.ui_cell_height = ui_cell_height
        self.threshold = threshold
        self.dead_timeout = dead_timeout

    def setup(self):
        s = self.api

        LOG.info("/Drag&Drop/Try ...From: [{0}][{1}] To: [{2}][{3}];"
                 .format(self.fromblade, self.fromtext, self.toblade, self.totext))

        # bring the two blades in view:
        if self.withrefresh:
            s = self.api
            s.refresh()
        js_no_autorefresh = None
        if self.ver <= "bigiq 4.3":
            # Remember Autorefresh and disable it:
            js_no_autorefresh = s.execute_script('return window._debug_disable_autorefresh;')
            if js_no_autorefresh is None:
                js_no_autorefresh = "null"
                # Disable Autorefresh:
                s.execute_script('window._debug_disable_autorefresh=true;')
            elif js_no_autorefresh:
                js_no_autorefresh = "true"
            elif js_no_autorefresh is False:
                js_no_autorefresh = "false"
                # Disable Autorefresh:
                s.execute_script('window._debug_disable_autorefresh=true;')

        # see_blade(blade=self.fromblade, ifc=self.ifc, ver=self.ver)
        # see_blade(blade=self.toblade, ifc=self.ifc, ver=self.ver)
        # wait for the brush to go away if there.
        # wait_for_brush_to_disappear(self.fromblade, ifc=self.ifc, ver=self.ver,
        #                            usedin="Drag&Drop", timeout=self.timeout)
        # wait_for_brush_to_disappear(self.toblade, ifc=self.ifc, ver=self.ver,
        #                            usedin="Drag&Drop", timeout=self.timeout)

        # fetch a valid webel from each blade (retry it if fails)

        def give_a_valid_from_webel():
            ff = False
            from_webel = click_blade_on_text(blade=self.fromblade,
                                             text=self.fromtext,
                                             visible=True,
                                             center_el_on_blade=True,
                                             usedin="Drag&Drop",
                                             ui_cell_height=self.ui_cell_height,
                                             threshold=self.threshold,
                                             remember_jsrefresh=True,
                                             ver=self.ver, timeout=self.dead_timeout,
                                             ifc=self.ifc)
            if from_webel is not None:
                ff = True
                LOG.debug("/Drag&Drop/Success. From Webel was fetched.")
            else:
                LOG.debug("/Drag&Drop/From Webel was None this time...")
            return ff

        def give_a_valid_to_webel():
            ff = False
            to_webel = click_blade_on_text(blade=self.toblade,
                                           text=self.totext,
                                           visible=True,
                                           center_el_on_blade=True,
                                           usedin="Drag&Drop",
                                           ui_cell_height=self.ui_cell_height,
                                           threshold=self.threshold,
                                           remember_jsrefresh=True,
                                           ver=self.ver, timeout=self.dead_timeout,
                                           ifc=self.ifc)
            if to_webel is not None:
                ff = True
                LOG.debug("/Drag&Drop/Success. To Webel was fetched.")
            else:
                LOG.debug("/Drag&Drop/To Webel was None this time...")
            return ff

        LOG.info("/Drag&Drop/Fetch webel ...From: [{0}][{1}];"
                 .format(self.fromblade, self.fromtext))
        wait(give_a_valid_from_webel, timeout=self.dead_timeout)
        LOG.info("/Drag&Drop/Fetch webel ...From: [{0}][{1}];"
                 .format(self.toblade, self.totext))
        wait(give_a_valid_to_webel, timeout=self.dead_timeout)

        # regain s
        s = self.api
        # Disable Autorefresh:
        s.execute_script('window._debug_disable_autorefresh=true;')
        wait_for_brush_to_disappear(self.fromblade, ifc=self.ifc, ver=self.ver,
                                    usedin="Drag&Drop", timeout=self.timeout)
        wait_for_brush_to_disappear(self.toblade, ifc=self.ifc, ver=self.ver,
                                    usedin="Drag&Drop", timeout=self.timeout)

        # Retry the Drag and Drop
        def tryactionchain():
            tobeornottobe = True
            try:
                # only support xpath for now
                from_webel = s.find_element_by_xpath(self.finxpath)
                to_webel = s.find_element_by_xpath(self.tinxpath)
                if not from_webel or not to_webel:
                    LOG.error("/Drag&Drop/Did a refresh just happened? "
                              "From:[{0}] To [{1}] - Needs both to be valid..."
                              .format(from_webel, to_webel))
                # The Drag and Drop:
                LOG.info("/Drag&Drop/Trying Drag&Drop now... ...")
                # print "Move to from_webel"
                # time.sleep(2)
                action = ActionChains(s)
                action.move_to_element(from_webel)
                action.perform()
                time.sleep(2)
                action = ActionChains(s)
                # print "Click and hold"
                action = ActionChains(s)
                action.click_and_hold(from_webel)
                action.perform()
                time.sleep(2)
                # print "Move to to"
                action = ActionChains(s)
                action.move_to_element(to_webel)
                action.perform()
                # print "Release"
                time.sleep(2)
                action = ActionChains(s)
                action.release(from_webel)
                action.perform()
                # time.sleep(1)
                # ActionChains(s).drag_and_drop(from_webel, to_webel).perform()
                time.sleep(1)
                if self.withconfirmdialog:
                    el = None
                    LOG.info("/Drag&Drop/Should Have Happened...Wait for Confirm Dialog...")
                    try:
                        s.wait(self.dialogtitle_c, By.CSS_SELECTOR)
                        el = s.find_element_by_css_selector(self.dialogtitle_c)
                        # print el
                    except NoSuchElementException:
                        tobeornottobe = False
                        pass
                    if el is None:
                        tobeornottobe = False
            except StaleElementReferenceException:
                tobeornottobe = False
                LOG.warning("/Drag&Drop/StaleElementReferenceException happened "
                            " during ActionChains. Will retry a few times...")
                pass
            return tobeornottobe

        def tryactionchain_43():
            tobeornottobe = True
            try:
                items = []
                # getting webel on from blade
                from_webel = None
                if self.fincss:
                    items = s.find_elements_by_css_selector(self.fincss)
                elif self.finxpath:
                    items = s.find_elements_by_xpath(self.finxpath)
                elif self.findid:
                    items = s.find_elements_by_id(self.findid)
                for item in items:
                    if self.fromtext in item.text:
                        from_webel = item
                # TO:
                # getting webel on to blade
                to_webel = None
                if self.tincss:
                    items = s.find_elements_by_css_selector(self.tincss)
                elif self.tinxpath:
                    items = s.find_elements_by_xpath(self.tinxpath)
                elif self.tindid:
                    items = s.find_elements_by_id(self.tindid)
                for item in items:
                    if self.totext in item.text:
                        to_webel = item
                if not from_webel or not to_webel:
                    LOG.error("/Drag&Drop/Did a refresh just happened? "
                              "From:[{0}] To [{1}] - Needs both to be valid..."
                              .format(from_webel, to_webel))
                # The Drag and Drop:
                LOG.info("/Drag&Drop/Trying Drag&Drop now... ...")
                ActionChains(s).drag_and_drop(from_webel, to_webel).perform()
                if self.withconfirmdialog:
                    el = None
                    try:
                        s.wait(self.dialogtitle_c, By.CSS_SELECTOR)
                        el = s.find_element_by_css_selector(self.dialogtitle_c)
                    except NoSuchElementException:
                        tobeornottobe = False
                        pass
                    if el is None:
                        tobeornottobe = False
            except StaleElementReferenceException:
                tobeornottobe = False
                LOG.debug("/Drag&Drop/StaleElementReferenceException happened "
                          " during ActionChains. Will retry a few times...")
                pass
            return tobeornottobe
        if self.ver >= 'bigiq 4.4':
            wait(tryactionchain, timeout=self.dead_timeout)
            # tryactionchain()
        else:  # self.ver <= 'bigiq 4.3':
            wait(tryactionchain_43, timeout=self.dead_timeout)
        LOG.info("/Drag&Drop/Success in Drag and Drop...")

        # Moving on to the Confirm Dialog, if any
        if self.withconfirmdialog:
            LOG.debug("/Drag&Drop/Confirming action in the confirm dialog...")
            LOG.info("/Drag&Drop/Confirming action in the confirm dialog...")

#             def is_confirm_dialog_there_yet():
#                 appeared = False
#                 try:
#                     s.wait(self.dialogtitle_c, By.CSS_SELECTOR)
#                     textd = s.find_element_by_css_selector(self.dialogtitle_c).text
#                     s.wait(self.dialogtitle_c, By.CSS_SELECTOR, it=Is.TEXT_MATCH,
#                            match=textd,
#                            interval=1,
#                            timeout=20,
#                            stabilize=1)
#                     appeared = True
#                 except StaleElementReferenceException:
#                         pass
#                 except NoSuchElementException:
#                         pass
#                 return appeared
#             wait(is_confirm_dialog_there_yet, timeout=self.dead_timeout)
            # click the confirm button and wait for the dialog to dissapear
            webel_click(css=self.use_this_c_button,
                        xpath=self.use_this_x_button,
                        did=self.use_this_d_button,
                        waitforcss=self.dialogtitle_c, negated=True,
                        timeout=self.dead_timeout, ifc=self.ifc)
            LOG.info("/Drag&Drop/Success in confirming the popup dialog...")
        # wait for the brush to go away if there.
        wait_for_brush_to_disappear(self.fromblade, ifc=self.ifc, ver=self.ver,
                                    usedin="Drag&Drop", timeout=self.timeout)
        wait_for_brush_to_disappear(self.toblade, ifc=self.ifc, ver=self.ver,
                                    usedin="Drag&Drop", timeout=self.timeout)
        if self.ver <= "bigiq 4.3":
            if js_no_autorefresh != "true":
                s.execute_script('window._debug_disable_autorefresh={0};'
                                 .format(js_no_autorefresh))
                LOG.debug("/Drag&Drop/Returned _debug_disable_autorefresh={0}"
                          .format(js_no_autorefresh))
        popup_error_check(negative=True, ifc=self.ifc, ver=self.ver)
        return s


brush_on_text = None
class BrushOnText(SeleniumCommand):  # @IgnorePep8
    """Clicks a text on a given blade and returns the brushed objects for all blades

    @param blade: name of the blade (example: "devices" as from devices_blade)
    @type blade: str
    @param text: name of the object to be clicked on a given blade
    @type text: str

    Optional Parameters:

    @type text: str
    @param ver: None. bq version. Ex: 'bigiq 4.3'.(Use to force a version)
                Defaults to None and ver is determined automatically.
    @type ver: string

    @return: A Dict with all/requested blade names and brushed objects
    """
    def __init__(self, blade, text, blades_list=None,
                 group=None, timeout=30, ver=None, *args, **kwargs):
        super(BrushOnText, self).__init__(*args, **kwargs)

        self.blade_name = blade
        self.text = text
        if not ver:
            ver = self.ifc.version
        self.ver = ver
        self.blade_c = '.blade'
        self.group = group
        self.timeout = timeout

    def setup(self):
        s = self.api
        click_blade_on_text(blade=self.blade_name, text=self.text,
                            group=self.group,
                            ver=self.ver,
                            ifc=self.ifc)

        params = webel_grab(css=self.blade_c,
                            attr=['id'], ifc=self.ifc)
        LOG.debug('Obtained params {0}' .format(params))
        if params:
            return_list = {}
            for item in params:
                current_blade = item.id[:-6]
                LOG.info('Starting to find brushed elements in {0}'.format(current_blade))
                brushed_elements = []
                if current_blade != self.blade_name:
                    see_blade(blade=current_blade, ifc=self.ifc, ver=self.ver)
                    elements = s.find_elements_by_xpath('//div[@id="{0}"]//div[not(contains(@class, "brushed")) and contains(@class,"listCell")]' .format(current_blade))
                    for item in elements:
                        brushed_elements.append(item.text)
                    if len(brushed_elements) > 0:
                        return_list[current_blade] = brushed_elements
                    else:
                        LOG.info('{0} blade does not have any related elements' .format(current_blade))
                else:
                    LOG.debug('Skipping {0} blade'.format(current_blade))

        else:
            LOG.error('/BrushOnText/No blade detected')

        return return_list
