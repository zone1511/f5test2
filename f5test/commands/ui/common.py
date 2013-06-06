from .base import SeleniumCommand
from ...interfaces.config import ConfigInterface, DeviceAccess
from ...interfaces.selenium import By, Is
from ...interfaces.selenium.driver import NoSuchElementException, ElementWait
from ...base import AttrDict
from ..base import WaitableCommand, CommandError
import os
import logging
import re
import codecs

LOG = logging.getLogger(__name__)


class BannerError(Exception):
    pass


class LoadingBannerWait(ElementWait):

    def __init__(self, *args, **kwargs):
        self._css = kwargs.pop('css')
        return super(LoadingBannerWait, self).__init__(*args, **kwargs)

    def test_result(self):
        result = self._result
        is_visible = result.is_displayed()
        css = result.get_attribute('class')
        if not self._css is None:
            if css and 'loading' not in css:
                return True
        else:
            if not is_visible or (css and 'loading' not in css):
                return True
        return False


wait_for_loading = None
class WaitForLoading(SeleniumCommand): #@IgnorePep8
    """Waits for the Loading XUI banner to change.

    @param timeout: Wait this many seconds for the task to finish (default: 60).
    @type timeout:  int
    @param interval: Polling interval (default: 1)
    @type interval:  int
    @param css: Fail if  after loading banner's css class is not this.
    @type css: str
    """
    def __init__(self, timeout=60, interval=1, css=None, *args, **kwargs):
        self.timeout = timeout
        self.interval = interval
        self.css = css
        super(WaitForLoading, self).__init__(*args, **kwargs)

    def setup(self):
        b = self.api

        prev_frame = b.get_current_frame()
        w = LoadingBannerWait(b, timeout=self.timeout,
                              interval=self.interval, stabilize=1, css=self.css)

        w.run(value='//div[@id="banner"]/div[@id="message"]/div[@id="messagetype"]',
              by=By.XPATH, frame='/')
        css = get_banner_css(ifc=self.ifc)
        b.switch_to_frame(prev_frame)
        if self.css and self.css not in css:
            raise BannerError("Unexpected banner! (css=%s)" % css)


get_banner_css = None
class GetBannerCss(SeleniumCommand): #@IgnorePep8
    """Returns the banner type: success, warning, confirm, loading, etc..

    @return: A set of css class strings.
    @rtype: set
    """
    def setup(self):
        xpath = '//div[@id="message"]/div[@id="messagetype"]'

        b = self.api
        frame = b.get_current_frame()
        if frame != None:
            b.switch_to_default_content()

        e = b.find_element_by_xpath(xpath)
        css_class = e.get_attribute('class').split()

        if frame != None:
            b.switch_to_frame(frame)

        return set(css_class)


get_cell_xpath = None
class GetCellXpath(WaitableCommand, SeleniumCommand): #@IgnorePep8
    """Xpath builder for common tables with thead and tbody elements.

    @param table_id: The ID of the table HTML element.
    @type table_id: str
    @param column: The column name as listed in the table header row.
    @type table_id: str
    @param value: The cell value to look for.
    @type value: str

    @return: The xpath
    @rtype: str
    """
    def __init__(self, table_id, column, value, *args, **kwargs):
        super(GetCellXpath, self).__init__(*args, **kwargs)
        self.table_id = table_id
        self.column = column
        self.value = value

    def setup(self):
        b = self.api
        params = AttrDict()
        params.table_id = self.table_id

        # WARNING: The following Xpath may cause your eyes to bleed.
        params.column = self.column
        params.value = self.value
        params.column_index = "count(//table[@id='%(table_id)s']/thead/tr/*[descendant-or-self::*[contains(text(), '%(column)s')]]/preceding-sibling::*) + 1" % params
        xpath = "//table[@id='%(table_id)s']/tbody/tr[td[%(column_index)s]//self::*[normalize-space(text())='%(value)s']]" % params
        # Validate the existence of the table with the required ID.
        try:
            b.find_element_by_xpath(xpath)
            return xpath
        except NoSuchElementException:
            raise CommandError('Cell with value %(value)s not found in table %(table_id)s on column %(column)s.' % params)


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
                 port=None, proto='https', timeout=120, *args, **kwargs):
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

        b.get("{0[proto]}://{0[address]}:{0[port]}{0[path]}".format(self.__dict__)).wait('username',
                                                                                         timeout=self.timeout)

        e = b.find_element_by_name("username")
        e.click()
        e.send_keys(self.username)

        e = b.find_element_by_id("passwd")
        e.send_keys(self.password)
        e.submit().wait('#navbar > #trail span', by=By.CSS_SELECTOR, timeout=30)
        b.maximize_window()

        # XXX: Workaround for Xui fly-out menus that don't disappear, thus
        # interfering with several browsers running with Native Events,
        # simulating real mouse events.
        script = "$('#body li.hasmenu').hide()"
        self.api.execute_script(script)


