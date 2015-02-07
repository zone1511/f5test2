'''
Created on Feb 21, 2014

@author: jono
'''
import traceback


class StageError(Exception):

    def __init__(self, errors, *args, **kwargs):
        self.errors = errors
        if isinstance(errors, (list, tuple)):
            lines = []
            for thread, exc_info in errors:
                lines.append("{0}: {1}".format(thread.getName(), exc_info[1]))
            message = '\n'.join(lines)
        else:
            message = errors
            self.errors = []
        super(StageError, self).__init__(message)

    def format_errors(self):
        ret = []
        for thread, exc_info in self.errors:
            ret.append('Exception in "%s"\n' % thread.getName())
            for line in traceback.format_exception(*exc_info):
                ret.append(line)
            ret.append('\n')
        return ret


class Stage(object):
    name = None
    parallelizable = True

#     def run(self):
#         raise NotImplementedError('oops!')
