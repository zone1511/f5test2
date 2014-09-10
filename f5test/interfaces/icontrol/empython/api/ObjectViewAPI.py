from ..DeviceClient import DeviceClient
from ..MessageParser import Dictionary, Array, String

class ObjectViewAPI(DeviceClient):

  def createObjectView(self, type, name, content, description, owner):
    req = Dictionary()
    req.put('type', String(type))
    req.put('name', String(name))
    req.put('content', String(content))
    req.put('description', String(description))
    req.put('owner', String(owner))
    return self.sendMsg('createObjectView', req)

  def deleteObjectView(self, uid):
    req = Dictionary()
    req.put('uid', String(uid))
    self.sendMsg('deleteObjectView', req)

  def addRuleToObjectView(self, uid, rule, ruleType, objectType):
    req = Dictionary()
    req.put('uid', String(uid))
    req.put('rule', String(rule))
    req.put('ruleType', String(ruleType))
    req.put('objectType', String(objectType))
    return self.sendMsg('addRuleToObjectView', req)

  def removeRuleFromObjectView(self, uid):
    req = Dictionary()
    req.put('uid', String(uid))
    self.sendMsg('removeRuleFromObjectView', req)