screen_shot = None
class ScreenShot(SeleniumCommand): #@IgnorePep8
    """Take a screenshot and save the page source.

    @param dir: Output directory (must have write permissions).
    @type dir: str
    @param screenshot: the name of the screenshot file (default: screenshot).
    @type screenshot: str
    """
    def __init__(self, dir, name=None, window=None, *args, **kwargs):  # @ReservedAssignment
        super(ScreenShot, self).__init__(*args, **kwargs)
        self.dir = dir
        if name is None:
            self.name = window or 'main'
        else:
            self.name = name
        self.window = window

    def setup(self):
        b = self.api
        if self.window is not None:
            b.switch_to_window(self.window)

        filename = os.path.join(self.dir, '%s.png' % self.name)
        if b.get_screenshot_as_file(filename):
            LOG.debug('Screenshot dumped to: %s' % filename)

        try:
            filename = os.path.join(self.dir, '%s.html' % self.name)
            #src = b.execute_script("return document.documentElement.innerHTML;")
            src = b.page_source
            src = re.sub('<head>', '<HEAD><BASE href="%s"/>' % b.current_url,
                         src, flags=re.IGNORECASE)

            # Prevent javascript from being executed when the saved page is loaded.
            src = re.sub('/xui/common/scripts/api.js', '', src)
            src = re.sub(re.escape('$(document).ready( startup );'), '', src)

            # Save the page source encoded as UTF-8
            with codecs.open(filename, "w", 'utf-8-sig') as f:
                f.write(src)
        except IOError, e:
            LOG.error('I/O error dumping source: %s', e)


logout = None
class Logout(SeleniumCommand): #@IgnorePep8
    """Log out by clicking on the Logout button."""
    def setup(self):
        b = self.api
        b.switch_to_default_content()
        logout = b.wait('#logout a', by=By.CSS_SELECTOR)
        logout.click().wait('username')
        self.ifc.del_credentials()


close_all_windows = None
class CloseAllWindows(SeleniumCommand): #@IgnorePep8
    """Close all windows but the main."""
    def setup(self):
        b = self.api
        all_windows = b.window_handles or []
        if len(all_windows) <= 1:
            return
        main_window = self.ifc.window
        for window in all_windows:
            if window != main_window:
                b.switch_to_window(window)
                b.close()
        b.switch_to_window(main_window)


browse_to_tab = None
class BrowseToTab(SeleniumCommand): #@IgnorePep8
    """XUI tab navigator. JQuery based.

    @param locator: Tab locator (e.g. Device | NTP)
    @type locator: str
    """
    def __init__(self, locator, *args, **kwargs):
        super(BrowseToTab, self).__init__(*args, **kwargs)
        self.locator = locator

    def __repr__(self):
        parent = super(BrowseToTab, self).__repr__()
        opt = {}
        opt['locator'] = self.locator
        return parent + "(locator=%(locator)s)" % opt

    def setup(self):
        b = self.api
        b.switch_to_default_content()
        locator = self.locator

        if locator == 'Options':
            xpath = "//div[@id='pagemenu']//a[(not(@class) or " \
                    "@class != 'options') and text()='Options']"
        else:
            xpath = "//div[@id='pagemenu']"
            count = 0
            for t in locator.split('|'):
                count += 1
                t = t.strip()
                if t.startswith('[') and t.endswith(']'):
                    xpath += "/ul/li[%s]" % t[1:-1]
                else:
                    if count == 1:
                        xpath += "/ul/li[@class != 'options' and a[text()='%s']]" % t
                    else:
                        xpath += "/ul/li[a[text()='%s']]" % t
                if count == 1:
                    b.wait(xpath, by=By.XPATH)
                e = b.find_element_by_xpath(xpath)
                #e.click()

            # XXX: Uses direct JQuery calls.
            b.execute_script("$(arguments[0]).children('a').click();", e)


