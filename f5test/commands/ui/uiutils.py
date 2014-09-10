'''
Created on Aug 30, 2013

@author: Andrei Dobre
'''
from base import SeleniumCommand
# from ...interfaces.config import ConfigInterface, DeviceAccess
# from ...interfaces.selenium import By
from f5test.utils.wait import wait
from f5test.base import AttrDict
from selenium.common.exceptions import NoSuchElementException, \
                                StaleElementReferenceException, \
                                ElementNotVisibleException
from f5test.interfaces.selenium import ActionChains
from f5test.interfaces.selenium.driver import By, Is
import logging
import re
# import time

LOG = logging.getLogger(__name__)


webel_grab = None
class WebelGrab(SeleniumCommand):  # @IgnorePep8
    """Will return a list of dictionaries that has requested attributes and
    properties of a given webel (by xpath/css/did).
    If no additional webel properties or attributes requested,
        it will fetch text by default.
    By default will fetch properties and attributes of the webel
        even if the webel is not currently visible;
    Webel needs to exist on the page though.

    @type xpath,css,did: str
    @param xpath,css,did: takes an xpath,css class or webel id

    @type attr: list
    @param attr: takes a list of attributes of the webel corresponding to the xpath

    @param prop: takes a list of properties of the webel corresponding to the xpath
    @return: a list of dicts, or [], even if there is no such element.
            Returning [] is good as one can iterate through empty list.

    @type use_js: bool
    @param use_js: Default True. To use js (force) to fetch text

    """
    def __init__(self, xpath=None, did=None, css=None, attr=None, prop=None,
                 use_js=True,
                 *args, **kwargs):
        super(WebelGrab, self).__init__(*args, **kwargs)

        if not xpath and not did and not css:
            LOG.error("/webel_grab/misuse - at least one param: xpath/css/did")
            raise NoSuchElementException
        if (prop is None) and (attr is None):
            prop = ["text"]
        if attr is None:
            attr = []
        if prop is None:
            prop = []
        self.xpath = xpath
        self.did = did
        self.css = css
        self.attr = attr
        self.prop = prop
        self.use_js = use_js

    def setup(self):
        s = self.api
        # To Do: Validate xpath el
        rlist = []
        using = None
        container = []
        try:
            if self.xpath:
                using = "xpath"
                container = s.find_elements_by_xpath(self.xpath)
            elif self.css:
                using = "css"
                container = s.find_elements_by_css_selector(self.css)
            elif self.did:
                using = "id"
                container = s.find_elements_by_id(self.did)
            for el in container:
                dic_per_tag = AttrDict()
                if self.attr != []:
                    for a_id in self.attr:
                        dic_per_tag[a_id] = el.get_attribute(a_id)
                if self.prop != []:
                    for p_id in self.prop:
                        if p_id == 'text':
                            if self.use_js:
                                text = s.execute_script("return arguments[0].innerHTML", el)
                            else:
                                text = el.text
                            dic_per_tag['text'] = text
                        elif p_id == 'id':
                            dic_per_tag['id'] = el.id
                        elif p_id == 'tag_name':
                            dic_per_tag['tag'] = el.tag_name
                        elif p_id == 'is_displayed':
                            dic_per_tag['is_displayed'] = el.is_displayed()
                        elif p_id == 'is_enabled':
                            dic_per_tag['is_enabled'] = el.is_enabled()
                        else:
                            dic_per_tag[p_id] = el.get_attribute(p_id)
                rlist.append(dic_per_tag)
            LOG.debug('/webel_grab/.list returned: {0} dict(s) in list for '
                      '{2}: [{1}]. LIST=[{3}]'
                      .format(len(rlist),
                              self.xpath or self.css or self.did,
                              using, rlist))
            return rlist
        except NoSuchElementException:
            return rlist
        except StaleElementReferenceException:
            return rlist


