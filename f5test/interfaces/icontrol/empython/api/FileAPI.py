from ..FileClient import FileClient
from ..MessageParser import Dictionary, Array, String

class FileAPI(FileClient):

    def pinConfigArchive(self, uids):
        req = Dictionary()
        req.put('uids', Array(uids))
        self.sendMsg('pinConfigArchive', req)

    def restoreConfigArchive(self, uid, force, includeLicense):
        req = Dictionary()
        req.put('uid', String(uid))
        req.put('force', String(force))
        req.put('includeLicense', String(includeLicense))
        self.sendMsg('restoreConfigArchive', req)

    def saveConfigArchive(self, device_uids, filename, description, includePrivateKeys, pin):
        req = Dictionary()
        req.put('device_uids', String(device_uids))
        req.put('filename', String(filename))
        req.put('description', String(description))
        req.put('includePrivateKeys', String(includePrivateKeys))
        req.put('pin', String(pin))
        return self.sendMsg('saveConfigArchive', req)

    def createPinnedConfigArchive(self, uid, filename, description, includePrivateKeys):
        req = Dictionary()
        req.put('uid', String(uid))
        req.put('filename', String(filename))
        req.put('description', String(description))
        req.put('includePrivateKeys', String(includePrivateKeys))
        return self.sendMsg('createPinnedConfigArchive', req)

    def deleteConfigArchive(self, uids):
        req = Dictionary()
        req.put('uids', Array(uids))
        self.sendMsg('deleteConfigArchive', req)

    def setFileConfig(self, maxPinnedArchives, maxRotatingArchives, privateKeysInArchives):
        req = Dictionary()
        req.put('maxPinnedArchives', String(maxPinnedArchives))
        req.put('maxRotatingArchives', String(maxRotatingArchives))
        req.put('privateKeysInArchives', String(privateKeysInArchives))
        self.sendMsg('setFileConfig', req)

    def setDeviceSchedules(self, device_uid, schedule_uids):
        req = Dictionary()
        req.put('device_uid', String(device_uid))
        req.put('schedule_uids', Array(schedule_uids))
        self.sendMsg('setDeviceSchedules', req)

    def removeDevicesFromSchedules(self, device_uid, schedule_uids):
        req = Dictionary()
        req.put('device_uid', String(device_uid))
        req.put('schedule_uids', Array(schedule_uids))
        self.sendMsg('removeDevicesFromSchedules', req)

    def setDeviceGroupSchedules(self, group_uid, schedule_uids):
        req = Dictionary()
        req.put('group_uid', String(group_uid))
        req.put('schedule_uids', Array(schedule_uids))
        self.sendMsg('setDeviceGroupSchedules', req)

    def removeDeviceGroupFromSchedules(self, group_uid, schedule_uids):
        req = Dictionary()
        req.put('group_uid', String(group_uid))
        req.put('schedule_uids', Array(schedule_uids))
        self.sendMsg('removeDeviceGroupFromSchedules', req)

    def createSchedule(self, taskname, timeofday_hour, timeofday_minute, frequency_type, dayofweek, dayofmonth, enabled, deviceUids, devGroupUids):
        req = Dictionary()
        req.put('taskname', String(taskname))
        req.put('timeofday_hour', String(timeofday_hour))
        req.put('timeofday_minute', String(timeofday_minute))
        req.put('frequency_type', String(frequency_type))
        req.put('dayofweek', String(dayofweek))
        req.put('dayofmonth', String(dayofmonth))
        req.put('enabled', String(enabled))
        req.put('deviceUids', Array(deviceUids))
        req.put('devGroupUids', Array(devGroupUids))
        self.sendMsg('createSchedule', req)

    def updateSchedule(self, uid, taskname, timeofday_hour, timeofday_minute, frequency_type, dayofweek, dayofmonth, enabled, deviceUids, devGroupUids):
        req = Dictionary()
        req.put('uid', String(uid))
        req.put('taskname', String(taskname))
        req.put('timeofday_hour', String(timeofday_hour))
        req.put('timeofday_minute', String(timeofday_minute))
        req.put('frequency_type', String(frequency_type))
        req.put('dayofweek', String(dayofweek))
        req.put('dayofmonth', String(dayofmonth))
        req.put('enabled', String(enabled))
        req.put('deviceUids', Array(deviceUids))
        req.put('devGroupUids', Array(devGroupUids))
        self.sendMsg('updateSchedule', req)

    def deleteSchedules(self, scheduleUids):
        req = Dictionary()
        req.put('scheduleUids', String(scheduleUids))
        self.sendMsg('deleteSchedules', req)

    def enableDisableSchedules(self, scheduleUids, enabled):
        req = Dictionary()
        req.put('scheduleUids', String(scheduleUids))
        req.put('enabled', String(enabled))
        self.sendMsg('enableDisableSchedules', req)

    def diffConfigCreate(self, device_uid, diff_compare_type, archive_uid1, archive_uid2, include_private_keys):
        req = Dictionary()
        req.put('device_uid', String(device_uid))
        req.put('diff_compare_type', String(diff_compare_type))
        req.put('archive_uid1', String(archive_uid1))
        req.put('archive_uid2', String(archive_uid2))
        req.put('include_private_keys', String(include_private_keys))
        self.sendMsg('diffConfigCreate', req)

    def diffConfigDelete(self, task_uid):
        req = Dictionary()
        req.put('task_uid', String(task_uid))
        self.sendMsg('diffConfigDelete', req)

    def diffConfigCancel(self, task_uid):
        req = Dictionary()
        req.put('task_uid', String(task_uid))
        self.sendMsg('diffConfigCancel', req)

    def diffConfigStart(self, task_uid, task_name):
        req = Dictionary()
        req.put('task_uid', String(task_uid))
        req.put('task_name', String(task_name))
        self.sendMsg('diffConfigStart', req)

    def diffConfigSetCompareFileNames(self, filenames):
        req = Dictionary()
        req.put('filenames', Array(filenames))
        self.sendMsg('diffConfigSetCompareFileNames', req)

    def diffConfigGetCurrentCompareFileNames(self):
        req = Dictionary()
        return self.sendMsg('diffConfigGetCurrentCompareFileNames', req)

    def diffConfigGetDefaultCompareFileNames(self):
        req = Dictionary()
        return self.sendMsg('diffConfigGetDefaultCompareFileNames', req)

