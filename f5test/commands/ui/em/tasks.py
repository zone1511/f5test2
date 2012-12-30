from ..base import SeleniumCommand
from ....interfaces.selenium import By
from ....interfaces.selenium.driver import ElementWait, NoSuchElementException
from ..common import login
import logging

LOG = logging.getLogger(__name__) 


class TaskWaitError(Exception):
    pass


class TaskWait(ElementWait):
    
    def __init__(self, interface, *args, **kwargs):
        self._interface = interface
        return super(TaskWait, self).__init__(interface.api, *args, **kwargs)

    def test_result(self, result):
        if result.text in ('Finished', 'Canceled'):
                return True
        return False

    def test_error(self, exc_type, exc_value, exc_traceback):
        b = self._interface.api
        loggedout = False
        try:
            b.find_element_by_id('loginform')
            b.switch_to_default_content()
            loggedout = True
        except NoSuchElementException:
            pass

        if loggedout:
            login(ifc=self._interface)
            #return True
            raise TaskWaitError('Log out occurred during the task!')


wait_for_task = None
class WaitForTask(SeleniumCommand):
    """Waits for the current task to finish. Assumes the page is the task details.

    @param timeout: Wait this many seconds for the task to finish (default: 300).
    @type timeout:  int
    @param interval: Polling interval (default: 12)
    @type interval:  int
    
    @return: True if task failed, false otherwise
    @rtype: bool
    """
    def __init__(self, timeout=300, interval=15, *args, **kwargs):
        super(WaitForTask, self).__init__(*args, **kwargs)
        self.timeout = timeout
        self.interval = interval

    def setup(self):
        b = self.api

        w = TaskWait(self.ifc, timeout=self.timeout, interval=self.interval)
        w.run(value='#progress_span .text', by=By.CSS_SELECTOR, frame='/contentframe')

        e = b.find_element_by_id('progress')
        css_class = e.get_attribute('class').split()
        return 'completewitherrors' in css_class