browse_to = None
class BrowseTo(SeleniumCommand): #@IgnorePep8
    """XUI menu navigator. JQuery based.

    @param locator: Menu locator (e.g. System | Logs : Options)
    @type locator: str
    """
    def __init__(self, locator, *args, **kwargs):
        super(BrowseTo, self).__init__(*args, **kwargs)
        self.locator = locator

    def __repr__(self):
        parent = super(BrowseTo, self).__repr__()
        opt = {}
        opt['locator'] = self.locator
        return parent + "(locator=%(locator)s)" % opt

    def setup(self):
        b = self.api

        b.switch_to_default_content()
        bits = self.locator.split(':', 1)
        locator = bits[0]
        index = 0
        if locator.endswith('[+]'):
            locator = locator.replace('[+]', '', 1).rstrip()
            index = 1

        panel, locator = locator.split('|', 1)
        panel = panel.strip()
        locator = locator.strip()
        xpath = "//div[@id='mainpanel']/div[a[text()='%s']]" % panel

        for t in locator.split('|'):
            t = t.strip()
            if t.startswith('[') and t.endswith(']'):
                xpath += "/ul/li[%s]" % t[1:-1]
            else:
                xpath += "/ul/li[a='%s']" % t
            e = b.find_element_by_xpath(xpath)

        # XXX: Uses direct JQuery calls.
        b.execute_script("$(arguments[0]).children('a:nth(%d)').click();" %
                         index, e)

        if len(bits) == 2:
            locator = bits[1]
            wait_for_loading(ifc=self.ifc)
            browse_to_tab(locator, ifc=self.ifc)

        elif len(bits) > 2:
            raise Exception('bad locator: %s Only one : allowed' % locator)


set_preferences = None
class SetPreferences(SeleniumCommand): #@IgnorePep8
    """Sets the "Idle time before automatic logout" in System->Preferences.

    @param timeout: The idle timeout value.
    @type timeout: int
    """
    def __init__(self, prefs=None, *args, **kwargs):
        super(SetPreferences, self).__init__(*args, **kwargs)
        self.prefs = prefs

    def setup(self):
        b = self.api
        browse_to('System | Preferences', ifc=self.ifc)
        b.wait('div_security_table', frame='/contentframe')

        # Dirty flag
        anything = False

        if self.prefs.get('timeout'):
            e = b.find_element_by_name('gui_session_inactivity_timeout')
            value = e.get_attribute('value')
            new_value = self.prefs.timeout
            if int(value) != new_value:
                LOG.info('Setting preference timeout=%s', new_value)
                e.clear()
                e.send_keys(str(new_value))
                anything = True

        if self.prefs.get('records'):
            e = b.find_element_by_name('records_per_page')
            value = e.get_attribute('value')
            new_value = self.prefs.records
            if int(value) != new_value:
                LOG.info('Setting preference records=%s', new_value)
                e.clear()
                e.send_keys(str(new_value))
                anything = True

        if anything:
            e = b.find_element_by_id("update")
            e.click()
            wait_for_loading(ifc=self.ifc)


set_platform_configuration = None
class SetPlatformConfiguration(SeleniumCommand): #@IgnorePep8
    """Sets the values in System->Platform page.

    @param values: Values to be updates.
    @type values: dict
    """
    def __init__(self, values=None, *args, **kwargs):
        super(SetPlatformConfiguration, self).__init__(*args, **kwargs)
        self.values = values

    def setup(self):
        b = self.api
        browse_to('System | Platform', ifc=self.ifc)
        update = b.wait('platform_update', frame='/contentframe')

        # Dirty flag
        anything = False

        if not self.values.get('ssh') is None:
            enabled = self.values.get('ssh', False)
            access = b.find_element_by_id('service.ssh')
            if (enabled and not access.is_selected() or
                not enabled and access.is_selected()):
                if enabled:
                    LOG.info("Enabling SSH Access.")
                else:
                    LOG.info("Disabling SSH Access.")
                access.click()
                anything = True

        if anything:
            update.click()
            wait_for_loading(ifc=self.ifc)

