'''
Created on April 24, 2014

@author: john.wong@f5.com
'''
from .base import IcontrolRestCommand
from ...utils.wait import wait
from ...interfaces.testcase import ContextHelper
import logging

LOG = logging.getLogger(__name__)
HA_TIMEOUT = 120

wait_item_sync = None
class WaitItemSync(IcontrolRestCommand):  # @IgnorePep8
    """Waits until 'item' syncs to 'device'.

    @param device: BIGIQ
    @type device: DeviceAccess
    @param item: item response
    @type name: dict

    @return: response from specified device
    """
    def __init__(self, device, item, timeout=HA_TIMEOUT, *args, **kwargs):
        super(WaitItemSync, self).__init__(*args, **kwargs)
        self.device = device
        self.uri = item.selfLink
        self.item = item
        self.timeout = timeout

    def prep(self):
        self.context = ContextHelper(__file__)

    def cleanup(self):
        self.context.teardown()

    def setup(self):
        name = self.item.name or self.item.templateName or self.item.title
        generation = self.item.generation

        def progress(resp):
            msg = "Waiting until '{0}' syncs".format(name)
            return msg

        LOG.info("Waiting until '{0}' syncs on {1}".format(name, self.device))
        p = self.context.get_icontrol_rest(device=self.device).api
        resp = wait(lambda: p.get(self.uri),
                    condition=lambda resp: resp.generation >= generation,
                    progress_cb=progress,
                    timeout=self.timeout, interval=2)

        return resp

wait_item_removed = None
class WaitItemRemoved(IcontrolRestCommand):  # @IgnorePep8
    """Waits until 'item' is removed from 'device'.

    @param device: BIGIQ
    @type device: DeviceAccess
    @param item: item to be deleted
    @type item: dict or post response of object

    @return: None
    """
    def __init__(self, device, item, timeout=HA_TIMEOUT, timeout_message=None,
                 *args, **kwargs):
        super(WaitItemRemoved, self).__init__(*args, **kwargs)
        self.device = device
        self.item = item
        self.uri = item.selfLink.rsplit('/', 1)[0]
        self.timeout = timeout
        self.timeout_message = timeout_message

    def prep(self):
        self.context = ContextHelper(__file__)

    def cleanup(self):
        self.context.teardown()

    def setup(self):
        p = self.context.get_icontrol_rest(device=self.device).api
        LOG.info("selfLink: {0}".format(self.item.selfLink))
        resp = p.get(self.uri)['items']
        if [item.selfLink for item in resp]:
            LOG.info("Verifying {0} removed from {1}".format(self.item.selfLink, self.device))
            wait(lambda: p.get(self.uri)['items'],
                 condition=lambda resp: self.item.selfLink not in [item.selfLink for item in resp],
                 progress_cb=lambda resp: "Waiting until {0} removed from {1}".format(self.item.selfLink, [item.selfLink for item in resp]),
                 timeout=self.timeout, interval=2,
                 timeout_message=self.timeout_message)

        else:
            LOG.info("selfLink not on {0}".format(self.device))
