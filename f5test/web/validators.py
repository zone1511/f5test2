'''
Created on Mar 8, 2013

@author: jono
'''
import os
from f5test.utils.cm import create_finder, IsoNotFoundError
from f5test.utils.version import Product


def file_validator(value, **kwargs):
    return value and os.path.exists(value) or 'File not found'


def project_validator(value, product=Product.BIGIP, **kwargs):
    if value:
        try:
            create_finder(value, product=product).find_file()
            return True
        except IsoNotFoundError:
            return 'Invalid project'


def build_validator(value, project=None, hotfix=None, product=Product.BIGIP, **kwargs):
    if hotfix and 'eng' == hotfix.lower() and not value:
        return 'Invalid ENG hotfix build'
    if value and project:
        try:
            create_finder(identifier=project, build=value, hotfix=hotfix,
                          product=product).find_file()
            return True
        except IsoNotFoundError:
            if hotfix:
                return 'Invalid build for {0} hotfix {1}'.format(project, hotfix)
            return 'Invalid build for %s' % project


def hotfix_validator(value, project=None, build=None, product=Product.BIGIP, **kwargs):
    if value and project:
        if 'eng' == value.lower():
            return True
        try:
            create_finder(identifier=project, build=build or None, hotfix=value,
                          product=product).find_file()
            return True
        except ValueError as e:
            return str(e)
        except IsoNotFoundError:
            return 'Invalid hotfix for %s' % project


validators = {'file': file_validator,
              'project': project_validator,
              'build': build_validator,
              'hotfix': hotfix_validator,
}
