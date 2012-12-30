from ..base import SeleniumCommand
from ..common import browse_to, wait_for_loading
from ... import icontrol as ICMD
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

        v = self.ifc.version
        icifc = self.ifc.get_icontrol_interface()
        vdict = ICMD.system.parse_version_file(ifc=icifc)

        if v.product.is_em and v < 'em 2.3':
            locator = 'Enterprise Management | Statistics | Options | Data Collection'
        elif v.product.is_em and v < 'em 3.0':
            locator = 'Enterprise Management | Options | Statistics | Data Collection'
        else:
            locator = 'Statistics | Managed Devices | Options | Data Collection'
        browse_to(locator, ifc=self.ifc)
        b.switch_to_frame('/contentframe')

        if v.product.is_em and v < 'em 2.2':
            e = b.wait('enable_data_collection')
        else:
            e = b.wait('enableDataCollection', timeout=30)

        # @value of <select> is actually the value of the selected option.
        value = e.get_attribute('value')
        old_enable = True if value == 'true' else False

        enable = self.enable
        if enable == True:
            o = e.find_element_by_xpath('option[text()="Enabled"]')
        else:
            o = e.find_element_by_xpath('option[text()="Disabled"]')

        o.click()

        if v.product.is_em and v < 'em 2.2':
            e = b.find_element_by_name('save_collection_changes')
            e.click()
            wait_for_loading(css='success', ifc=self.ifc)
        # XXX: solar-topaz-em and allagasg are EM 3.1 but are missing certain UI changes.
        # This project check must be removed when these branches will be invalidated.
        elif v.product.is_em and vdict.get('project') in ('em-nsd',):
            e = b.find_element_by_id('saveBtn')
            e.click()
            wait_for_loading(css='success', ifc=self.ifc)
        else:
            if old_enable and enable is False:
                e = b.wait('disableStatsBtn')
                e.click()
                b.wait(value='disableStatsDlg:dialog')
                e = b.find_element_by_xpath('//div[@id="disableStatsDlg:dialog"]//input[@value="Confirm"]')
                e.click().wait('disableStatsDlg:dialog', negated=True)
            elif old_enable is False and enable:
                e = b.wait('enableStatsBtn')
                e.click()
                b.wait(value='enableStatsDlg:dialog')
                e = b.find_element_by_xpath('//div[@id="enableStatsDlg:dialog"]//input[@value="Confirm"]')
                e.click().wait('enableStatsDlg:dialog', negated=True)
            else:
                pass


get_stats_state = None
class GetStatsState(SeleniumCommand):
    """Get enabled stats collection state."""
    def setup(self):
        b = self.api

        v = self.ifc.version
        if v.product.is_em and v < 'em 3.0':
            locator = 'Enterprise Management | Options | Statistics | Data Collection'
        else:
            locator = 'Statistics | Managed Devices | Options | Data Collection'
        browse_to(locator, ifc=self.ifc)
        b.switch_to_frame('/contentframe')
        e = b.wait('enableDataCollection')

        # @value of <select> is actually the value of the selected option.
        value = e.get_attribute('value')
        return True if value == 'true' else False
