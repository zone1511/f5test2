from ..DeviceClient import DeviceClient
from ..MessageParser import Dictionary, Array, String

class DeviceAPI(DeviceClient):

    def failover(self, deviceId):
        req = Dictionary()
        req.put('deviceId', String(deviceId))
        self.sendMsg('failover', req)

    def failback(self, deviceId):
        req = Dictionary()
        req.put('deviceId', String(deviceId))
        self.sendMsg('failback', req)

    def configSync(self, deviceId):
        req = Dictionary()
        req.put('deviceId', String(deviceId))
        self.sendMsg('configSync', req)

    def configSyncDetect(self, deviceId):
        req = Dictionary()
        req.put('deviceId', String(deviceId))
        self.sendMsg('configSyncDetect', req)

    def rebootDeviceJob(self, deviceId):
        req = Dictionary()
        req.put('deviceId', String(deviceId))
        self.sendMsg('rebootDeviceJob', req)

    def delete_device(self, deviceIds):
        req = Dictionary()
        req.put('deviceIds', Array(deviceIds))
        return self.sendMsg('delete_device', req)

    def getObjectPropsSsoUri(self, object, uid, device_uid): #@ReservedAssignment
        req = Dictionary()
        req.put('object', String(object))
        req.put('uid', String(uid))
        req.put('device_uid', String(device_uid))
        return self.sendMsg('getObjectPropsSsoUri', req)

    def refresh_device(self, deviceIds):
        req = Dictionary()
        req.put('deviceIds', Array(deviceIds))
        self.sendMsg('refresh_device', req)

    def updateCollectCertificates(self, deviceIds, deviceGroupUids):
        req = Dictionary()
        req.put('deviceIds', Array(deviceIds))
        req.put('deviceGroupUids', Array(deviceGroupUids))
        self.sendMsg('updateCollectCertificates', req)

    def createDeviceGroup(self, name, description, deviceUids):
        req = Dictionary()
        req.put('name', String(name))
        req.put('description', String(description))
        req.put('deviceUids', Array(deviceUids))
        return self.sendMsg('createDeviceGroup', req)

    def deleteDeviceGroup(self, groupUids):
        req = Dictionary()
        req.put('groupUids', Array(groupUids))
        return self.sendMsg('deleteDeviceGroup', req)

    def deleteDeviceGroupDevice(self, deviceUid, groupUids):
        req = Dictionary()
        req.put('deviceUid', String(deviceUid))
        req.put('groupUids', Array(groupUids))
        return self.sendMsg('deleteDeviceGroupDevice', req)

    def updateDeviceGroupMembers(self, groupUid, deviceUids):
        req = Dictionary()
        req.put('groupUid', String(groupUid))
        req.put('deviceUids', Array(deviceUids))
        self.sendMsg('updateDeviceGroupMembers', req)

    def updateDeviceGroupMembership(self, groupUid, deviceUids):
        req = Dictionary()
        req.put('groupUid', String(groupUid))
        req.put('deviceUids', Array(deviceUids))
        self.sendMsg('updateDeviceGroupMembership', req)

    def updateDeviceGroupProperties(self, groupUid, description):
        req = Dictionary()
        req.put('groupUid', String(groupUid))
        req.put('description', String(description))
        self.sendMsg('updateDeviceGroupProperties', req)

    def createCopyConfigJob(self, device_uids, source_device_uid, copy_users, copy_auth, copy_shell_access):
        req = Dictionary()
        req.put('device_uids', Array(device_uids))
        req.put('source_device_uid', String(source_device_uid))
        req.put('copy_users', String(copy_users))
        req.put('copy_auth', String(copy_auth))
        req.put('copy_shell_access', String(copy_shell_access))
        return self.sendMsg('createCopyConfigJob', req)

    def setCopyConfigJobErrorOpts(self, job_uid, continue_on_error, replace_users):
        req = Dictionary()
        req.put('job_uid', String(job_uid))
        req.put('continue_on_error', String(continue_on_error))
        req.put('replace_users', String(replace_users))
        self.sendMsg('setCopyConfigJobErrorOpts', req)

    def updateCopyConfigJobUsers(self, usernames, job_uid):
        req = Dictionary()
        req.put('usernames', Array(usernames))
        req.put('job_uid', String(job_uid))
        self.sendMsg('updateCopyConfigJobUsers', req)

    def deleteCopyConfigJob(self, job_uid):
        req = Dictionary()
        req.put('job_uid', String(job_uid))
        self.sendMsg('deleteCopyConfigJob', req)

    def startCopyConfigJob(self, job_uid):
        req = Dictionary()
        req.put('job_uid', String(job_uid))
        return self.sendMsg('startCopyConfigJob', req)

    def cancelCopyConfigJob(self, job_uid):
        req = Dictionary()
        req.put('job_uid', String(job_uid))
        return self.sendMsg('cancelCopyConfigJob', req)

    def createUserPasswordJob(self, device_uids):
        req = Dictionary()
        req.put('device_uids', Array(device_uids))
        return self.sendMsg('createUserPasswordJob', req)

    def setUserPasswordJobErrorOpts(self, job_uid, continue_on_error):
        req = Dictionary()
        req.put('job_uid', String(job_uid))
        req.put('continue_on_error', String(continue_on_error))
        self.sendMsg('setUserPasswordJobErrorOpts', req)

    def setUserPasswordJobPassword(self, job_uid, password):
        req = Dictionary()
        req.put('job_uid', String(job_uid))
        req.put('password', String(password))
        self.sendMsg('setUserPasswordJobPassword', req)

    def deleteUserPasswordJob(self, job_uid):
        req = Dictionary()
        req.put('job_uid', String(job_uid))
        self.sendMsg('deleteUserPasswordJob', req)

    def startUserPasswordJob(self, job_uid):
        req = Dictionary()
        req.put('job_uid', String(job_uid))
        return self.sendMsg('startUserPasswordJob', req)

    def cancelUserPasswordJob(self, job_uid):
        req = Dictionary()
        req.put('job_uid', String(job_uid))
        return self.sendMsg('cancelUserPasswordJob', req)

    def changesetCreateFromDevice(self, name, description, deviceUid, partitionUid):
        req = Dictionary()
        req.put('name', String(name))
        req.put('description', String(description))
        req.put('deviceUid', String(deviceUid))
        req.put('partitionUid', String(partitionUid))
        return self.sendMsg('changesetCreateFromDevice', req)

    def changesetCreateFromDeviceSetClasses(self, jobUid, classes):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        req.put('classes', Array(classes))
        self.sendMsg('changesetCreateFromDeviceSetClasses', req)

    def changesetCreateFromDeviceSetInstances(self, jobUid, classUid, instances):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        req.put('classUid', String(classUid))
        req.put('instances', Array(instances))
        self.sendMsg('changesetCreateFromDeviceSetInstances', req)

    def changesetCreateFromDeviceSetInstanceVariables(self, jobUid, instances):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        req.put('instances', Array(instances))
        self.sendMsg('changesetCreateFromDeviceSetInstanceVariables', req)

    def changesetCreateFromDeviceConstructText(self, jobUid, includeDependencies):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        req.put('includeDependencies', String(includeDependencies))
        self.sendMsg('changesetCreateFromDeviceConstructText', req)

    def changesetCreateFromDeviceSetText(self, jobUid, text):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        req.put('text', String(text))
        return self.sendMsg('changesetCreateFromDeviceSetText', req)

    def changesetCreateFromDeviceCancelJob(self, jobUid):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        self.sendMsg('changesetCreateFromDeviceCancelJob', req)

    def changesetCreateFromDeviceDeleteJob(self, jobUid):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        self.sendMsg('changesetCreateFromDeviceDeleteJob', req)

    def changesetCreateFromTemplate(self, name, description, templateUid):
        req = Dictionary()
        req.put('name', String(name))
        req.put('description', String(description))
        req.put('templateUid', String(templateUid))
        return self.sendMsg('changesetCreateFromTemplate', req)

    def changesetCreateFromTemplateSetVariables(self, jobUid, variables):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        req.put('variables', Array(variables))
        self.sendMsg('changesetCreateFromTemplateSetVariables', req)

    def changesetCreateFromTemplateSetText(self, jobUid, text):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        req.put('text', String(text))
        self.sendMsg('changesetCreateFromTemplateSetText', req)

    def changesetCreateFromTemplateDeleteJob(self, jobUid):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        self.sendMsg('changesetCreateFromTemplateDeleteJob', req)

    def createTextChangeset(self, name, description, textSource):
        req = Dictionary()
        req.put('name', String(name))
        req.put('description', String(description))
        req.put('textSource', String(textSource))
        return self.sendMsg('createTextChangeset', req)

    def updateChangeset(self, changesetUid, name, description, textSource):
        req = Dictionary()
        req.put('changesetUid', String(changesetUid))
        req.put('name', String(name))
        req.put('description', String(description))
        req.put('textSource', String(textSource))
        self.sendMsg('updateChangeset', req)

    def deleteChangeset(self, changesetUid):
        req = Dictionary()
        req.put('changesetUid', String(changesetUid))
        self.sendMsg('deleteChangeset', req)

    def licenseCreate(self):
        req = Dictionary()
        return self.sendMsg('licenseCreate', req)

    def licenseCancel(self, jobUid):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        self.sendMsg('licenseCancel', req)

    def licenseDelete(self, jobUid):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        self.sendMsg('licenseDelete', req)

    def licenseFetchEulas(self, jobUid, devices):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        req.put('devices', Array(devices))
        self.sendMsg('licenseFetchEulas', req)

    def licenseAcceptEulas(self, jobUid):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        self.sendMsg('licenseAcceptEulas', req)

    def licenseSetOptions(self, jobUid, continueOnError, createConfigArchive, includePrivateKeys, rebootOnLicense):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        req.put('continueOnError', String(continueOnError))
        req.put('createConfigArchive', String(createConfigArchive))
        req.put('includePrivateKeys', String(includePrivateKeys))
        req.put('rebootOnLicense', String(rebootOnLicense))
        self.sendMsg('licenseSetOptions', req)

    def licenseStart(self, jobUid, taskName):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        req.put('taskName', String(taskName))
        self.sendMsg('licenseStart', req)

    def templateCreateFromDevice(self, partitionUid, name, description):
        req = Dictionary()
        req.put('partitionUid', String(partitionUid))
        req.put('name', String(name))
        req.put('description', String(description))
        return self.sendMsg('templateCreateFromDevice', req)

    def templateCreateFromTemplate(self, templateUid, name, description):
        req = Dictionary()
        req.put('templateUid', String(templateUid))
        req.put('name', String(name))
        req.put('description', String(description))
        return self.sendMsg('templateCreateFromTemplate', req)

    def templateCreateFromText(self, name, description):
        req = Dictionary()
        req.put('name', String(name))
        req.put('description', String(description))
        return self.sendMsg('templateCreateFromText', req)

    def templateCreateSetClasses(self, jobUid, classes):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        req.put('classes', Array(classes))
        self.sendMsg('templateCreateSetClasses', req)

    def templateCreateSetInstances(self, jobUid, classUid, instances):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        req.put('classUid', String(classUid))
        req.put('instances', Array(instances))
        self.sendMsg('templateCreateSetInstances', req)

    def templateCreateSetOptions(self, jobUid, includeDependencies):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        req.put('includeDependencies', String(includeDependencies))
        self.sendMsg('templateCreateSetOptions', req)

    def templateCreateConstructText(self, jobUid):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        self.sendMsg('templateCreateConstructText', req)

    def templateCreateSetText(self, jobUid, text):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        req.put('text', String(text))
        self.sendMsg('templateCreateSetText', req)

    def templateCreateSetAttributes(self, jobUid, description, verifyChangesets, persistChangesets):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        req.put('description', String(description))
        req.put('verifyChangesets', String(verifyChangesets))
        req.put('persistChangesets', String(persistChangesets))
        self.sendMsg('templateCreateSetAttributes', req)

    def templateCreateSetVariable(self, jobUid, varUid, defaultValue, description, isEditable, isVisible):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        req.put('varUid', String(varUid))
        req.put('defaultValue', String(defaultValue))
        req.put('description', String(description))
        req.put('isEditable', String(isEditable))
        req.put('isVisible', String(isVisible))
        self.sendMsg('templateCreateSetVariable', req)

    def templateCreateSetVariableEnum(self, jobUid, varUid, values):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        req.put('varUid', String(varUid))
        req.put('values', Array(values))
        self.sendMsg('templateCreateSetVariableEnum', req)

    def templateCreateCompleted(self, jobUid):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        return self.sendMsg('templateCreateCompleted', req)

    def templateCreateDeleteJob(self, jobUid):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        self.sendMsg('templateCreateDeleteJob', req)

    def templateCreateGetText(self, jobUid):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        return self.sendMsg('templateCreateGetText', req)

    def templateSetText(self, templateUid, text):
        req = Dictionary()
        req.put('templateUid', String(templateUid))
        req.put('text', String(text))
        self.sendMsg('templateSetText', req)

    def templateSetAttributes(self, templateUid, description, isPublished, verifyChangesets, persistChangesets):
        req = Dictionary()
        req.put('templateUid', String(templateUid))
        req.put('description', String(description))
        req.put('isPublished', String(isPublished))
        req.put('verifyChangesets', String(verifyChangesets))
        req.put('persistChangesets', String(persistChangesets))
        self.sendMsg('templateSetAttributes', req)

    def templateSetVariable(self, templateUid, varUid, defaultValue, description, isEditable, isVisible):
        req = Dictionary()
        req.put('templateUid', String(templateUid))
        req.put('varUid', String(varUid))
        req.put('defaultValue', String(defaultValue))
        req.put('description', String(description))
        req.put('isEditable', String(isEditable))
        req.put('isVisible', String(isVisible))
        self.sendMsg('templateSetVariable', req)

    def templateSetVariableEnum(self, templateUid, varUid, values):
        req = Dictionary()
        req.put('templateUid', String(templateUid))
        req.put('varUid', String(varUid))
        req.put('values', Array(values))
        self.sendMsg('templateSetVariableEnum', req)

    def templateDelete(self, templateUid):
        req = Dictionary()
        req.put('templateUid', String(templateUid))
        self.sendMsg('templateDelete', req)

    def templateGetText(self, templateUid):
        req = Dictionary()
        req.put('templateUid', String(templateUid))
        return self.sendMsg('templateGetText', req)

    def stagedChangesetCreateFromTemplate(self, jobUid, templateUid):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        req.put('templateUid', String(templateUid))
        return self.sendMsg('stagedChangesetCreateFromTemplate', req)

    def stagedChangesetCreateFromChangeset(self, jobUid, changesetUid):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        req.put('changesetUid', String(changesetUid))
        return self.sendMsg('stagedChangesetCreateFromChangeset', req)

    def stagedChangesetCreateSetDevices(self, jobUid, devices):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        req.put('devices', Array(devices))
        self.sendMsg('stagedChangesetCreateSetDevices', req)

    def stagedChangesetCreateSetPartitions(self, jobUid, partitions):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        req.put('partitions', Array(partitions))
        self.sendMsg('stagedChangesetCreateSetPartitions', req)

    def stagedChangesetCreateSetOptions(self, jobUid, description, createArchive, includePrivateKeys):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        req.put('description', String(description))
        req.put('createArchive', String(createArchive))
        req.put('includePrivateKeys', String(includePrivateKeys))
        self.sendMsg('stagedChangesetCreateSetOptions', req)

    def stagedChangesetCreateSetVariables(self, jobUid, deviceUid, variables):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        req.put('deviceUid', String(deviceUid))
        req.put('variables', Array(variables))
        self.sendMsg('stagedChangesetCreateSetVariables', req)

    def stagedChangesetCreateVerify(self, jobUid):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        self.sendMsg('stagedChangesetCreateVerify', req)

    def stagedChangesetCreateCancelVerify(self, jobUid):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        self.sendMsg('stagedChangesetCreateCancelVerify', req)

    def stagedChangesetCreateCompleted(self, jobUid):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        self.sendMsg('stagedChangesetCreateCompleted', req)

    def stagedChangesetCreateDeleteJob(self, jobUid):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        self.sendMsg('stagedChangesetCreateDeleteJob', req)

    def stagedChangesetDelete(self, stagedChangesetUid):
        req = Dictionary()
        req.put('stagedChangesetUid', Array(stagedChangesetUid))
        self.sendMsg('stagedChangesetDelete', req)

    def stagedChangesetPushCreate(self, stagedChangesets):
        req = Dictionary()
        req.put('stagedChangesets', Array(stagedChangesets))
        return self.sendMsg('stagedChangesetPushCreate', req)

    def stagedChangesetPushSetOptions(self, jobUid, continueOnError):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        req.put('continueOnError', String(continueOnError))
        self.sendMsg('stagedChangesetPushSetOptions', req)

    def stagedChangesetPushVerify(self, jobUid, taskName):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        req.put('taskName', String(taskName))
        self.sendMsg('stagedChangesetPushVerify', req)

    def stagedChangesetPushCancelVerify(self, jobUid):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        self.sendMsg('stagedChangesetPushCancelVerify', req)

    def stagedChangesetPushDeploy(self, jobUid, taskName):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        req.put('taskName', String(taskName))
        self.sendMsg('stagedChangesetPushDeploy', req)

    def stagedChangesetPushCancelJob(self, jobUid):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        self.sendMsg('stagedChangesetPushCancelJob', req)

    def stagedChangesetPushDeleteJob(self, jobUid):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        self.sendMsg('stagedChangesetPushDeleteJob', req)

    def roleSetPermissions(self, role, permissions):
        req = Dictionary()
        req.put('role', String(role))
        req.put('permissions', Dictionary(permissions))
        self.sendMsg('roleSetPermissions', req)

    def roleGetUserPermissions(self, authUser):
        req = Dictionary()
        req.put('authUser', String(authUser))
        return self.sendMsg('roleGetUserPermissions', req)

    def roleGetPermissions(self, role):
        req = Dictionary()
        req.put('role', String(role))
        return self.sendMsg('roleGetPermissions', req)

    def proxySetConfiguration(self, sslProxyHost, sslProxyPort, ftpProxyHost, ftpProxyPort, useSslProxyForFtp, proxyEnable):
        req = Dictionary()
        req.put('sslProxyHost', String(sslProxyHost))
        req.put('sslProxyPort', String(sslProxyPort))
        req.put('ftpProxyHost', String(ftpProxyHost))
        req.put('ftpProxyPort', String(ftpProxyPort))
        req.put('useSslProxyForFtp', String(useSslProxyForFtp))
        req.put('proxyEnable', String(proxyEnable))
        self.sendMsg('proxySetConfiguration', req)

    def proxyGetConfiguration(self):
        req = Dictionary()
        return self.sendMsg('proxyGetConfiguration', req)

    def systemInfoGetFilesystemStats(self, mountPoint):
        req = Dictionary()
        req.put('mountPoint', String(mountPoint))
        return self.sendMsg('systemInfoGetFilesystemStats', req)

    def systemInfoGetLocalHAInfo(self):
        req = Dictionary()
        return self.sendMsg('systemInfoGetLocalHAInfo', req)

    def supportInfoCreate(self, caseNumber):
        req = Dictionary()
        req.put('caseNumber', String(caseNumber))
        return self.sendMsg('supportInfoCreate', req)

    def supportInfoSetAdditionalInfo(self, jobUid, additionalInfo):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        req.put('additionalInfo', String(additionalInfo))
        self.sendMsg('supportInfoSetAdditionalInfo', req)

    def supportInfoSetOptions(self, jobUid, qkviewArgs):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        req.put('qkviewArgs', String(qkviewArgs))
        self.sendMsg('supportInfoSetOptions', req)

    def supportInfoAddDevices(self, jobUid, deviceUids):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        req.put('deviceUids', Array(deviceUids))
        self.sendMsg('supportInfoAddDevices', req)

    def supportInfoDeleteDevices(self, jobUid, deviceUids):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        req.put('deviceUids', Array(deviceUids))
        self.sendMsg('supportInfoDeleteDevices', req)

    def supportInfoGatherInfo(self, jobUid):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        self.sendMsg('supportInfoGatherInfo', req)

    def supportInfoCancelGatherInfo(self, jobUid):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        self.sendMsg('supportInfoCancelGatherInfo', req)

    def supportInfoAddAttachment(self, jobUid, tmpFilePath, actualFileName):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        req.put('tmpFilePath', String(tmpFilePath))
        req.put('actualFileName', String(actualFileName))
        self.sendMsg('supportInfoAddAttachment', req)

    def supportInfoDeleteAttachments(self, jobUid, filePaths):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        req.put('filePaths', Array(filePaths))
        self.sendMsg('supportInfoDeleteAttachments', req)

    def supportInfoCreateArchive(self, jobUid):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        self.sendMsg('supportInfoCreateArchive', req)

    def supportInfoSetDestination(self, jobUid, targetType, targetDir, ftpServer, ftpServerPort, ftpLogin, ftpPassword):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        req.put('targetType', String(targetType))
        req.put('targetDir', String(targetDir))
        req.put('ftpServer', String(ftpServer))
        req.put('ftpServerPort', String(ftpServerPort))
        req.put('ftpLogin', String(ftpLogin))
        req.put('ftpPassword', String(ftpPassword))
        self.sendMsg('supportInfoSetDestination', req)

    def supportInfoGetArchiveFilePath(self, jobUid):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        return self.sendMsg('supportInfoGetArchiveFilePath', req)

    def supportInfoSendInfo(self, jobUid):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        self.sendMsg('supportInfoSendInfo', req)

    def supportInfoFinishJob(self, jobUid):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        self.sendMsg('supportInfoFinishJob', req)

    def supportInfoDeleteJob(self, jobUid):
        req = Dictionary()
        req.put('jobUid', String(jobUid))
        self.sendMsg('supportInfoDeleteJob', req)

    def swapDeviceCreateChecklist(self, deviceUid):
        req = Dictionary()
        req.put('deviceUid', String(deviceUid))
        self.sendMsg('swapDeviceCreateChecklist', req)

    def swapDeviceSetChecklistValue(self, deviceUid, name, value):
        req = Dictionary()
        req.put('deviceUid', String(deviceUid))
        req.put('name', String(name))
        req.put('value', String(value))
        self.sendMsg('swapDeviceSetChecklistValue', req)

    def swapDeviceSetCurrentButton(self, deviceUid, button):
        req = Dictionary()
        req.put('deviceUid', String(deviceUid))
        req.put('button', String(button))
        self.sendMsg('swapDeviceSetCurrentButton', req)

    def swapDeviceSetHostname(self, deviceUid, hostName):
        req = Dictionary()
        req.put('deviceUid', String(deviceUid))
        req.put('hostName', String(hostName))
        self.sendMsg('swapDeviceSetHostname', req)

    def swapDeviceSetRegkey(self, deviceUid, regkey):
        req = Dictionary()
        req.put('deviceUid', String(deviceUid))
        req.put('regkey', String(regkey))
        self.sendMsg('swapDeviceSetRegkey', req)

    def swapDeviceDeleteChecklist(self, deviceUid):
        req = Dictionary()
        req.put('deviceUid', String(deviceUid))
        self.sendMsg('swapDeviceDeleteChecklist', req)

    def setDeviceConfig(self, refreshIntervalMinutes, defaultIncludePrivateKeys, defaultExternalLink, autoRefreshEnabled):
        req = Dictionary()
        req.put('refreshIntervalMinutes', String(refreshIntervalMinutes))
        req.put('defaultIncludePrivateKeys', String(defaultIncludePrivateKeys))
        req.put('defaultExternalLink', String(defaultExternalLink))
        req.put('autoRefreshEnabled', String(autoRefreshEnabled))
        self.sendMsg('setDeviceConfig', req)

    def eventNotification(self, deviceUid, dbKeyValues):
        req = Dictionary()
        req.put('deviceUid', String(deviceUid))
        req.put('dbKeyValues', Array(dbKeyValues))
        self.sendMsg('eventNotification', req)

    def getDevicesAddresses(self):
        req = Dictionary()
        return self.sendMsg('getDevicesAddresses', req)

    def setDeviceProp(self, uid, accessAddress, emIpAddress, uiAccessAddress, location, contact, externalLink, ignoreCfOnlyMgmtNetworkRestriction):
        req = Dictionary()
        req.put('uid', String(uid))
        req.put('accessAddress', String(accessAddress))
        req.put('emIpAddress', String(emIpAddress))
        req.put('uiAccessAddress', String(uiAccessAddress))
        req.put('location', String(location))
        req.put('contact', String(contact))
        req.put('externalLink', String(externalLink))
        req.put('ignoreCfOnlyMgmtNetworkRestriction', String(ignoreCfOnlyMgmtNetworkRestriction))
        return self.sendMsg('setDeviceProp', req)

    def deviceSetMaintenanceMode(self, deviceUid, mode, reason):
        req = Dictionary()
        req.put('deviceUid', String(deviceUid))
        req.put('mode', String(mode))
        req.put('reason', String(reason))
        self.sendMsg('deviceSetMaintenanceMode', req)

    def deviceSetPeerOverride(self, deviceUid, peerDeviceUid):
        req = Dictionary()
        req.put('deviceUid', String(deviceUid))
        req.put('peerDeviceUid', String(peerDeviceUid))
        self.sendMsg('deviceSetPeerOverride', req)

    def deviceDisablePeerOverride(self, deviceUid):
        req = Dictionary()
        req.put('deviceUid', String(deviceUid))
        self.sendMsg('deviceDisablePeerOverride', req)

    def iControlProxySetConfiguration(self, enabled):
        req = Dictionary()
        req.put('enabled', String(enabled))
        self.sendMsg('iControlProxySetConfiguration', req)

    def iControlProxyGetConfiguration(self):
        req = Dictionary()
        return self.sendMsg('iControlProxyGetConfiguration', req)['enabled'] == 'true'
