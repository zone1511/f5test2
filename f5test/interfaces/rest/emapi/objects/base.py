from .....base import enum, AttrDict

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
