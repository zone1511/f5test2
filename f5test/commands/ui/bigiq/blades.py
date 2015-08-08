'''
Created on Aug 15, 2013

@author: jono
'''
from ..base import SeleniumCommand
from ....interfaces.selenium import By
import logging

LOG = logging.getLogger(__name__)


activate = None
class Activate(SeleniumCommand):  # @IgnorePep8
    """Activate blade and optionally clicks the +.

    @param name: The blade's name.
    @type name: str
    @param add: Also click on blade's + sprite?
    @type add: bool
    @return: The blade element
    """
    def __init__(self, name=None, add=False, *args, **kwargs):
        super(Activate, self).__init__(*args, **kwargs)
        self.name = name
        self.add = add

    def setup(self):
        b = self.api
        version = self.ifc.version

        # In 4.4 some modules (see below) are not using the new Angular UI.
        module = b.find_element_by_id('navMenuCurrentLink').text
        submodule = b.find_element_by_css_selector('#navMenuSublinks .active').text
        path = "%s|%s" % (module, submodule)
        bits = self.name.split('|')
        if len(bits) > 1 and bits[1] == '+':
            self.name = bits[0]
            self.add = True
        if version >= 'bigiq 4.4' and path not in ('Cloud|Overview',
                                                   'Security|Web Application Security') \
           or version >= 'bigiq 4.5' and path not in ('Security|Web Application Security'):
            blade_xpath = "//*[div[contains(@class, 'panelMain ') and descendant::*[contains(@class, 'panelHeader ') and descendant::*[text()='%s']]]]"
            blade = b.find_element_by_xpath(blade_xpath % self.name)
            header = blade.find_element_by_css_selector('.panelHeader')
            if blade.tag_name == 'dockedpanel':
                header.jquery_click()
            blade = b.wait("//panel[div[descendant::*[contains(@class, 'panelHeader ') and descendant::*[text()='%s']]]]" % self.name, By.XPATH)

            if self.add:
                bits = [] if self.add is True else self.add.split('|')
                plus = blade.find_element_by_css_selector('.panelAddButton')
                plus.jquery_click()
                if len(bits) > 1:
                    menu = blade.wait('.dropdown-menu', By.CSS_SELECTOR)

                    item = menu.find_element_by_xpath("//a[text()='%s']" % bits[1])
                    item.click()
                blade.wait("flyout", By.CSS_SELECTOR)

        else:
            blade_xpath = "//div[contains(@class, 'blade ') and descendant::div[contains(@class, 'headerLabel') and text()='%s']]"
            blade = b.find_element_by_xpath(blade_xpath % self.name)
            header = blade.find_element_by_css_selector('.bladeHeader')

            # Note: Low level jQuery click is used here because the header might be
            # docked and Selenium would try to force scroll into view to be able
            # to click right in the middle x,y of the .bladeHeader element.
            b.execute_script("return arguments[0].click()", header)

            # Note: The 0.5 delay is to cover the UI animation for shuffling around
            # the blades. There are no AJAX actions.
            blade.wait(".innerContainer", By.CSS_SELECTOR, stabilize=0.5)

            if self.add:
                plus = blade.find_element_by_css_selector('.bladeAddButton')
                b.execute_script("return arguments[0].click()", plus)
                blade.wait(".bladeSub", By.CSS_SELECTOR)

        return blade
