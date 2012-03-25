from .. import base

class SeleniumCommand(base.Command):

    def __init__(self, ifc, *args, **kwargs):
        self.ifc = ifc
        if self.ifc is None:
            raise TypeError('Selenium interface cannot be None.')
        assert self.ifc.is_opened()
        self.api = self.ifc.api

        super(SeleniumCommand, self).__init__(*args, **kwargs)

    def __repr__(self):
        parent = super(SeleniumCommand, self).__repr__()
        opt = {}
        opt['session_id'] = self.api.session_id
        opt['command_executor'] = self.api.command_executor
        return parent + "(command_executor=%(command_executor)s" \
                        "session_id=%(session_id)s)" % opt
    