def wait_for_text_in_webel(text, xpath=None, did=None, css=None,
                           mtm=False,
                           attr=None,
                           textineach=False,
                           prop=None,
                           negated=False, timeout=10,
                           usedin=None,
                           *args, **kwargs):
    """Wait for a text (or multiple text) to appear within a list of elements

    @param text: Mandatory. String to search for.
                If regex_transform is used, it will break it down based on
                normal separators and will try to match substrings one after the other.
    @type text: string

    @param xpath, css, did: At least one Mandatory. defaulting to xpath.
                takes an xpath, css or an webel id to click on
    @type xpath, css, did: str

    Optional Parameters:

    @param mtm: default False. Multiple "AND" Text Only Match.
                    Will break down the string into substrings
                    so it can match all of them
                    (one after the other - lookahead assertion)
                    into the received el(s) list of attributes/props
                    Keeps text and numbers only, but also keeps:
                    - single spaces;
                    - "-"
                    - "_"
                    For Multi-match, in between desired texts,
                    use special chars like:
                    - "*" or
                    - "\" or
                    - ":" (etc.)
    @type mtm: bool

    @param attr: Default None. Look into received specific attributes.
                E.g. ['class', 'style']
    @type attr: list of strings

    @param prop: Default: ['text', 'is_displayed'].
                1. Will look into the element text. One should not remove this prop.
                2. Will look to see if the element is displayed.
                    (remove this and will not look for True on this property)
    @type prop: list of strings

    @param negated: default False. Inverts action. Makes sure the text is not in the el
    @type negated: bool

    @param timeout: default 10 seconds.
                    It will retry the search for 10 seconds.
                    Does not matter if used in conjunction with negated=True
    @type timeout: int

    @return: Returns the generated list of the search if found or fail.
             If negated, returns True or False"""

    usedin = "{0}/waitfortext/".format(usedin if usedin else "")

    x = []
    if not prop and not attr:
        prop = ['text', 'is_displayed']
    if not prop:
        prop = []
    if not attr:
        attr = []
    ftext = None
    if mtm:
        # Matches one or more non-alphanumeric characters or "_" or space:
        # ([^\w\s]|_)- followed by either a space or the end of string ($).
        # The (?= ) construct is a lookahead assertion:
        # it makes sure that a matching space is not included in the match,
        # so it doesn't get replaced; only the [\W_]+ gets replaced.
        # Then all (such) or new line chars\specials are replaced with ".*?"
        # Use "*" or "\" etc. for multi text assertion.
        ftext = text.encode('utf-8')
        try:
            ftext = re.sub(
                r'([^\w\s]|_)+(?=\s|$)|(\n|\(|\)|\+|\[|\]|\{|\}|\\|\/|\*)', \
                ".*?", ftext)
        except Exception, e:
            LOG.debug("{0}Error in re.sub:".format(usedin))
            raise e
        while ftext[-3:] == ".*?":
            ftext = ftext[:-3]
        LOG.debug("{0}text: '{1}'/Formed regex text is: '{2}'".format(usedin, text, ftext))

    def to_appear():
        try:
            x = webel_grab(xpath=xpath, did=did, css=css,
                            attr=attr, prop=prop,
                            *args, **kwargs)
            LOG.debug("{0}. Looking for '{1}'; Grabbed: '{2}'"
                                 .format(usedin, text, x))
            if negated and x == []:
                return True
            occured = False
            if x != [] and 'text' in prop:
                for el in x:
                    if textineach:
                        occured = False
                    ret = None
                    # look in text properties
                    eltext = el.text
                    if mtm:  # if using multi text match (regex lookahead assert)
                        eltext = eltext.encode('utf-8')
                        ret = re.search(ftext, eltext, re.S | re.U)
                        LOG.debug("{0}current re.search result: {1}"
                                  .format(usedin, ret))
                        # if looking for a visible element
                        if 'is_displayed' in prop and ret:
                            if el.is_displayed:
                                LOG.debug("{0}regex:'{1}'/. Found '{2}' in '{3}'"
                                         .format(usedin, ftext, text, el.text,))
                                occured = True
                        # if it does not matter if the element is visible or not
                        elif ret:
                            LOG.debug("{0}regex:'{1}'/. Found '{2}' in '{3}'"
                                     .format(usedin, ftext, text, el.text,))
                            occured = True
                    else:  # regular exact text match search (old style)
                        # if looking for a visible element
                        if 'is_displayed' in prop and text in eltext:
                            if el.is_displayed:
                                LOG.debug("{0}exact match/Found '{1}' in '{2}'"
                                         .format(usedin, text, el.text))
                                occured = True
                        # if it does not matter if the element is visible or not
                        elif text in eltext:
                            LOG.debug("{0}exact match/Found '{1}' in '{2}'"
                                         .format(usedin, text, el.text))
                            occured = True
            # (also) look in attributes (if not found already in properties)
            if x != [] and attr != [] and not occured:
                for el in x:
                    for val in attr:
                        LOG.debug("{0}looking in attr [{1}]; got: [{2}]"
                                            .format(usedin, val, el.get(val)))
                        # LOG.info("{0}looking in attr [{1}]; got: [{2}]"
                        #                    .format(usedin, val, el.get(val)))
                        if textineach:
                            occured = False
                        # if using multi text match (regex lookahead assert)
                        if mtm:
                            ret = None
                            eltext = el.get(val)
                            eltext = eltext.encode('utf-8')
                            ret = re.search(ftext, eltext, re.S | re.U)
                            LOG.debug("{0}current re.search result: {1}"
                                      .format(usedin, ret))
                            if ret:
                                LOG.debug("{0}regex:'{1}'/. Found '{2}' in '{3}'"
                                         .format(usedin, ftext, text, el.get(val)))
                                occured = True
                            else:
                                if textineach:
                                    break
                        # regular exact text match search (old style)
                        else:
                            if text in el.get(val):
                                occured = True
                            else:
                                if textineach:
                                    break
                    if textineach and not occured:
                        break
            if occured and not negated:
                return True
            if not occured and negated:
                return True
        except NoSuchElementException:
            if negated:
                return negated
            else:
                pass
        except StaleElementReferenceException:
            if negated:
                return negated
            else:
                pass
        except Exception, e:
            LOG.debug("{0}Error:".format(usedin))
            raise e
    wait(to_appear, interval=1, timeout=timeout,
         progress_cb=lambda x: '{0}. Still looking for text "{1}"...'
                                .format(usedin, text),
         timeout_message="%s. Did Not Find text '%s' in {0}s" % (usedin, text))
    return x


