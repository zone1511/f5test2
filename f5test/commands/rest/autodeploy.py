'''
Created on Feb 25, 2014

@author: dhandapani
'''

from ...interfaces.rest.emapi.objects.autodeploy import Image
from ...utils.wait import wait
from .base import IcontrolRestCommand

IMAGE_LOCATION = '/shared/images'
CONFIG_LOCATION = '/shared/configs'


wait_for_image = None
class WaitForImage(IcontrolRestCommand):  # @IgnorePep8
    """Waits for an image to either appear or disappear."""

    def __init__(self, rest, image_name, appear=True, *args, **kwargs):
        super(WaitForImage, self).__init__(*args, **kwargs)
        self.rest = rest
        self.image_name = image_name
        self.appear = appear

    def setup(self):

        def images_list():
            resp = self.rest.get(Image.URI)
            return [temp['filename'] for temp in resp['items']]

        if self.appear:
            wait(images_list,
                 condition=lambda temp: self.image_name in temp,
                 progress_cb=lambda temp: 'Waiting for the image to appear...',
                 interval=2, timeout=120)

            # Wait until the image has been verified on BIGIQ
            wait(lambda: self.rest.get(Image.ITEM_URI % self.image_name),
                 condition=lambda temp: temp['verificationState'] == 'VERIFY_SUCCEEDED',
                 progress_cb=lambda _: 'Waiting for the image to be verified on BIGIQ',
                 interval=3, timeout=180)

        else:
            wait(images_list,
                 condition=lambda temp: self.image_name not in temp,
                 progress_cb=lambda temp: 'Waiting for the image to disappear...',
                 interval=2, timeout=120)
