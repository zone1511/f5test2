from __future__ import absolute_import
from selenium.webdriver.remote.webdriver import WebDriver as RemoteWebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.remote.command import Command
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (NoSuchElementException, 
    StaleElementReferenceException, WebDriverException) # ElementNotVisibleException
import time
import logging
import uuid

LOG = logging.getLogger(__name__) 


class ConditionError(Exception):
    pass

class Is(object):
    DISPLAYED = "is_displayed"
    VISIBLE = "is_displayed" # alias
    SELECTED = "is_selected"
    ENABLED = "is_enabled"
    PRESENT = None
    TEST = None


class NONEGIVEN:
    pass


class WebElementWrapper(WebElement):

    def wait(self, *args, **kwargs):
        """Waits for condition c"""
        return self.parent.wait(*args, element=self, **kwargs)

    def click(self, *args, **kwargs):
        """condition wrapped"""
        super(WebElementWrapper, self).click(*args, **kwargs)
        return self.parent

    def submit(self, *args, **kwargs):
        """condition wrapped"""
        super(WebElementWrapper, self).submit(*args, **kwargs)
        return self.parent

    def hover(self):
        """Gets the location."""
        self.parent.execute(Command.MOVE_TO, {'element': self.id})
        return self.parent

 
class RemoteWrapper(RemoteWebDriver):
    
    def __init__(self, *args, **kwargs):
        self._current_frame = None # None is the _top frame
        return super(RemoteWrapper, self).__init__(*args, **kwargs)

    def switch_to_frame(self, index_or_name):
        """Switches focus to a frame by index or name."""
        self._current_frame = index_or_name
        super(RemoteWrapper, self).switch_to_frame(index_or_name)

    def switch_to_default_content(self):
        self._current_frame = None
        super(RemoteWrapper, self).switch_to_default_content()

    def create_web_element(self, element_id):
        """Override from RemoteWebDriver to use firefox.WebElement."""
        return WebElementWrapper(self, element_id) 

    def move_to_element(self, to_element):
        """Moving the mouse to the middle of an element.
        Args:
            to_element: The element to move to.
        """
        return self.execute(Command.MOVE_TO, {'element': to_element.id})
        #return self.execute(Command.HOVER_OVER_ELEMENT, {'id': to_element.id})

    def get(self, *args, **kwargs):
        """Loads a web page in the current browser."""
        super(RemoteWrapper, self).get(*args, **kwargs)
        return self

    def open_window(self, name=None, location='', tokens=''):
        """Opens up a new tab or window."""
        if name is None:
            name = uuid.uuid4().hex
        script = "window.open('%s','%s', '%s')" % (location, name, tokens)
        super(RemoteWrapper, self).execute_script(script)
        return name

    def maximize_window(self):
        script = "if (window.screen) {window.moveTo(0, 0); window.resizeTo(window.screen.availWidth, window.screen.availHeight);};"
        return super(RemoteWrapper, self).execute_script(script)

    def wait(self, value=None, by=By.ID, frame=NONEGIVEN, it=Is.DISPLAYED, 
             negated=False, timeout=10, interval=0.1, stabilize=0, element=None, test=None):
        """Waits for an element to become active/visible/etc..
        If frame is passed, then it will first switch to main frame, try to
        locate the element and switch back to main frame.
        """

        f = {}
        f['by'] = by
        if frame is NONEGIVEN:
            f['frame'] = '[current]'
        else:
            f['frame'] = frame or '_top'
        f['value'] = value
        f['negated'] = negated and 'not' or 'to be'
        if it == Is.VISIBLE or it == Is.DISPLAYED:
            f['state'] = 'visible'
        elif it == Is.SELECTED:
            f['state'] = 'selected'
        elif it == Is.ENABLED:
            f['state'] = 'enabled'
        else:
            f['state'] = 'present'
        c_text = 'element with %(by)s "%(value)s" in frame %(frame)s %(negated)s %(state)s' % f

        
        if element is None:
            element = self
        
        if test:
            assert callable(test), '"test" must be a callback function with 2 params: element and exception.'

        if not frame is NONEGIVEN:
            self.switch_to_default_content()

        now = start = time.time()
        e = None
        stable_time = 0
        while now - start < timeout:
            good = False
            try:
                if not frame is NONEGIVEN:
                    self.switch_to_frame(frame)

                e = element.find_element(by=by, value=value)

                if it == Is.TEST:
                    if test(e, None):
                        LOG.debug("Custom condition met.")
                        good = True
                elif it == Is.PRESENT:
                    if not negated:
                        LOG.debug("Condition '%s' met.", c_text)
                        good = True
                    else:
                        LOG.debug("Waiting for '%s'.", c_text)
                elif (not getattr(e, it)() ^ (not negated)):
                    LOG.debug("Condition '%s' met.", c_text)
                    good = True
                else:
                    LOG.debug("Waiting for '%s'.", c_text)

            # BUG: Remove IndexError when issue 2116 is fixed.
            except (IndexError, NoSuchElementException, StaleElementReferenceException), exc:
                if it == Is.TEST:
                    if test(None, exc):
                        LOG.debug("Custom condition met.")
                        good = True
                elif (it == Is.PRESENT and negated):
                    LOG.debug("Condition '%s' met.", c_text)
                    good = True
                LOG.debug("Waiting for '%s'.", c_text)
            except WebDriverException, exc:
                LOG.debug("Selenium is confused: '%s'.", exc)
            finally:
                if not frame is NONEGIVEN:
                    self.switch_to_default_content()

            if good:
                if stable_time >= stabilize:
                    break
                else:
                    stable_time += interval
                    LOG.debug("(stabilizing)...")
            else:
                # Reset the stable time when condition is not met.
                stable_time = 0

            time.sleep(interval)
            now = time.time()
        else:
            raise ConditionError, "Condition '%s' not met after %d seconds." % (c_text, now - start)
        
        return e
