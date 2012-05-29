from __future__ import absolute_import
from selenium.webdriver.remote.webdriver import WebDriver as RemoteWebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.remote.command import Command
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (NoSuchElementException, 
    StaleElementReferenceException, WebDriverException, NoSuchWindowException)
import copy
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
    PRESENT = 0
    TEST = 1


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
        self._frames = {}
        self._current_window_handle = None
        return super(RemoteWrapper, self).__init__(*args, **kwargs)

    @property
    def current_window_handle(self):
        """
        Cache and return the handle of the current window.

        :Usage:
            driver.current_window_handle
        """
        if not self._current_window_handle:
            self._current_window_handle = super(RemoteWrapper, self).current_window_handle
        return self._current_window_handle

    def switch_to_frame(self, frame_path='.', window_handle=None, forced=False):
        """Switches focus to a frame by index or name.
        
        @param frame_path: The frame path (e.g. /frame1/subframe or ../parent)
        @param window: The window handle
        @param forced: Attempt to switch frames even we're out of sync
        """
        if window_handle is None:
            window_handle = self.current_window_handle
        orig_frames = self._frames.setdefault(window_handle, [])
        frames = copy.copy(orig_frames)
        
        for i, bit in enumerate(frame_path.split('/')):
            if bit == '':
                # Path starts with a / (absolute)
                if i == 0: 
                    frames[:] = []
                # Path ends / (ignore it)
                else:
                    continue
            elif bit == '..':
                try:
                    # Go up one level
                    frames.pop()
                except IndexError:
                    # We've reached the bottom already
                    continue
            elif bit == '.':
                # Ignore it
                continue
            else:
                frames.append(bit)
        
        if forced or frames != orig_frames:
            try:
                super(RemoteWrapper, self).switch_to_default_content()
                for frame in frames:
                    super(RemoteWrapper, self).switch_to_frame(frame)
                orig_frames[:] = frames
            except:
                # Attempt to revert the positioning in the frames chain
                super(RemoteWrapper, self).switch_to_default_content()
                for frame in orig_frames:
                    super(RemoteWrapper, self).switch_to_frame(frame)
                raise
                
    def get_current_frame(self, window_handle=None):
        """Returns the frame locator for the given window.
        
        @param window: The window handle
        """
        if window_handle is None:
            window_handle = self.current_window_handle
        return '/' + '/'.join(self._frames.setdefault(window_handle, []))

    def switch_to_default_content(self):
        """Switches to the topmost frame (aka _top)."""
        return self.switch_to_frame('/')

    def switch_to_window(self, window_name, frame=None, timeout=3):
        """Switching the window automatically resets the current frame to _top.
        
        @param window_name: Window handle or name
        @param frame: Frame path to set inside the window. By default it'll set 
        the last frame path and if none is set it'll be /.
        @param timeout: Wait this long for the window to become available.
        @type timeout: int (seconds)
        """
        interval = 0.1
        now = start = time.time()
        
        while True:
            try:
                super(RemoteWrapper, self).switch_to_window(window_name)
                # Kill the cached value
                self._current_window_handle = None
                break
            except NoSuchWindowException:
                LOG.debug('Window %s not yet present.', window_name)
                if now - start >= timeout:
                    raise

            time.sleep(interval)
            now = time.time()

        if frame is None:
            frame = self.get_current_frame()
        self.switch_to_frame(frame, forced=True)

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

    def open_window(self, location='', name=None, tokens=''):
        """Opens up a new tab or window."""
        if name is None:
            name = uuid.uuid4().hex
        script = "window.open('%s','%s', '%s')" % (location, name, tokens)
        super(RemoteWrapper, self).execute_script(script)
        return name

    def maximize_window(self):
        if not self.name in ('chrome'):
            self.set_window_position(0, 0)
            self.set_window_size(1366, 768)
        else:
            LOG.warning("maximize_window not supported in %s." % self.name)

    def wait(self, value=None, by=By.ID, frame=None, it=Is.DISPLAYED, 
             negated=False, timeout=10, interval=0.1, stabilize=0, element=None, 
             test=None, multiple=False):
        """Waits for an element to satisfy a certain condition.
        
        @param value: the locator 
        @type value: str
        @param by: the locator type, one of: ID, XPATH, LINK_TEXT, NAME, 
                   TAG_NAME, CSS_SELECTOR, CLASS_NAME
        @type by: enum
        @param frame: the frame path (e.g. /topframe/subframe, default: current frame)
        @type frame: str
        @param it: condition, one of: DISPLAYED, SELECTED, ENABLED, PRESENT or 
                   TEST
        @type it: enum
        @param negated: negate the condition if true
        @type negated: bool
        @param timeout: timeout (default: 10 sec)
        @type timeout: int
        @param interval: polling interval
        @type interval: int
        @param stabilize: how long to wait after the condition is satisfied to
                          make sure it doesn't change again (default: 0 sec)
        @type stabilize: int
        @param element: parent element
        @type element: WebElement instance
        @param test: complex condition callback, called with (element, exception)
        @type test: callable
        """

        f = {}
        f['by'] = by
        f['value'] = value
        f['negated'] = negated and 'not' or 'to be'
        
        if frame is None:
            f['frame'] = '*current*'
        else:
            f['frame'] = frame
        
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
        
        if multiple and not test:
            raise TypeError('When testing for multiple elements a test callback needs to be specified.')

        if test:
            assert callable(test), '"test" must be a callback function with 2 params: element and exception.'

        now = start = time.time()
        e = None
        stable_time = 0
        
        while now - start < timeout:
            good = False
            try:
                # Caveat: If this is the first iteration *and* we're using a 
                # relative frame *and* switch_to_frame fails halfway, then the 
                # subsequent iterations will all fail! 
                if frame:
                    self.switch_to_frame(frame)
                    # Absolutize the frame (in case the one provided was relative)
                    frame = self.get_current_frame()

                e = element.find_elements(by=by, value=value) if multiple \
                    else element.find_element(by=by, value=value)

                #LOG.debug(e)
                if multiple or it == Is.TEST:
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
                #elif not (sum(map(lambda x:getattr(x, it)(), e)) == len(e) if multiple else getattr(e, it)() ^ (not negated)):
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
                elif (it in (Is.PRESENT, Is.DISPLAYED) and negated):
                    LOG.debug("Condition '%s' met.", c_text)
                    good = True
                LOG.debug("Waiting for '%s'.", c_text)
            except WebDriverException, exc:
                LOG.debug("Selenium is confused: '%s'.", exc)

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
