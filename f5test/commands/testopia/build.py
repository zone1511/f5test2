"""Commands for Testopia.Build API."""
from .base import TestopiaCommand
from xmlrpclib import Fault
import logging

LOG = logging.getLogger(__name__) 


class BuildExistsError(Exception):
    """Thrown when the build requested already exists.""" 
    pass


create_build = None
class CreateBuild(TestopiaCommand):
    """Create a new build.
    """
    def __init__(self, build, product, *args, **kwargs):
        super(CreateBuild, self).__init__(*args, **kwargs)
        self.build = build
        self.product = product

    def setup(self):
        t = self.api
        try:
            ret = t.Build.check_build(self.build, self.product)
        except Fault, e:
            if e.faultCode == 32000 and 'does not exist' in e.faultString:
                ret = t.Build.create(dict(product=self.product, name=self.build))
            else:
                raise
        return ret
