'''
Created on Jan 21, 2012

@author: jono
'''
from ..base import SeleniumCommand
from ..common import browse_to, wait_for_loading, browse_to_tab
from .tasks import wait_for_task
import logging
#import urlparse

LOG = logging.getLogger(__name__) 


sync_to = None
class SyncTo(SeleniumCommand):
    """Sync To Peer or Group."""

    def setup(self):
        b = self.api
        
        v = self.ifc.version
        success = True
        if v.product.is_em and v < 'em 3.0':
            browse_to('System | High Availability | ConfigSync', ifc=self.ifc)
            button = b.wait('SYNC_PUSH', frame='/contentframe')
    
            button.click()
            alert = b.switch_to_alert()
            alert.accept()
            LOG.info('Syncing...')
            wait_for_loading(ifc=self.ifc)
            success = not wait_for_task(timeout=600, ifc=self.ifc)
        else:
            browse_to('Device Management | Device Groups', ifc=self.ifc)
            table = b.wait('list_table', frame='/contentframe')
            links = table.find_elements_by_xpath('tbody//a')
            for a in links:
                dg = a.text
                a.click().wait('update')
                browse_to_tab('ConfigSync', ifc=self.ifc)
                button = b.wait('export', frame='/contentframe')
                td = b.find_element_by_xpath("//table[@id='properties_table']/tbody/tr/td[2]")
                status = td.text.strip()
                LOG.debug("%s: %s", dg, status)
                if status != 'In Sync':
                    button.click()
                    alert = b.switch_to_alert()
                    alert.accept()
                    LOG.info('Syncing %s...', dg)
                    wait_for_loading(ifc=self.ifc)
                    success &= not wait_for_task(timeout=600, ifc=self.ifc)
        
        return success
