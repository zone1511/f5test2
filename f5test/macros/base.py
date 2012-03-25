"""Base classes for macros.

A macro is a collection of commands.
"""
import threading
import sys
from ..base import Aliasificator


class MacroError(Exception):
    """Base exception for all exceptions raised by macros."""
    pass


class Macro(object):
    
    __metaclass__ = Aliasificator

    def __init__(self, *args, **kwargs):
        self.commands = []
        self.completed_commands = []
        super(Macro, self).__init__(*args, **kwargs)

    def add_command(self, step):
        """In case of a failure, revert prep/setup commands"""
        self.commands.append(step)

    def prep(self):
        pass

    def setup(self):
        for step in self.commands:
            try:
                step.prep()
                step.setup()
            except:
                self.revert()
                raise

    def run(self):
        """In case of a failure, revert prep/setup commands"""
        try:
            self.prep()
            return self.setup()
        except:
            self.revert()
            raise
        finally:
            self.cleanup()

    def revert(self):
        """In case of a failure, revert prep/setup commands"""
        for step in reversed(self.completed_commands):
            step.revert()

    def cleanup(self):
        """Cleanup all commands"""
        for step in reversed(self.completed_commands):
            step.cleanup()


class MacroThread(threading.Thread):

    def __init__(self, macro, queue, *args, **kwargs):
        self.macro = macro
        self.queue = queue
        super(MacroThread, self).__init__(*args, **kwargs)
    
    def run(self):
        try:
            return self.macro.run()
        except:
            self.queue.put({self: sys.exc_info()})


class StageError(Exception):
    pass


class Stage(object):
    name = None
    parallelizable = True
