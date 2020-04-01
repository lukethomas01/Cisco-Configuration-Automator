import sys
import os
import logging
import platform
from rook.exceptions.tool_exceptions import RookDependencyError

PLATFORM = sys.platform
CPYTHON = platform.python_implementation() == 'CPython'


class DummyExtension(object):
    pass


if PLATFORM in ('darwin', 'linux2', 'linux'):
    hook_installed = False
    original_os_fork = os.fork

    if CPYTHON:
        try:
            import native_extensions
        except Exception as e:
            raise RookDependencyError(e)
    else:
        native_extensions = DummyExtension()

    native_extensions.python_fork_handler_called = 1

    def os_fork_hook():
        try:
            from .singleton import singleton_obj

            singleton_obj.pre_fork()
        except:
            # TODO - remove
            import traceback
            traceback.print_exc()
            pass

        # Set "called" flag, to be checked in the
        # pthread_atfork, and reset after
        native_extensions.python_fork_handler_called = 1
        pid = original_os_fork()
        native_extensions.python_fork_handler_called = 0

        try:
            from .singleton import singleton_obj

            if pid == 0:
                # child

                # Clean all Rook state
                singleton_obj.post_fork_clean()

                # Shutdown external API
                from . import interface
                interface.stop()

                # restore original fork
                os.fork = original_os_fork
            else:
                # parent
                singleton_obj.post_fork_recover()
        except:
            # TODO - remove
            import traceback
            traceback.print_exc()
            pass

        return pid

    def install_fork_handler():
        global hook_installed, original_os_fork

        if hook_installed:
            return

        if CPYTHON:
            # due to occasional deadlocks in PyPy, pthread_atfork
            # functionality is disabled
            native_extensions.RegisterPreforkCallback()

        os.fork, hook_installed = os_fork_hook, True

    def remove_fork_handler():
        global hook_installed, original_os_fork

        os.fork, hook_installed = original_os_fork, False

else:
    def install_fork_handler():
        pass
