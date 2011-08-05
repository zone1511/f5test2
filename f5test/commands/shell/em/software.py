from ..sql import Query
from .device import GetTask
from ....utils.version import Version

get_installation_task = None
class GetInstallationTask(GetTask):

    def setup(self):
        task = super(GetInstallationTask, self).setup()[0]

        if task['detail_table'] == 'update_job':
            fields = ['u.status', 'u.error_code', 'u.error_message',
                      'u.display_device_address', 'u.display_install_location',
                      'u.progress_percent']
            hf_fields = ['hf.status AS hf_status', 'hf.error_code AS hf_error_code', 
                         'hf.error_message AS hf_error_message']
            self.query = """SELECT %s FROM update_device_job u
                                      LEFT JOIN device_2_install_hotfixes_job hf  ON
                                          (hf.hotfix_job_id = update_job AND
                                           hf.device_id = u.device_id)
                                      WHERE update_job = %d""" % \
                        (','.join(fields + hf_fields), self.task_id)
    
            details = super(GetInstallationTask, self).setup()
        else:
            details = []

        task['details'] = details
        task['progress_percent'] = sum([100 if int(x['progress_percent']) < -1 else int(x['progress_percent']) 
                                        for x in details]) / len(details)
        return task


get_image_list = None
class GetImageList(Query):

    def __init__(self, *args, **kwargs):
        fields = ['uid', 'product_name', 'version', 'min_version', 'build_number']
        query = """SELECT %s FROM update_info
                   WHERE image_status = 'imported'""" % \
                    (','.join(fields))

        super(GetImageList, self).__init__(query=query, *args, **kwargs)

    def setup(self):
        ret = {}
        for im in super(GetImageList, self).setup():
            ver = Version("%(product_name)s %(version)s %(build_number)s" % im)
            ret[ver] = int(im['uid'])
        return ret

get_hotfix_list = None
class GetHotfixList(Query):

    def __init__(self, *args, **kwargs):
        fields = ['uid', 'name', 'title', 'build_number', 'product_name', 
                  'product_version']
        query = """SELECT %s FROM hotfix_image
                   WHERE image_status = 'imported'""" % \
                    (','.join(fields))

        super(GetHotfixList, self).__init__(query=query, *args, **kwargs)

    def setup(self):
        #ret = []
        ret = {}
        for hf in super(GetHotfixList, self).setup():
            ver = Version("%(product_name)s %(product_version)s %(title)s" % hf)
            #ret.append(dict(uid=int(hf['uid']), version=ver))
            ret[ver] = int(hf['uid'])
        return ret
