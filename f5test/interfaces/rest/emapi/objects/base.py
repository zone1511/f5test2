import json

from .....base import enum, AttrDict
from .....utils.wait import wait


DEFAULT_TIMEOUT = 30


class TaskError(Exception):
    pass


# Ref: https://indexing.f5net.com/source/xref/management-adc/tm_daemon/msgbusd/java/src/com/f5/rest/common/RestReference.java
class Reference(AttrDict):

    def __init__(self, other=None):
        if other:
            try:
                self['link'] = other['link'] if 'link' in other else other['selfLink']
            except KeyError:
                raise KeyError('Referenced object does not have a selfLink key.')

    def set(self, link):
        self['link'] = link


class ReferenceList(list):

    def __init__(self, other=None):
        super(ReferenceList, self).__init__()
        if other:
            map(self.append, other)

    def append(self, other):
        if not isinstance(other, Reference):
            other = Reference(other)
        return super(ReferenceList, self).append(other)

    def extend(self, others):
        return map(self.append, others)


class Link(AttrDict):
    def __init__(self, *args, **kwargs):
        super(Link, self).__init__(*args, **kwargs)
        self.setdefault('link', '')


class Task(AttrDict):
    STATUS = enum('CREATED', 'STARTED', 'CANCEL_REQUESTED', 'CANCELED',
                  'FAILED', 'FINISHED')
    PENDING_STATUSES = ('CREATED', 'STARTED', 'CANCEL_REQUESTED')
    FINAL_STATUSES = ('CANCELED', 'FAILED', 'FINISHED')
    FAIL_STATE = 'FAILED'

    @staticmethod
    def wait(rest, resource, loop=None, timeout=30, interval=1,
             timeout_message=None):
        def get_status():
            return rest.get(resource.selfLink)
        if loop is None:
            loop = get_status
        ret = wait(loop, timeout=timeout, interval=interval,
                   timeout_message=timeout_message,
                   condition=lambda x: x.status not in Task.PENDING_STATUSES,
                   progress_cb=lambda x: 'Status: {0}'.format(x.status))
        assert ret.status in Task.FINAL_STATUSES, "{0.status}:{0.error}".format(ret)

        if ret.status == Task.FAIL_STATE:
            msg = json.dumps(ret, sort_keys=True, indent=4, ensure_ascii=False)
            raise TaskError("Task failed.\n%s" % msg)

        return ret
