'''
Created on Dec 2, 2011

@author: jono
'''
from ..base import SeleniumCommand
from ..common import browse_to
from ....base import Options
from ....utils.wait import wait
from ..common import get_cell_xpath
from ....interfaces.selenium.driver import By, Is
import logging

LOG = logging.getLogger(__name__) 


create = None
class Create(SeleniumCommand):
    """Create a new report.
    
    @param report_type: Report type (e.g. 'Capacity Planning' or 'Device Inventory')
    @type report_type: str
    @param name: Report name (e.g. 'my report')
    @type name: str
    @param options: Report type (e.g. 'Capacity Planning' or 'Device Inventory')
    @type options: Options instance
    """
    def __init__(self, report_type, name, options=None, *args, **kwargs):
        super(Create, self).__init__(*args, **kwargs)
        self.report_type = report_type
        self.name = name
        self.options = options or Options()

    def do_select_devices(self, sequence, table_id):
        b = self.ifc.api
        for device in sequence:
            mgmtip = device.access_address
            LOG.info('Selecting %s...', mgmtip)
    
            row_xpath = get_cell_xpath(table_id, 'Device Address', mgmtip, 
                                       ifc=self.ifc)
            e = b.find_element_by_xpath("%s/td[1]/input" % row_xpath)
            assert e.is_enabled(), "Checkbox for %s is not enabled. " \
                "Possible causes: device engaged in another task or emdeviced "\
                "is down." % mgmtip
            e.click()

    def setup(self):
        b = self.api
        o = self.options
        
        browse_to('Enterprise Management | Reports', ifc=self.ifc)
        b.wait('form:typeTable', frame='/contentframe')
        type_row = b.find_element_by_xpath("//table[@id='form:typeTable']"
                                           "//span[normalize-space(text())='%s']" % 
                                           self.report_type)
        type_row.click().wait("//label[@id='form:typeLabel' "
                              "and normalize-space(text())='%s']" % 
                              self.report_type, By.XPATH)

        # Fill in the report name
        create = b.find_element_by_id('form:create')
        button = create.click().wait('next')
        name_input = b.find_element_by_id('reportName')
        name_input.click()
        name_input.send_keys(self.name)

        if self.report_type not in ('Certificate Inventory', 'Device Inventory'):
            table = b.find_element_by_css_selector('table.deviceTable')
            table_id = table.get_attribute('id')
            if o.devices:
                self.do_select_devices(o.devices, table_id)
            else:
                select_all = b.find_element_by_xpath("//table[@id='%s']/thead/tr"
                                                     "/th/input" % table_id)
                select_all.click()

        submit = button.click().wait('submitButton')
        submit.click().wait('form:reportGrid')
        
        LOG.info('Waiting for report to complete...')
        tr_xpath = "//table[@id='form:schedInstanceTable']/tbody/" \
                 "tr[descendant::span[normalize-space(text())='Completed " \
                 "Reports']]/following::tr[td[2]/div='%s']" % self.name
        b.wait(tr_xpath, By.XPATH, timeout=60)
        b.wait("%s/td[2]/div/img[@class='runningStatus']" % tr_xpath, By.XPATH, 
               negated=True, it=Is.PRESENT, timeout=60)
        LOG.info('Report done.')
        
        return tr_xpath


delete = None
class Delete(SeleniumCommand):
    """Delete an existing report.
    
    @param report_type: Report type (e.g. 'Capacity Planning')
    @type report_type: str
    @param name: Report name (e.g. 'my report')
    @type name: str
    """
    def __init__(self, report_type, name, *args, **kwargs):
        super(Delete, self).__init__(*args, **kwargs)
        self.report_type = report_type
        self.name = name

    def setup(self):
        b = self.api
        
        browse_to('Enterprise Management | Reports', ifc=self.ifc)
        b.wait('form:typeTable', frame='/contentframe')
        type_row = b.find_element_by_xpath("//table[@id='form:typeTable']"
                                           "//span[normalize-space(text())='%s']" % 
                                           self.report_type)
        type_row.click().wait("//label[@id='form:typeLabel' "
                              "and normalize-space(text())='%s']" % 
                              self.report_type, By.XPATH)

        tr_xpath = "//table[@id='form:schedInstanceTable']/tbody/" \
                 "tr[descendant::span[normalize-space(text())='Completed " \
                 "Reports']]/following::tr[td[2]/div='%s']" % self.name

        # Due to async nature of the UI do a retry-loop on the delete operation
        # since I've seen many StaleElement exceptions occurring in 
        # is_selected() or the following click().
        def try_delete():
            e = b.find_element_by_xpath('%s/td[1]/div/input' % tr_xpath)
            if not e.is_selected():
                delete = e.click().wait('form:deleteButton', it=Is.ENABLED)
            else:
                delete = b.find_element_by_id('form:deleteButton')
            confirm = delete.click().wait('delDialogForm:confirm')
            confirm.click().wait('deleteDialog', negated=True)
            return True
        
        wait(try_delete, timeout=60)
