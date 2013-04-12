from .base import SSHCommand
from .ssh import get_version
from ..base import CachedCommand
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


list = None
class List(SSHCommand):
    """Run a generic one line bigpipe command.

    >>> bigpipe.generic('list')

    @param command: the arguments for tmsh
    @type command: str
    """
    def __init__(self, command, recursive=False, folder='/Common', *args, **kwargs):

        super(List, self).__init__(*args, **kwargs)
        # tmsh doesn't support working with folders when called from shell
        self.command = 'echo "cd %s; list %s %s" | tmsh | cat' % (folder,
                                                                  command,
                                                                  recursive and 'recursive' or '')

    def setup(self):
        ret = self.api.run(self.command)
        if not ret.status:
            return tmsh.parser(ret.stdout)
        else:
            LOG.error(ret)
            raise SSHCommandError(ret)


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
