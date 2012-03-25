from ..base import TestCase, Options
from .config import ConfigInterface
from .selenium import SeleniumInterface
from .ssh import SSHInterface
from .icontrol import IcontrolInterface, EMInterface
from .rest import RestInterface


class InterfaceHelper(object):
    """Adds get_selenium() helper to a TestCase.
    
    - If key is a string, then it will use it as the key to lookup in the global
    handles store, which is managed by the test package.
    
    - If key is a SeleniumInterface instance then it will open it, add it to the
    local handles store and return the opened interface.
    
    - If key is None then it will try to open a new SeleniumInterface using the
    args and kwargs provided.
    """
    def _setup(self, name, ifcs=None):
        config = ConfigInterface().open()
        config.setdefault('_attrs', Options())
        
        self.ifcs = ifcs
        self._apis = {}
        self._handles = {}
        self._data = Options()
        i = pos = 0
        my_id = name
        while pos != -1:
            pos = my_id.find('.', i)
            if pos > 0:
                parent = my_id[:pos]
                load = config._attrs.get(parent)
                if load and isinstance(load, dict):
                    self._handles.update(load)
                
                i = pos + 1
        
    def _teardown(self):
        for interface in self._apis.keys():
            self.pop_interface(interface)

    def set_data(self, key, data):
        self._data[key] = data

    def get_data(self, key):
        return self._data.get(key)

    def unset_data(self, key):
        self._data.__delitem__(key)

    def push_interface(self, interface, managed=False):
        if not managed:
            interface.open()
        self._apis[interface] = managed
        if isinstance(self.ifcs, list):
            self.ifcs.append(interface)
        #return interface.api
        return interface

    def pop_interface(self, interface):
        managed = self._apis.pop(interface)
        if isinstance(self.ifcs, list):
            self.ifcs.remove(interface)
        if not managed:
            interface.close()

    def get_interface(self, interface_class, key=None, *args, **kwargs):
        managed = False
        if isinstance(key, basestring):
            interface = self._handles.get(key)
            managed = True
        else:
            if isinstance(key, interface_class):
                interface = key
            elif key is None:
                interface = interface_class(*args, **kwargs)
            else:
                raise ValueError("key argument must be either string, "
                                 "%s or None" % interface_class)

        return self.push_interface(interface, managed)
        
    def get_config(self, *args, **kwargs):
        return self.get_interface(ConfigInterface, *args, **kwargs)

    def get_selenium(self, key='selenium', *args, **kwargs):
        return self.get_interface(SeleniumInterface, key, *args, **kwargs)

    def get_ssh(self, *args, **kwargs):
        return self.get_interface(SSHInterface, *args, **kwargs)

    def get_icontrol(self, *args, **kwargs):
        return self.get_interface(IcontrolInterface, *args, **kwargs)

    def get_em(self, *args, **kwargs):
        return self.get_interface(EMInterface, *args, **kwargs)

    def get_rest(self, *args, **kwargs):
        return self.get_interface(RestInterface, *args, **kwargs)


class InterfaceTestCase(InterfaceHelper, TestCase):
    """Updates the current test attributes with the ones set in config._attrs.
    
    In tests.setup_module():
    config._attrs['tests'] = dict(handle1=1)
    
    In tests.em.setup_module():
    config._attrs['tests.em'] = dict(handle1=2)
    
    In tests.em.ui.setup_module():
    config._attrs['tests.em.ui'] = dict(handle2=3)
    
    
    Then the test would be able to access these attrs like this:
    
    tests.em.ui.test_file.TestClass.testMe:
    def testMe(self):
        print self.handle1 # would print '2'
        print self.handle2 # would print '3'
    """
    @classmethod
    def setup_class(cls):
        ih = InterfaceHelper()
        name = "%s.%s" % (cls.__module__, cls.__name__)
        ih._setup(name)
        cls.ih = ih

    @classmethod
    def teardown_class(cls):
        cls.ih._teardown()

    def setUp(self, *args, **kwargs):
        self._setup(self.id())
        
        super(TestCase, self).setUp(*args, **kwargs)

    def tearDown(self, *args, **kwargs):
        self._teardown()
        
        super(TestCase, self).tearDown(*args, **kwargs)
