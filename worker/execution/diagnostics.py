"""Bounded safe RPC observations: never store arguments, responses or exception text."""
import threading
import time

PHASES = {'volume.inspect', 'worker.inspect', 'worker.reload', 'image.inspect',
          'create', 'inspect.before_start', 'attach', 'start', 'output_collection',
          'output_wait', 'inspect.after_output', 'kill', 'inspect.after_kill', 'wait',
          'stream.close', 'collector.join', 'inspect.cleanup', 'inspect.cleanup_labels',
          'remove', 'inspect.removal', 'workspace.populate', 'workspace.cleanup'}


class RpcTrace:
    MAX_EVENTS = 96

    def __init__(self):
        self.events = []
        self.lock = threading.Lock()
        self.origin = time.monotonic()
        self.last_failure = None
        self.truncated = False

    @staticmethod
    def category(error):
        name = type(error).__name__
        if name in ('ReadTimeout', 'ConnectTimeout', 'Timeout', 'TimeoutError'):
            return 'timeout'
        if name in ('ConnectionError', 'ProtocolError', 'SocketError'):
            return 'transport_error'
        if name in ('NotFound', 'ImageNotFound'):
            return 'not_found'
        if name == 'APIError':
            return 'daemon_error'
        if isinstance(error, OSError):
            return 'io_error'
        if isinstance(error, ValueError):
            return 'invalid_metadata'
        return 'internal_error'

    def note(self, phase, started, deadline_ms, outcome='ok', category=None):
        if phase not in PHASES or outcome not in ('ok', 'error', 'not_found', 'complete', 'incomplete', 'overflow', 'timeout'):
            raise ValueError('Invalid diagnostic vocabulary')
        entry = dict(phase=phase, start_ms=round((started-self.origin)*1000, 3),
                     elapsed_ms=round((time.monotonic()-started)*1000, 3),
                     deadline_ms=deadline_ms, outcome=outcome)
        if category is not None:
            entry['category'] = category
        with self.lock:
            if self.last_failure is None and (outcome == 'error' or (outcome == 'incomplete' and category)):
                self.last_failure = phase
            if len(self.events) < self.MAX_EVENTS:
                self.events.append(entry)
            else:
                self.truncated = True

    def call(self, phase, function, deadline_ms=10000, allow_not_found=False):
        started = time.monotonic()
        try:
            result = function()
        except Exception as error:
            category = self.category(error)
            self.note(phase, started, deadline_ms,
                      'not_found' if allow_not_found and category == 'not_found' else 'error', category)
            raise
        self.note(phase, started, deadline_ms)
        return result
