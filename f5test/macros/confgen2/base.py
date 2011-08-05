'''
Created on Jun 10, 2011

@author: jono
'''
from f5test.macros.base import Macro
from f5test.base import Options
import jinja2
from jinja2.ext import ExprStmtExtension
import logging
import os

LOG = logging.getLogger(__name__)


class Author(object):
    def __call__(self):
        return 'hey!'
    
    def boo(self, param):
        return "heh: %s" % param

class ConfigGenerator(Macro):

    def setup(self):
        ctx = Options()
        ctx.categories = ['cat1', 'cat2']
        ctx.author = Author()
        #ctx.can_edit = True
        #env = jinja2.Environment(loader=jinja2.PackageLoader(__package__))
        dir = os.path.join(os.path.dirname(__file__), 'templates')
        env = jinja2.Environment(loader=jinja2.FileSystemLoader(dir), 
                                 extensions=[ExprStmtExtension],
                                 trim_blocks=True, line_statement_prefix='#')
        template_subject = env.get_template('tmsh_base.tmpl')
        print template_subject.render(ctx)

if __name__ == '__main__':
    ConfigGenerator().run()
