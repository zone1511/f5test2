from ..base import TestCase, Options
from .config import ConfigInterface
from .selenium import SeleniumInterface, DEFAULT_SELENIUM
from .ssh import SSHInterface
from .icontrol import IcontrolInterface, EMInterface
from .rest import RestInterface
import logging

INTERFACES_CONTAINER = 'interfaces'
# This container is used by logcollect plugin to copy extra files needed for
# troubleshooting in case of a failure/error. The format is expected to be:
# To copy files from a remote device.
# <filename>: (<SSHInterface instance>, <remote_file_path>)
# OR
# <filename>: <local_file_path>
# To copy from the local file system.
LOGCOLLECT_CONTAINER = 'logcollect'
LOG = logging.getLogger(__name__)


class InterfaceHelper(object):
    """
    Provides a few helper methods that will make the interface handling
    easier and also data sharing between contexts. This class may be used
    stand-alone or subclassed by a TestCase class.
    """
    def _setup(self, name):
        """
        Initializes the class. The main reason why this is not called
        __init__ is because it would collide with TestCase class' __init__.

        :param name: The context name (usually the test name/id).
        :type name: string
        """
        config = ConfigInterface().open()
        self.config = config.setdefault('_attrs', Options())
        self.name = name

    def _teardown(self):
        """
        Closes every interface opened in the current context only! This method
        should be called from a teardown* method, __exit__ method of a context
        manager or a finally block.
        """
        for name, interface in self.get_container(container=INTERFACES_CONTAINER,
                                                  exact=True).items():
            interface.close()
            self.unset_data(name, container=INTERFACES_CONTAINER)

        if self.name in self.config:
            del self.config[self.name]

    def _clear(self):
        """
        WARNING: This clears *ALL* contexts, not only the current one.
        """
        if isinstance(self.config, dict):
            self.config.clear()

    def set_data(self, key, data, container='default'):
        """
        Sets a name=value for the current context, just like you'd do with a
        dictionary. Each context may have multiple containers. The default
        container is meant to be used for storing user data. Other containers
        may be used to avoid key collision with user data.

        :param key: The key (or name) of the mapping.
        :param data: The value (or data) of the mappting.
        :param container: Container name.
        """
        container = self.set_container(container)
        container[key] = data

    def get_data(self, key, container='default'):
        """
        Retrieve the data stored by set_data().

        Example:
        Current context is 'context.level.1.1'.

        context.level.1:
            foo=bar (container=default)
            foo=bar2 (container=other)
            foo2=masked (container=default)
        context.level.1.1:
            foo2=barbar (container=default)

        >>> get_data('foo')
        bar
        >>> get_data('foo', container='other')
        bar2
        >>> get_data('foo2')
        barbar

        :param key: The key (or name) of the mapping.
        :param container: Container name.
        """
        data = self.get_container(container)
        if isinstance(data, dict):
            return data.get(key)

    def set_container(self, container='default'):
        """
        Create an empty container or return an existing one.
        """
        root = self.config.setdefault(self.name, Options())
        return root.setdefault(container, Options())

    def get_container(self, container='default', exact=False):
        """
        Returns a *volatile* dictionary of a container built hierarchically from
        parent containers.

        :param container: Container name.
        :param exact: Allow values defined in parent contexts to be included in
        child contexts.
        :type exact: bool
        """
        i = pos = 0
        my_id = self.name
        data = Options()
        while pos != -1:
            if exact:
                pos = -1
            else:
                pos = my_id.find('.', i)

            if pos > 0:
                parent = my_id[:pos]
            else:
                parent = my_id

            load = self.config.get(parent)
            if load and container in load and \
               isinstance(load[container], dict):
                data.update(load[container])
            i = pos + 1
        return data

    def unset_data(self, key, container='default'):
        """
        Delete a mapping from a container by its key.
        """
        root = self.config.setdefault(self.name, Options())
        container = root.setdefault(container, Options())
        del container[key]

    def get_interface(self, name_or_class, name=None, *args, **kwargs):
        """
        Get a previously stored interface or create a new one. If the optional
        parameter name is given then the created interface will be stored as a
        mapping with that name. Interface specific arguments can be passed in
        *args and **kwargs.

        :param name_or_class: The interface class or name (given as a string)
        :type name_or_class: a subclass of Interface or a string
        :param name:  The name to be used when storing this newly created
        interface instance.
        :type name: string
        """
        if isinstance(name_or_class, basestring):
            interface = self.get_data(name_or_class,
                                      container=INTERFACES_CONTAINER)
            assert interface, 'Interface %s was not found.' % name_or_class
            return interface
        else:
            interface = name_or_class(*args, **kwargs)
            interface.open()

        if name is None:
            name = id(interface)

        self.set_data(name, interface, container=INTERFACES_CONTAINER)
        return interface

    def get_config(self, *args, **kwargs):
        return self.get_interface(ConfigInterface, *args, **kwargs)

    def get_selenium(self, name_or_class=DEFAULT_SELENIUM, *args, **kwargs):
        """
        Historically get_selenium() would be called from the majority of tests
        without any arguments, in which case it should reuse a previously opened
        SeleniumInterface shared by all UI tests.

        As things got reworked in this class, the name/signature of these
        methods became obsolete.
        """
        return self.get_interface(name_or_class, *args, **kwargs)

    def get_selenium_anon(self, *args, **kwargs):
        return self.get_interface(SeleniumInterface, *args, **kwargs)

    def get_ssh(self, *args, **kwargs):
        return self.get_interface(SSHInterface, *args, **kwargs)

    def get_icontrol(self, *args, **kwargs):
        return self.get_interface(IcontrolInterface, *args, **kwargs)

    def get_em(self, *args, **kwargs):
        return self.get_interface(EMInterface, *args, **kwargs)

    def get_rest(self, *args, **kwargs):
        return self.get_interface(RestInterface, *args, **kwargs)


class ContextHelper(InterfaceHelper):

    def __init__(self, name):
        self._setup(name)

    def teardown(self):
        self._teardown()


class InterfaceTestCase(InterfaceHelper, TestCase):
    """
    A TestCase subclass that brings the functionality of the InterfaceHelper
    class to each test case method.
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
