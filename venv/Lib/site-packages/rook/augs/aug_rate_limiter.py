from threading import Lock
from collections import OrderedDict


class AugRateLimiter(object):
    def __init__(self, quota, window_size):
        self._quota = quota
        self._window_size = window_size
        self._lock = Lock()

        self._windows = OrderedDict()

    def allow(self, now):
        if self._quota is None:
            return '0'

        now_ms = int(now * 1000)

        self._cleanup(now_ms)

        current_window_key = now_ms // self._window_size * self._window_size
        prev_window_key = current_window_key - self._window_size

        current_window_usage = self._windows.setdefault(current_window_key, 0)
        prev_window_usage = self._windows.get(prev_window_key)

        if prev_window_usage is None:
            if current_window_usage > self._quota:
                return None
        else:
            prev_weight = 1 - (now_ms - current_window_key) / float(self._window_size)
            weighted_usage = (prev_window_usage * prev_weight) + current_window_usage

            if weighted_usage > self._quota:
                return None

        return current_window_key

    def record(self, key, duration):
        if self._quota is None:
            return

        total_duration = self._windows.get(key)  # windows might be cleared while aug is running (unlikely)

        if total_duration is not None:
            self._windows[key] += int(duration * 1000)

    def _cleanup(self, now):
        # every 5 windows-times, clear windows older than 10 window-times
        locked = False

        try:
            locked = self._lock.acquire(False)

            if locked:
                if len(self._windows) > 10:
                    self._windows = {k: v for k, v in self._windows.items() if k < now - self._window_size * 5}
        finally:
            if locked:
                self._lock.release()
