from .base import SSHCommand
from .ssh import get_version
from ..base import CachedCommand, WaitableCommand
from ...base import Options
from ...utils.parsers import tmsh
import logging

LOG = logging.getLogger(__name__)


class CommandNotSupported(Exception):
    """The command is not supported on this TMOS version."""
    pass


class SSHCommandError(Exception):
    """The exit status was non-zero, indicating an error."""
    pass


run = None
class Run(WaitableCommand, SSHCommand):
    """Run a generic one line tmsh command.

    >>> tmsh.run('sys mcp-state field-fmt', command='show')

    @param arguments: the arguments for tmsh, including module
    @type arguments: str
    @param recursive: recurse to subfolders
    @type recursive: bool
    @param folder: the initial folder (default is /Common)
    @type folder: str
    @param command: the tmsh command (list, show, modify, create, etc.)
    @type command: str
    """
    def __init__(self, arguments, recursive=False, folder=None, command='list',
                 *args, **kwargs):

        super(Run, self).__init__(*args, **kwargs)
        self.command = "%s %s" % (command, arguments)

        if recursive:
            self.command += ' recursive'

        if folder:
            # XXX: in this case the return status will always be 0 (success)!!
            self.command = 'echo "cd %s; %s" | tmsh | cat' % (folder, self.command)
        else:
            self.command = 'tmsh %s' % self.command

    def setup(self):
        ret = self.api.run(self.command)
        if not ret.status:
            return tmsh.parser(ret.stdout)
        else:
            LOG.error(ret)
            raise SSHCommandError(ret)


list = None
class List(Run):
    """Run a one line tmsh list command.

    >>> tmsh.list('sys db')

    @param arguments: the arguments for tmsh list
    @type arguments: str
    """
    def __init__(self, arguments, *args, **kwargs):
        super(List, self).__init__(arguments, command='list', *args, **kwargs)


list_software = None
class ListSoftware(CachedCommand, SSHCommand):
    """Run `tmsh list sys software`.

    For: bigip 10.1.0+, em 2.0.0+
    """

    def setup(self):

        v = get_version(ifc=self.ifc)

        if v < 'bigip 10.1.0' or v < 'em 2.0.0':
            raise CommandNotSupported('only in 10.1.0+')

        ret = self.api.run('tmsh list sys software')

        if not ret.status:
            return tmsh.parser(ret.stdout)
        else:
            LOG.error(ret)
            raise SSHCommandError(ret)


get_provision = None
class GetProvision(SSHCommand):
    """Run `tmsh list sys provision`.

    For: bigip 10.0.1+, em 2.0.0+
    """

    def setup(self):

        v = get_version(ifc=self.ifc)

        if v.product.is_bigip and v < 'bigip 10.0.1' or \
           v.product.is_em and v < 'em 2.0.0':
            raise CommandNotSupported('only in 10.0.1+ and em 2+')

        ret = self.api.run('tmsh list sys provision')

        if not ret.status:
            ret = tmsh.parser(ret.stdout)
            if v.product.is_bigip and v < 'bigip 10.0.2':
                modules = dict([(k.split(' ')[-1], v) for k, v in ret.glob('provision*').items()])
            else:
                modules = dict([(k.split(' ')[-1], v) for k, v in ret.glob('sys provision*').items()])
            return Options(modules)
        else:
            LOG.error(ret)
            raise SSHCommandError(ret)
