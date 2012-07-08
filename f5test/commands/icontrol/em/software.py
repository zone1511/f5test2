from .base import EMCommand
from ....base import Options

import_image = None
class ImportImage(EMCommand):
    """Import a new ISO image into EM's repository."""
    
    def __init__(self, filename, *args, **kwargs):
        super(ImportImage, self).__init__(*args, **kwargs)
        
        self.filename = filename

    def setup(self):
        em = self.api
        ret = em.legacy_software_install.import_image(self.filename,
            originalFilename=None,      # Original Filename
            force='true',               # Overwrite existing packages
            deleteImage='true')         # Delete image after import
        return int(ret['uid'])

delete_image = None
class DeleteImage(EMCommand):
    """Delete ISO image from EM's repository."""
    
    def __init__(self, uid, *args, **kwargs):
        super(DeleteImage, self).__init__(*args, **kwargs)
        
        self.uid = uid

    def setup(self):
        em = self.api
        return em.legacy_software_install.delete_image(self.uid)
        

install_image = None
class InstallImage(EMCommand):
    """Install a SW image [+ HF] from EM's repository."""
    
    def __init__(self, targets, uid, hfuid=None, options=None, *args, **kwargs):
        super(InstallImage, self).__init__(*args, **kwargs)
        
        self.targets = targets
        self.uid = uid
        self.hfuid = hfuid
        
        o = Options(options)
        o.bootFromInstalledSlot = o.get('boot_from_target', True) and 'true' or 'false'
        o.configOptions = o.get('essential_config', False) and 'essential' or 'full'
        o.includePrivateKeys = o.get('include_pk', True) and 'true' or 'false'
        o.installSlot = o.get('install_on_active', True) and 'active' or 'empty'
        o.continueOnError = o.get('continue_on_error', True) and 'true' or 'false'
        self.options = o

    def setup(self):
        em = self.api

        device_infos = []
        device_uids = []
        for target in self.targets:
            info = {}
            info['slotUid'] = target['slot_uid']
            info['installSlot'] = target['slot_uid']
            info['bootSlotUid'] = target['slot_uid']
            info['configSlotUid'] = target['slot_uid']
            info['deviceUid'] = target['device_uid']
            info['updateImageUid'] = self.uid
            device_infos.append(info)
            device_uids.append(target['device_uid'])

        rc = em.legacy_software_install.create_update_job(device_infos)
        job_id = self.options.jobID = rc['uid']
        em.legacy_software_install.modify_update_job(self.options)
        
        if self.hfuid:
            rc = em.legacy_software_install.create_hotfix_job([self.hfuid], 
                                                              job_id)
            hf_uid = rc['uid']

            assert device_uids, "deviceUids array must be specified when doing SW+HF"
            assert device_infos, "deviceInfos array must be specified when doing SW+HF"

            action = 'add_devices'
            force = 'true'
            continueOnError = 'true'
            em.legacy_software_install.modify_hotfix_job(hf_uid, action, force, 
                                                   device_uids, continueOnError)

            options = {}
            options['jobID'] = hf_uid
            options['installSlot'] = 'active'
            options['bootFromInstalledSlot'] = 'true'
            em.legacy_software_install.modify_hotfix_job_slots(options)

        em.legacy_software_install.start_update(job_id)

        if self.hfuid:
            em.legacy_software_install.install_hotfixes(job_id)

        return rc
        
