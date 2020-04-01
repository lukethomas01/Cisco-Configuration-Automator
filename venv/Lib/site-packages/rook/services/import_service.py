import sys
import time
import threading

import six
import os
import inspect
import site
import imp
import hashlib

from rook.services.exts.cloud_debug_python.module_explorer import _GetLineNumbers
from six.moves import builtins

from rook.logger import logger

from rook.config import ImportServiceConfig

from rook.serverless import on_lambda

from rook.exceptions.tool_exceptions import RookDependencyError, RookSourceFilePathSuggestion

from rook.file_utils import FileUtils

from rook.processor.error import Error

_SUPPORTED_PY_FORMATS = ['.py', '.pyc']

_BLACKLISTED_PATHS = []


# TODO - review if we can move to a standard lock instead of the import lock
class CountingImportLock(object):
    """
    When locked, only this thread can import (so all imports are guaranteed to have completed,
                                              and there are no partially initialized modules in sys.modules)
    """
    def __init__(self):
        self._count = 0

    def __enter__(self):
        imp.acquire_lock()
        self._count += 1

    def __exit__(self, *args, **kwargs):
        self._count -= 1
        imp.release_lock()

    def get_recursion_count(self):
        return self._count


class ImportService(object):

    NAME = "Import"

    class Notification(object):
        def __init__(self, module_name, module_filename, include_externals, lineno, callback, removed, aug, file_hash):
            self.module_name = module_name
            self.module_filename = module_filename
            self.callback = callback
            self.removed = removed
            self.include_externals = include_externals
            self.lineno = lineno
            self.aug = aug
            self.file_hash = file_hash

    def __init__(self, bdb_location_service):
        self._bdb_location_service = bdb_location_service

        self._modules = frozenset(sys.modules.keys())
        self._path_cache = {}
        self._post_import_notifications = {}

        self._thread = None
        self._quit = False

        self._old_import = None

        self.file_utils = FileUtils()

        external_paths = [sys.exec_prefix]
        if hasattr(site, 'getsitepackages'):
            external_paths = external_paths + site.getsitepackages()

        self.external_paths = [os.path.normcase(os.path.realpath(external_path))
                               for external_path in external_paths]

        if on_lambda():
            _BLACKLISTED_PATHS.extend(['/var/task/flask', '/var/task/chalice'])

        import platform
        if platform.system() != 'Windows' and ImportServiceConfig.USE_IMPORT_HOOK:
            platform = platform.python_implementation().lower()

            def import_hook(*args, **kwargs):
                """
                Declared here to make it obvious that you can't replace the function by monkeypatching -
                the C extension will always reference the function set with SetImportHook.
                """
                __rookout__tracebackhide__ = True
                # Locking the global import lock here extends the section for which it is locked -
                # we don't want the import hook to be called from two threads simultaneously,
                # but the scope in which the import lock is held might only encompass the call to the original
                # __import__. The import lock is re-entrant, so it's OK for us to lock it and then for Python
                # to lock it again.
                with import_hook.import_lock:
                    result = self._old_import(*args, **kwargs)

                    # TODO - review if we can process the module being loaded regardless instead of evaluating the full list
                    try:
                        # if the recursion count is > 1,
                        # then this call to import_hook is a nested import, which means that the parent
                        # import has not finished executing its code yet, but it's already in sys.modules.
                        # if we evaluate now, we will try to place BPs in the module before it finished executing,
                        # potentially resulting in CodeNotFound.
                        if import_hook.import_lock.get_recursion_count() == 1:
                            self.evaluate_module_list()
                    except:
                        pass

                    return result
            # this must be a reentrant lock - imports can cause other imports
            import_hook.import_lock = CountingImportLock()

            if platform == "cpython":
                try:
                    import native_extensions
                except Exception as e:
                    raise RookDependencyError(e)

                logger.debug('Enabling native import hook')
                native_extensions.SetImportHook(import_hook)
                # atomic swap
                builtins.__import__, self._old_import = native_extensions.CallImportHookRemovingFrames, builtins.__import__
            elif platform == "pypy":
                import __pypy__
                logger.debug('Enabling pypy import hook')
                # atomic swap
                builtins.__import__, self._old_import = __pypy__.hidden_applevel(import_hook), builtins.__import__
            else:
                # assertion should never be reached, singleton.py checks platform support
                raise AssertionError("Unsupported platform")
        else:
            self._thread = threading.Thread(target=self._query_thread,
                                            name=ImportServiceConfig.THREAD_NAME)
            self._thread.daemon = True
            self._thread.start()

    def close(self):
        if self._old_import:
            builtins.__import__ = self._old_import

        if self._thread:
            self._quit = True

            # If threading was monkey patched by gevent waiting on thread will likely throw an exception
            try:
                from gevent.monkey import is_module_patched
                if is_module_patched("threading"):
                    time.sleep(ImportServiceConfig.SYS_MODULES_QUERY_INTERVAL)
            except:
                pass

            self._thread.join()

    def register_post_import_notification(self, aug, name, filepath, aug_file_hash, include_externals, lineno, callback, removed):
        # Normalize file path
        if filepath:
            filepath = os.path.normcase(os.path.normpath(filepath))

        filename = os.path.basename(filepath) if filepath else None
        notification = self.Notification(name, filepath, include_externals, lineno, callback, removed, aug, aug_file_hash)

        # Register notification for future loads
        self._post_import_notifications[aug.aug_id] = notification

        match_found = False
        file_hashes = {}
        with CountingImportLock():
            # Attempt to satisfy notification using known modules
            for module_name in self._modules:
                module_object = sys.modules[module_name]

                # Get module details and check if it matches
                module_filename = self._get_module_path(module_object)

                # If module is not valid, ignore
                if not self._is_valid_module(module_object, module_filename):
                    continue

                if filename == os.path.basename(module_object.__file__):
                    file_content = self.file_utils.get_safe_file_contents(module_object)
                    if file_content:
                        file_hash = hashlib.sha256(file_content).hexdigest()
                        file_hashes[file_hash] = inspect.getsourcefile(module_object)

                if module_filename:
                    if self._does_module_match_notification(module_object.__name__, module_filename, notification, self.external_paths):
                        match_found = True
                        notification.callback(module_object)

        if not match_found:
            if aug_file_hash in file_hashes:
                aug.send_warning(Error(exc=RookSourceFilePathSuggestion(filepath, file_hashes[aug_file_hash])))

    def remove_aug(self, aug_id):
        notification = self._post_import_notifications.pop(aug_id, None)
        if notification is None:
            return

        notification.removed()

    def clear_augs(self):
        # This does not require a lock - `notifications` may be added to or removed from in a different thread
        # while we still haven't replaced it with an empty dict(),
        # but `notifications` is just a pointer to the same dict object pointed to by
        # `_post_import_notifications`. Once we do replace `_post_import_notifications`
        # with a new dict, we can be sure that no more notifications will be added.
        # At that point, it's safe to iterate over `notifications` and remove all notifications.
        notifications = self._post_import_notifications
        self._post_import_notifications = dict()
        for notification in six.itervalues(notifications):
            notification.removed()

    def pre_fork(self):
        CountingImportLock().__enter__()

    def post_fork(self):
        try:
            CountingImportLock().__exit__()
        except RuntimeError:
            # This is a bit of a heck as we don't seem to hold import lock in the child.
            # See the TODO about migrating away from the import lock.
            pass

    def _is_valid_module(self, module_object, module_filename):
        return module_filename and os.path.splitext(module_filename)[1] in _SUPPORTED_PY_FORMATS and \
            module_object and inspect.ismodule(module_object) and hasattr(module_object, '__file__')

    def _query_thread(self):
        logger.debug('Starting ImportService thread')
        self._bdb_location_service.ignore_current_thread()

        while not self._quit:
            try:
                with CountingImportLock():
                    self.evaluate_module_list()
            except:
                if logger:
                    logger.exception("Error while evaluating module list")

            # time can be None if interpreter is in shutdown
            if not time:
                return
            time.sleep(ImportServiceConfig.SYS_MODULES_QUERY_INTERVAL)

    def evaluate_module_list(self):
        try:
            # Nobody is waiting for notifications
            if not self._post_import_notifications:
                return

            # No new modules
            if len(self._modules) == len(sys.modules):
                return

            # Get a fresh list
            module_names = frozenset(sys.modules.keys())
            # self._modules is only replaced (it's immutable - a frozenset), so there's no need to copy it here,
            # just keep a reference to the current self._modules so we don't start working on a different set
            # mid-loop
            old_modules = self._modules

            # For everybody not in the old list, check notifications
            for module_name in module_names:
                module = sys.modules[module_name]
                module_filename = self._get_module_path(module)
                if module_name not in old_modules and self._is_valid_module(module, module_filename):
                    self._notify_of_new_module(module.__name__, module, module_filename)

            # Update the "old" list
            self._modules = module_names

        except:
            logger.exception("Exception in ImportService")

    def _notify_of_new_module(self, module_name, module_object, module_filename):
        self._trigger_all_notifications_for_module(module_filename, module_name, module_object)

    def _trigger_all_notifications_for_module(self, module_filename, module_name, module):
        if module_filename:
            for aug_id, notification in six.iteritems(self._post_import_notifications.copy()):
                if self._does_module_match_notification(module_name, module_filename, notification,
                                                        self.external_paths):
                    try:
                        notification.callback(module)
                    except:
                        logger.exception("Error on module load callback")
                elif os.path.basename(notification.module_filename) == os.path.basename(module_filename):
                    file_content = self.file_utils.get_safe_file_contents(module)
                    if file_content:
                        file_hash = hashlib.sha256(file_content).hexdigest()
                        if notification.file_hash == file_hash:
                            notification.aug.send_warning(Error(exc=RookSourceFilePathSuggestion(notification.module_filename, module_filename)))

    def _get_module_path(self, module):
        if module is None or not hasattr(module, '__name__') or not hasattr(module, '__file__'):
            return None
        result = self._path_cache.get(module.__name__)

        if result is not None:
            return result

        if module:
            try:
                path = inspect.getsourcefile(module)
                if not path:
                    if module.__file__.endswith('.pyc'):
                        path = module.__file__.replace('.pyc', '.py')
            except:
                return None

            if path:
                result = os.path.realpath(os.path.normcase(os.path.abspath(path)))
                self._path_cache[module.__name__] = result
                return result

        return None

    @staticmethod
    def is_black_listed_path(path):
        for blacklisted_path in _BLACKLISTED_PATHS:
            if path.startswith(blacklisted_path):
                return True
        return False

    @staticmethod
    def _does_module_match_notification(module_name, module_filename, notification, external_paths):
        if not notification.include_externals:
            for external_path in external_paths:
                if module_filename.startswith(external_path):
                    return False

        if notification.module_filename and ImportService.path_contains_path(module_filename, notification.module_filename) or \
                        notification.module_name and module_name == notification.module_name and \
                        not ImportService.is_black_listed_path(module_filename):
            return True
        else:
            return False

    @staticmethod
    def _does_code_object_match_notification(code_object, notification):
        return notification.lineno in _GetLineNumbers(code_object)

    @staticmethod
    def path_contains_path(full_path, partial_path):
        if full_path.endswith(partial_path):
            return len(full_path) == len(partial_path) or full_path[-len(partial_path)-1] in ('/', '\\')
        else:
            return False