delete_items = None
class DeleteItems(SeleniumCommand): #@IgnorePep8
    """Deletes selected items in a table. Expects success banner.
    """
    def setup(self):
        b = self.api
        LOG.debug('Deleting selected items...')

        # The "new style" refers to the Luna UI-kind of tables that pop up a
        # Delete confirmation modal dialog, instead of the BS3 delete + delete
        # confirm workflow.
        new_style = False
        try:
            delete_button = b.find_element_by_id("confirmDelete:dialogForm:confirm")
            new_style = True
        except NoSuchElementException:
            pass

        if new_style:
            delete_button = b.wait("//form[@id='tableForm']//input[contains(@id, 'deleteButton')]",
                                   By.XPATH, it=Is.ENABLED)
            delete_button = delete_button.click().wait("confirmDelete:dialogForm:confirm")
        else:
            try:
                delete_button = b.find_element_by_xpath("//input[@value='Delete...']")
            except NoSuchElementException:
                delete_button = b.find_element_by_xpath("//input[@value='Delete']")
            delete_button = delete_button.click().wait("delete_confirm", By.NAME)

        # Click the confirm Delete
        delete_button.click()
        wait_for_loading(ifc=self.ifc)
        LOG.debug('Deleted successfully.')


audit_search = None
class AuditSearch(SeleniumCommand): #@IgnorePep8
    """Searches for a specific string in the audit log.
    Returns the first row found.
    """
    def __init__(self, value=None, *args, **kwargs):
        super(AuditSearch, self).__init__(*args, **kwargs)
        self.value = value

    def setup(self):
        b = self.api
        LOG.info('Looking for "%s" in the audit...', self.value)

        browse_to('System | Logs | Audit | Search', ifc=self.ifc)
        b.wait('div_search_params_table', frame='/contentframe')

        event_text = b.find_element_by_name('search_event')
        event_text.clear()
        event_text.send_keys(self.value)

        search = b.find_element_by_name('search')
        search.click()
        wait_for_loading(ifc=self.ifc)
        show_all(ifc=self.ifc)

        try:
            row = b.find_element_by_id('0')
        except:
            b.find_element_by_id('no_record_row')
            raise CommandError('No audit rows found.')

        cells = row.find_elements_by_tag_name('td')
        count = len(b.find_elements_by_xpath("//table[@id='list_table']/tbody//tr"))
        return (count, cells[0].text, cells[1].text, cells[2].text, cells[3].text)


handle_errorframe = None
class HandleErrorframe(SeleniumCommand): #@IgnorePep8
    """Handles the "Unable to contact [product name] device" overlay.
    Note: Login path is not implemented yet.
    """
    def setup(self):
        b = self.api
        LOG.debug('Looking for errorframe...')
        frame = b.get_current_frame()

        try:
            b.switch_to_frame("/errorframe")
            b.wait('complete', timeout=60)
            continue_button = b.find_element_by_id("button-continue")
            if continue_button.is_displayed():
                LOG.debug('Errorframe is displayed.')
                continue_button.click()
                b.switch_to_default_content()
                b.wait('errorframe', negated=True)
            else:
                LOG.debug('Errorframe is NOT displayed. Phew!')
        finally:
            b.switch_to_frame(frame)


show_all = None
class ShowAll(SeleniumCommand): #@IgnorePep8
    """
    Set the paginator to "Show All".
    """
    def setup(self):
        b = self.api
        try:
            select = b.find_element_by_name("ptable")
            showall = select.find_element_by_xpath("option[@value='-1']")
            showall_caption = showall.text.strip()
            showall.click()
            wait_for_loading(ifc=self.ifc)
        except NoSuchElementException:
            showall_caption = None
            LOG.debug('No paginator found.')
        return showall_caption


get_bs3textarea_text = None
class GetBs3textareaText(SeleniumCommand): #@IgnorePep8
    """A cross-browser command that returns the text of a textarea element
    updated through a BS3 call.

    @param element: The textarea element
    @type element: WebDriverElement instance
    @return: The text
    @rtype: str
    """
    def __init__(self, element, *args, **kwargs):
        super(GetBs3textareaText, self).__init__(*args, **kwargs)
        self.element = element

    def setup(self):
        _, uap = self.ifc.useragent
        if uap.browser.name == 'Microsoft Internet Explorer':
            return self.element.text
        else:
            return self.element.get_attribute('value')
