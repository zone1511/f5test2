'''
Created on Feb 21, 2014

@author: a.dobre@f5.com
'''
from .. import base
from ...interfaces.aws.core import AwsInterface


class AWSCommand(base.Command):
    """
    @param device: a device alias from config
    @type device: str
    @param api: an opened underlying interface
    @type api: boto api
    @param region: AWS region
    @type region: str
    @param key_id: the user access key id to connect to AWS (aka username)
    @type key_id: str
    @param access_key: the password
    @type access_key: str
    """

    ifc_class = AwsInterface

    def __init__(self, ifc=None, device=None,
                 region=None, key_id=None, access_key=None,
                 *args, **kwargs):

        if ifc is None:
            self.ifc = self.ifc_class(region=region, key_id=key_id,
                                      access_key=access_key,
                                      device=device)
            self.api = self.ifc.open()
            self._keep_alive = True
        else:
            self.ifc = ifc
            self.api = self.ifc.api
            self._keep_alive = True
        assert self.api
        self.device = device
        self.key_id = key_id
        self.access_key = access_key
        self.region = region

        super(AWSCommand, self).__init__(*args, **kwargs)

    def prep(self):
        super(AWSCommand, self).prep()
        if not self.ifc.is_opened():
            self.ifc.open()
            # self.api.connect()
        self.api = self.ifc.api

    def cleanup(self):
        if not self._keep_alive:
            self.ifc.close()
        return super(AWSCommand, self).cleanup()
