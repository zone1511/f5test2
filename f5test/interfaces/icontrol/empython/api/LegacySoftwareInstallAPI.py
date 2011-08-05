from ..SwimdClient import SwimdClient
from ..MessageParser import Dictionary, Array, String

class LegacySoftwareInstallAPI(SwimdClient):

    def setSwimConfig(self, pendingTaskTimeoutMinutes, simultaneousInstallationsPerTask):
        req = Dictionary()
        req.put('pendingTaskTimeoutMinutes', String(pendingTaskTimeoutMinutes))
        req.put('simultaneousInstallationsPerTask', String(simultaneousInstallationsPerTask))
        self.sendMsg('setSwimConfig', req)

    def cancelHotfixJob(self, jobno):
        req = Dictionary()
        req.put('jobno', String(jobno))
        self.sendMsg('cancelHotfixJob', req)

    def start_update(self, jobno):
        req = Dictionary()
        req.put('jobno', String(jobno))
        self.sendMsg('start_update', req)

    def cancel_update(self, jobno):
        req = Dictionary()
        req.put('jobno', String(jobno))
        self.sendMsg('cancel_update', req)

    def delete_image(self, update_info_id):
        req = Dictionary()
        req.put('update_info_id', String(update_info_id))
        self.sendMsg('delete_image', req)

    def delete_job(self, table, jobID, deviceID):
        req = Dictionary()
        req.put('table', String(table))
        req.put('jobID', String(jobID))
        req.put('deviceID', String(deviceID))
        self.sendMsg('delete_job', req)

    def download_notify(self, client_id, filename):
        req = Dictionary()
        req.put('client_id', String(client_id))
        req.put('filename', String(filename))
        return self.sendMsg('download_notify', req)

    def get_post_pkg_additions(self, client_id):
        req = Dictionary()
        req.put('client_id', String(client_id))
        return self.sendMsg('get_post_pkg_additions', req)

    def create_update_job(self, deviceInfos):
        req = Dictionary()
        req.put('deviceInfos', Array(deviceInfos))
        return self.sendMsg('create_update_job', req)

    def modify_update_job(self, options):
        req = Dictionary()
        req.put('options', Dictionary(options))
        return self.sendMsg('modify_update_job', req)

    def create_hotfix_job(self, hotfixUids, uid):
        req = Dictionary()
        req.put('hotfixUids', Array(hotfixUids))
        if uid:
            req.put('uid', String(uid))
        return self.sendMsg('create_hotfix_job', req)

    def install_hotfixes(self, uid):
        req = Dictionary()
        if uid:
            req.put('uid', String(uid))
        return self.sendMsg('install_hotfixes', req)

    def modify_hotfix_job(self, job_uid, action, force, deviceUids, continueOnError):
        req = Dictionary()
        req.put('job_uid', String(job_uid))
        if action:
            req.put('action', String(action))
        if force:
            req.put('force', String(force))
        if deviceUids:
            req.put('deviceUids', Array(deviceUids))
        if continueOnError:
            req.put('continueOnError', String(continueOnError))
        return self.sendMsg('modify_hotfix_job', req)

    def modify_hotfix_job_slots(self, options):
        req = Dictionary()
        req.put('options', Dictionary(options))
        return self.sendMsg('modify_hotfix_job_slots', req)

    def query_hotfix_job(self, job_uid, query):
        req = Dictionary()
        req.put('job_uid', String(job_uid))
        req.put('query', String(query))
        return self.sendMsg('query_hotfix_job', req)

    def import_image(self, filename, originalFilename, force, deleteImage):
        req = Dictionary()
        req.put('filename', String(filename))
        req.put('originalFilename', String(originalFilename))
        if force:
            req.put('force', String(force))
        if deleteImage:
            req.put('deleteImage', String(deleteImage))
        return self.sendMsg('import_image', req)

    def import_image_async(self, filename, originalFilename, force, deleteImage):
        req = Dictionary()
        req.put('filename', String(filename))
        req.put('originalFilename', String(originalFilename))
        if force:
            req.put('force', String(force))
        if deleteImage:
            req.put('deleteImage', String(deleteImage))
        return self.sendMsg('import_image_async', req)

