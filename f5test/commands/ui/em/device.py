from ..base import SeleniumCommand
from ..common import browse_to, get_cell_xpath, wait_for_loading, \
    browse_to_tab
from ....interfaces.selenium.driver import By
import logging
import urlparse

LOG = logging.getLogger(__name__) 


refresh = None
class Refresh(SeleniumCommand):
    """Refresh one device given the access address."""
    def __init__(self, mgmtip, timeout=60, *args, **kwargs):
        super(Refresh, self).__init__(*args, **kwargs)
        self.mgmtip = [mgmtip] if isinstance(mgmtip, basestring) else mgmtip
        self.timeout = timeout

    def setup(self):
        b = self.api
        
        browse_to('Enterprise Management | Devices', ifc=self.ifc)
        b.wait('tableForm:emDeviceTable_table', frame='/contentframe')

        for mgmtip in self.mgmtip:
            LOG.debug('Selecting %s...', mgmtip)
            row_xpath = get_cell_xpath('tableForm:emDeviceTable_table', 
                                       'Device Address', mgmtip, ifc=self.ifc)
            e = b.find_element_by_xpath("%s/td[1]/span/input" % row_xpath)
            assert e.is_enabled(), "Checkbox for %s is not enabled. " \
                            "Possible causes: device engaged in another task or " \
                            "emdeviced is down." % mgmtip
            e.click()
        LOG.info('Refreshing %d device(s)...', len(self.mgmtip))
        b.wait('tableForm:emDeviceTable_mask', negated=True)

        e = b.find_element_by_name('tableForm:emDeviceTable:updateStatusButton')
        e.click()
        wait_for_loading(css='success', timeout=self.timeout, ifc=self.ifc)
        
        e = b.find_element_by_xpath("%s/td[2]/img" % row_xpath)
        assert not 'status_device_unreachable.gif' in e.get_attribute('src'), \
               "Device unreachable after refresh!"


create_pinned_archive = None
class CreatePinnedArchive(SeleniumCommand):
    """Create a pinned archive through Devices->Device->Archives.
    
    @param mgmtip: The access address.
    @type mgmtip: str
    @param name: The archive name.
    @type name: str
    """
    def __init__(self, mgmtip, name, *args, **kwargs):
        super(CreatePinnedArchive, self).__init__(*args, **kwargs)
        self.mgmtip = mgmtip
        self.name = name

    def setup(self):
        b = self.api
        
        browse_to('Enterprise Management | Devices', ifc=self.ifc)
        b.wait('tableForm:emDeviceTable_table', frame='/contentframe')

        mgmtip = self.mgmtip
        LOG.info('Selecting %s...', mgmtip)

        row_xpath = get_cell_xpath('tableForm:emDeviceTable_table', 
                                   'Device Address', mgmtip, ifc=self.ifc)
        e = b.find_element_by_xpath("%s/td[3]/a" % row_xpath)
        assert e.is_enabled(), "Checkbox for %s is not enabled. " \
                        "Possible causes: device engaged in another task or " \
                        "emdeviced is down." % mgmtip
        e.click().wait('device_table_div', timeout=20)
        browse_to_tab('Archives', ifc=self.ifc)
        
        LOG.info("Creating archive %s...", self.name)
        button = b.wait('tableForm:archiveTable:createPinnedArchiveButton_new',
                        frame='/contentframe')
        filename = button.click().wait('tableForm:pinnedArchiveFormtable:fileName')
        filename.send_keys(self.name)
        create = b.find_element_by_name("tableForm:createButton")
        create.click()
        wait_for_loading(ifc=self.ifc)
        
        e = b.find_element_by_xpath("//table[@id='tableForm:archiveTable_table']"
                                    "//a[normalize-space(.)='%s.ucs']" % self.name)
        uri = e.get_attribute('href')
        qs = urlparse.urlparse(uri).query
        LOG.info(qs)
        params = urlparse.parse_qs(qs)
        return params['uid'][0]


cancel_running_task = None
class CancelRunningTask(SeleniumCommand):
    """Cancel a running task.
    
    @param job_uid: The task ID.
    @type job_uid: str or int
    """
    def __init__(self, job_uid, *args, **kwargs):
        super(CancelRunningTask, self).__init__(*args, **kwargs)
        self.job_uid = job_uid

    def setup(self):
        b = self.api
        LOG.info('Cleaning running task...')
        browse_to('Enterprise Management | Tasks', ifc=self.ifc)
        table = b.wait('task_monitor_list', frame='/contentframe')
        row_xpath = get_cell_xpath('task_monitor_list', 'ID', self.job_uid, 
                                   ifc=self.ifc)
        link = table.find_element_by_xpath('%s/td[3]/a' % row_xpath)
        cancel_button = link.click().wait('stop', By.NAME)
        cancel_button.click().wait('task_monitor_list')
