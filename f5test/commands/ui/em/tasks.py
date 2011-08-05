from ..base import SeleniumCommand
from ....interfaces.selenium import By, Is # ActionChains
#from ...interfaces.selenium.driver import StaleElementReferenceException
from ...base import AttrDict
import logging

LOG = logging.getLogger(__name__) 


wait_for_task = None
class WaitForTask(SeleniumCommand):
    """Waits for the current task to finish. Assumes the page is the task details.

    @param timeout: Wait this many seconds for the task to finish (default: 300).
    @type timeout:  int
    @param interval: Polling interval (default: 10)
    @type interval:  int
    
    @return: True if task failed, false otherwise
    @rtype: bool
    """
    def __init__(self, timeout=300, interval=10, *args, **kwargs):
        super(WaitForTask, self).__init__(*args, **kwargs)
        self.timeout = timeout
        self.interval = interval

    def setup(self):
        params = AttrDict()
        b = self.api

        def is_done(e, exc):
            if exc:
                LOG.debug(exc)
            
            if e:
                if e.text == 'Finished':
                    return True
                LOG.info(e.text)
            return False

        params.value = '#progress_span .text'
        params.it = Is.TEST
        params.by = By.CSS_SELECTOR
        params.frame = 'contentframe'
        params.test = is_done

        b.wait(timeout=self.timeout, interval=self.interval, **params)
        b.switch_to_frame('contentframe')
        e = b.find_element_by_id('progress')
        css_class = e.get_attribute('class').split()
        return 'completewitherrors' in css_class