webel_click = None
class WebelClick(SeleniumCommand):  # @IgnorePep8
    """Clicks on given xpath or css or did
    - unless turned off, it will retry until click or timeout
    - ability to right click
    - ability to force click (js)
    - with the ability to wait for other elements to appear or disappear (negated)
        after the fact:
        ids, xpaths, css (list of ids are supported if the given var returns lists)
    - with the ability to wait for a text in a webel or even in webel attributes
        to appear or disappear (negated) after the fact
    - it will wait for all of the above one after the other

    @param xpath, css, did: At least one Mandatory. defaulting to xpath.
                takes an xpath, css or an webel id to click on
    @type xpath, css, did: str

    Optional Parameters:

    @param retryit: default True, to retry in case the element is not there yet
    @type retryit: bool

    @param waitforxpath, waitforid, waitforcss: takes an xpath to wait for it
            to become visible after the fact
    @type waitforxpath, waitforid, waitforcss: str

    @param waitfortext: text to wait for in a different web element(s) or attr/prop of such
    @type waitfortext: str
    @param attr: list of attributes/props of an web element where a text can be searched within
    @type attr: list of strings, eg: ['value', 'class']
    @param inxpath, incss, indid: the webel identifier where to look for the text
    @type inxpath, incss, indid: str

    @type negated,jsclick: bool
    @param negated: to wait for the element to not be there anymore (after the fact only)
    @param jsclick: jsclick (even if invisible) (force). Default False.

    @param timeout: how long to wait for each wait action
    @type timeout: int

    @param right_click: default False, to right click on that el.
    @type right_click: bool

    @return: webel pos in browser if found and clicked, or fail
    """

    def __init__(self, xpath=None, css=None, did=None,
                 waitforid=None, waitforxpath=None, waitforcss=None,
                 waitfortext=None, inxpath=None, incss=None, indid=None, attr=None,
                 negated=False,
                 right_click=False,
                 jsclick=False,
                 retryit=True, timeout=5,
                 *args, **kwargs):
        super(WebelClick, self).__init__(*args, **kwargs)
        self.xpath = xpath
        self.css = css
        self.did = did
        self.waitforid = waitforid
        self.waitforxpath = waitforxpath
        self.waitforcss = waitforcss
        self.waitfortext = waitfortext
        self.inxpath = inxpath
        self.incss = incss
        self.indid = indid
        self.negated = negated
        self.timeout = timeout
        self.jsclick = jsclick
        if attr is None:
            attr = []
        self.attr = attr
        self.retryit = retryit
        self.right_click = right_click

    def setup(self):
        # To Do: Validate xpath/css/did el
        self.using = 'xpath'
        self.s = None

        def retrythis():
            button = None
            isit = False
            try:
                LOG.debug("/WebelClick/{0}/Fetching:'{1}'"
                          .format(self.using, self.xpath or self.css or self.did))
                if self.xpath:
                    button = self.api.find_element_by_xpath(self.xpath)
                elif self.css:
                    self.using = 'css'
                    button = self.api.find_element_by_css_selector(self.css)
                elif self.did:
                    self.using = 'id'
                    button = self.api.find_element_by_id(self.did)
                if button:
                    if self.jsclick and not self.right_click:
                        self.s = self.api.execute_script("return arguments[0].click()", button)
                    elif not self.jsclick and self.right_click:
                        LOG.debug("/WebelClick/{0}/Entering Action Chains."
                          .format(self.using))
                        action = ActionChains(self.api)
                        # LOG.debug("/WebelClick/{0}/In Action Chains: Move to El.".format(self.using))
                        action.move_to_element(button)
                        # LOG.debug("/WebelClick/{0}/In Action Chains: Stabilizing 1 sec.".format(self.using))
                        # time.sleep(1)
                        # LOG.debug("/WebelClick/{0}/In Action Chains: Context Click.".format(self.using))
                        action.context_click()
                        # LOG.debug("/WebelClick/{0}/In Action Chains: Perform().".format(self.using))
                        self.s = action.perform()
                        LOG.debug("/WebelClick/{0}/After Action Chains: Perform(): Finished."
                          .format(self.using))
                    elif not self.jsclick and not self.right_click:
                        self.s = button.click()
                    else:  # force js right click # NOT IMPLEMENTED YET # not sure is needed
                        # self.s = self.api.execute_script("return arguments[0].context_click()",
                        #                     button)
                        LOG.error("/WebelClick/Can't force right click on invisible element yet.")
                        pass
                isit = True
            except NoSuchElementException:
                isit = False
                LOG.debug("/WebelClick/{0}/except: NoSuchElementException. Passing."
                          .format(self.using))
                pass
            except ElementNotVisibleException:
                isit = False
                LOG.warning("/WebelClick/{0}/'{1}'/ElementNotVisibleException! Passing."
                            .format(self.using, self.xpath or self.css or self.did))
                pass
            except Exception, e:
                raise e
            return isit
        if self.retryit:
            wait(retrythis, interval=1, timeout=self.timeout,
                 progress_cb=lambda x: "/WebelClick/{0}/'{1}'/Retry Click..."
                            .format(self.using, self.xpath or self.css or self.did),
                 timeout_message="/WebelClick/%s/'%s'/Could not Click "
                 "it after {0}s" % (self.using, (self.xpath or self.css or self.did)))
        else:
            retrythis

        if self.waitforid:
            self.s = self.api
            self.s = self.s.wait(self.waitforid, negated=self.negated, timeout=self.timeout)
        if self.waitforxpath:
            self.s = self.api
            self.s = self.s.wait(self.waitforxpath, By.XPATH, negated=self.negated,
                       timeout=self.timeout)
        if self.waitforcss:
            self.s = self.api
            self.s = self.s.wait(self.waitforcss, By.CSS_SELECTOR, negated=self.negated,
                       timeout=self.timeout)
        if self.waitfortext and (self.inxpath or self.incss or self.indid):
            wait_for_text_in_webel(text=self.waitfortext,
                                   xpath=self.inxpath,
                                   css=self.incss,
                                   did=self.indid,
                                   attr=self.attr,
                                   negated=self.negated, timeout=self.timeout,
                                   ifc=self.ifc)
        return self.s
