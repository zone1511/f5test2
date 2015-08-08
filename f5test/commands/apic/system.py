'''
Created on Jun 16, 2015

@author: john.wong@f5.com
'''
from .base import ApicRestCommand
from ...base import AttrDict
from ...interfaces.rest.apic.objects.system import DevicePackage
import logging

LOG = logging.getLogger(__name__)
DEFAULT_DP_PATH = '/build/platform/cisco-apic/daily/current/F5DevicePackage.zip'


upload_dp = None
class UploadDp(ApicRestCommand):  # @IgnorePep8
    """Upload Device Package (DP)

    @param path: path #mandatory
    @type name: string

    @return: Return vsnMDev data after POST.
    @rtype: dict
    """
    def __init__(self, path=None, *args, **kwargs):
        super(UploadDp, self).__init__(*args, **kwargs)
        self.path = path or DEFAULT_DP_PATH

    def setup(self):
        """Uploads DP."""
        headers = {'Content-Type': 'multipart/form-data'}

        with open(self.path, "r") as f:
            payload = AttrDict()
            payload.name = f
            self.ifc.api.post(DevicePackage.UPLOAD_URI, headers=headers,
                              payload=payload)
        return self.ifc.api.get(DevicePackage.URI)

delete_dp = None
class DeleteDp(ApicRestCommand):  # @IgnorePep8
    """Delete Device Package (DP)

    @param vns_mdev: vnsMDev response #mandatory
    @type vnsMDev: dict

    @return: POST response of delete
    @rtype: dict
    """
    def __init__(self, vns_mdev, *args, **kwargs):
        super(DeleteDp, self).__init__(*args, **kwargs)
        self.vns_mdev = vns_mdev

    def setup(self):
        """Deletes DP."""

        payload = AttrDict()
        payload.infraInfra = AttrDict()
        vns_mdev = AttrDict()
        vns_mdev['@dn'] = self.vns_mdev['@dn']
        vns_mdev['@status'] = 'deleted'

        payload.infraInfra.vnsMDev = vns_mdev

        return self.ifc.api.post(DevicePackage.DELETE_URI, payload=payload)
