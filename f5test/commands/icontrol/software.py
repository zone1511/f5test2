from .base import IcontrolCommand
from ..base import WaitableCommand
import time

import logging
LOG = logging.getLogger(__name__)


get_software_image = None
class GetSoftwareImage(WaitableCommand, IcontrolCommand):
    """Get the software image data. If no filename is provided all images are
    returned.
    """

    def __init__(self, filename=None, blade=0, is_hf=False, *args, **kwargs):
        super(GetSoftwareImage, self).__init__(*args, **kwargs)

        self.filename = filename
        self.blade = blade
        self.is_hf = is_hf

    def setup(self):
        ic = self.api
        if self.filename:
            if ic.System.Cluster.is_clustered_environment():
                blades = ic.System.Cluster.get_slot_id(cluster_names=['default'])
                states = ic.System.Cluster.get_member_ha_state(cluster_names=['default'],
                                                               slot_ids=blades)
                imageIDs = []
                for blade_id, state in zip(blades[0], states[0]):
                    if state != 'HA_STATE_UNKNOWN':
                        imageIDs.append({'chassis_slot_id': blade_id,
                                         'filename': self.filename})
            else:
                imageIDs = [{'chassis_slot_id': self.blade,
                             'filename': self.filename}]
        else:
            if self.is_hf:
                imageIDs = ic.System.SoftwareManagement.get_software_hotfix_list()
            else:
                imageIDs = ic.System.SoftwareManagement.get_software_image_list()

        if self.is_hf:
            return ic.System.SoftwareManagement.get_software_hotfix(imageIDs=imageIDs)
        else:
            return ic.System.SoftwareManagement.get_software_image(imageIDs=imageIDs)


delete_software_image = None
class DeleteSoftwareImage(WaitableCommand, IcontrolCommand):
    """Delete a software image. If no filename is provided all images are
    removed.
    """

    def __init__(self, filename=None, is_hf=False, *args, **kwargs):
        super(DeleteSoftwareImage, self).__init__(*args, **kwargs)

        self.filename = filename
        self.is_hf = is_hf

    def setup(self):
        ic = self.api
        if self.filename:
            if isinstance(self.filename, (list, tuple)):
                images = self.filename
            else:
                images = [self.filename]
        else:
            if self.is_hf:
                images = [x['filename'] for x in ic.System.SoftwareManagement.get_software_hotfix_list()]
            else:
                images = [x['filename'] for x in ic.System.SoftwareManagement.get_software_image_list()]

        if images:
            return ic.System.SoftwareManagement.delete_software_image(image_filenames=images)


install_software = None
class InstallSoftware(IcontrolCommand):
    """Install a new software image.

    @param desired_version: a Version instance
    @type desired_version: Version
    @param volume: the target volume
    @type volume: str
    """

    def __init__(self, desired_version, volume=None, *args, **kwargs):
        super(InstallSoftware, self).__init__(*args, **kwargs)

        self.desired_version = desired_version
        self.volume = volume

    def setup(self):
        ic = self.api

        if not self.volume:
            statuses = ic.System.SoftwareManagement.get_all_software_status()
            for status in statuses:
                if not status['active']:
                    s = status['installation_id']['install_volume']
                    break
            else:
                raise ValueError('No inactive slots found.')
        else:
            s = self.volume

        v = self.desired_version
        p = v.product.to_tmos
        #print s, v, p
        ic.System.SoftwareManagement.install_software_image(install_volume=s,
                                                            product=p,
                                                            version=v.version,
                                                            build=v.build)

        LOG.debug('Sleeping after install asyc...')
        time.sleep(10)
        return s


clear_volume = None
class ClearVolume(IcontrolCommand):
    """Clear a volume."""
    def __init__(self, volume, *args, **kwargs):
        super(ClearVolume, self).__init__(*args, **kwargs)

        self.volume = volume

    def setup(self):
        ic = self.api

        s = self.volume
        ic.System.SoftwareManagement.install_software_image(install_volume=s,
                                                            product='',
                                                            version='',
                                                            build='')
        time.sleep(5)
        return s


get_software_status = None
class GetSoftwareStatus(WaitableCommand, IcontrolCommand):
    """Get the status of an installation."""

    def __init__(self, volume=None, *args, **kwargs):
        super(GetSoftwareStatus, self).__init__(*args, **kwargs)

        self.volume = volume

    def setup(self):

        ic = self.api
        if self.volume is None:
            volumes = map(lambda x: x['installation_id']['install_volume'],
              ic.System.SoftwareManagement.get_all_software_status())
        else:
            volumes = [self.volume]

        for volume in volumes:
            if ic.System.Cluster.is_clustered_environment():
                blades = ic.System.Cluster.get_slot_id(cluster_names=['default'])
                states = ic.System.Cluster.get_member_ha_state(cluster_names=['default'],
                                                               slot_ids=blades)
                installIDs = []
                for blade_id, state in zip(blades[0], states[0]):
                    if state != 'HA_STATE_UNKNOWN':
                        installIDs.append({'chassis_slot_id': blade_id,
                                           'install_volume': volume})
            else:
                installIDs = [{'chassis_slot_id': 0,
                               'install_volume': volume}]

        return ic.System.SoftwareManagement.get_software_status(installation_ids=installIDs)


get_active_volume = None
class GetActiveVolume(WaitableCommand, IcontrolCommand):
    """Get the status of an installation."""

    def setup(self):
        ic = self.api
        _ = list(filter(lambda x: x['active'],
                        ic.System.SoftwareManagement.get_all_software_status()))
        return _[0]['installation_id']['install_volume']


get_inactive_volume = None
class GetInactiveVolume(WaitableCommand, IcontrolCommand):
    """Get the status of an installation."""

    def setup(self):
        ic = self.api
        _ = list(filter(lambda x: not x['active'] and (x['status'] == 'complete' or
                                                       x['status'].startswith('failed')),
                        ic.System.SoftwareManagement.get_all_software_status()))
        return _[0]['installation_id']['install_volume']
