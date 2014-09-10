'''
Created on Aug 16, 2013

@author: Andrei Dobre
'''
#from ..base import SeleniumCommand
#from ...base import SSHCommand
#from ....interfaces.selenium import By
import logging
#import os
#import inspect
import yaml
import types as T

LOG = logging.getLogger(__name__)


yload = None


class YLoad:
    """Loads UI Yaml file.

    @param name:
    @type name:
    @param add:
    @type add:
    @return: a list of dicts with all the yaml objects
    """

    def __init__(self, yamlfilename, yamlfolder=None, yamlmainobj="main", *args, **kwargs):
        #super(YLoad, self).__init__(*args, **kwargs)

        self.yamlfolder = yamlfolder
        self.yamlfilename = yamlfilename
        self.ymobj = yamlmainobj

    def setup(self):
        yfile = None
        try:
            if self.yamlfolder:
                if self.yamlfolder[-1] != "/":
                    yfile = "{0}/{1}".format(self.yamlfolder, self.yamlfilename)
                else:
                    yfile = "{0}{1}".format(self.yamlfolder, self.yamlfilename)
        except Exception, e:
            LOG.warning("Could not get OS path for the YAML file. Can't run tests. "
                        "Exception is: \n{0}".format(e))
            raise AssertionError("Could not find the YAML file. Can't run tests. "
                                 "Exception is: \n{0}".format(e))
        try:
            yamlparamfile = open(yfile, 'r')
        except IOError as iox:
            LOG.warning("Could not find and open the YAML file. Can't run tests. "
                        "Exception is: \n{0}".format(iox))
            raise AssertionError("Could not open YAML file. Can't run tests. Exception is:"
                           " \n{0}".format(iox))
        except Exception, e:
            LOG.warning('Could not open the YAML file found.'
                        'Exception is: \n{0}'.format(e))
            raise e

        try:
            yloader = yaml.load(yamlparamfile)
            yamlparamfile.close()
        except Exception, e:
            LOG.error('Could not Load the YAML file. This is critical.'
                        'Exception is: \n{0}'.format(e))
            raise e
        if self.ymobj:
            return yloader.get(self.ymobj)
        else:
            return yloader

#       TO DOs: validate and read the main content from the param file

class ParseYaml:
    """Parse UI Yaml file.

    @param name:
    @type name:
    @param add:
    @type add:
    @return: a list of dicts with UI yaml objects
    """

    def __init__(self, yloader=None, *args, **kwargs):
        #super(YLoad, self).__init__(*args, **kwargs)

        self.yl = yloader

    def get_yo(self, ui="main"):
        #validate ui parameter
        if not isinstance(ui, T.StringTypes):
            ui = str(ui)
#        els = self.yl.get(ui)
#        if els == None:
#            LOG.error("Could not find '{0}' object in yaml. Can't run tests.".format(ui))
#            raise AssertionError("Could not find '{0}' object in yaml. "
#                                     "Can't run tests.".format(ui))
        yobj = self.yl
        #this function reads from a dict/lsit of dicts and returns
        #  the next element (of the first list el, if list)
        #it can be recursive
        """validate and get all objects from an yaml object"""
        #pass an yaml dictionary as a one list obj - if not list already
        if not isinstance(yobj, T.ListType):
            yobj = [yobj]
        yaml_obj = None
        for el in yobj:
            try:
                if el.get(ui):
                    yaml_obj = el.get(ui)
                    break
            except Exception, e:
                    raise e
        return yaml_obj

    def get_ybels(self, blade, els='expanded'):
        """get specific list and dicts of elements from the yaml"""
        #get the parameter yaml device dictionary
        #LOG.info("Get the {1} list from {0} blade - param yaml.".format(blade, els))
        if els == 'list':
            #get the parameter yaml device dict for elements inside list container
            return blade.get("lc_elements")
        elif els == 'expanded':
            return blade.get("expanded_elements")
        else:
            return blade.get(els)
