from ..base import SeleniumCommand
from ..common import browse_to
#from ....interfaces.config import ConfigInterface
#from ...base import AttrDict
import logging

LOG = logging.getLogger(__name__) 


enable_stats = None
class EnableStats(SeleniumCommand):
    """Enable stats collection."""
    def __init__(self, enable=True, *args, **kwargs):
        super(EnableStats, self).__init__(*args, **kwargs)
        self.enable = enable

    def setup(self):
        b = self.api
        
        browse_to('Enterprise Management | Statistics : Options | Data Collection', 
                            ifc=self.ifc, version=self.version)
        b.switch_to_frame('contentframe')
        e = b.wait('enableDataCollection')
        
        #e = b.find_element_by_id('enableDataCollection')
        value = e.get_attribute('value')
        old_enable = True if value == 'true' else False
        
        enable = self.enable
        if enable == True:
            o = e.find_element_by_xpath('option[text()="Enabled"]')
        else:
            o = e.find_element_by_xpath('option[text()="Disabled"]')
        
        o.click()
        #e = b.find_element_by_xpath('//table[@id="optionsButtonGrid"]//input[@value="Save Changes"]')
        #e.click()
        
        if old_enable and enable is False:
            e = b.wait('disableStatsBtn')
            #e = b.find_element_by_id('disableStatsBtn')
            e.click()
            b.wait(value='disableStatsDlg:dialog')
            e = b.find_element_by_xpath('//div[@id="disableStatsDlg:dialog"]//input[@value="Confirm"]')
            e.click().wait('disableStatsDlg:dialog', negated=True)
        elif old_enable is False and enable:
            e = b.wait('enableStatsBtn')
            #e = b.find_element_by_id('enableStatsBtn')
            e.click()
            b.wait(value='enableStatsDlg:dialog')
            e = b.find_element_by_xpath('//div[@id="enableStatsDlg:dialog"]//input[@value="Confirm"]')
            e.click().wait('enableStatsDlg:dialog', negated=True)
        else:
            pass
