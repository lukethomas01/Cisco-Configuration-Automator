import socket
import threading
import time
from six.moves.queue import Queue, Empty
from six.moves.urllib.parse import urlparse
import select
import errno
import certifi
import ssl
import re
import os

import six
import websocket

from rook.exceptions import RookCommunicationException, RookInvalidToken, RookDependencyConflict
import rook.com_ws.socketpair_compat  # do not remove - adds socket.socketpair on Windows

try:
    from websocket import WebSocketBadStatusException
except ImportError:
    raise RookDependencyConflict('websocket')

# Python < 2.7.9 is missing important SSL features for websocket
# (unless supplied by CentOS etc)
if not websocket._ssl_compat.HAVE_SSL:
    try:
        import backports.ssl
        import backports.ssl_match_hostname
        import OpenSSL
        websocket._http.ssl = backports.ssl
        websocket._http.HAVE_SSL = True
        websocket._http.HAVE_CONTEXT_CHECK_HOSTNAME = True
    except ImportError:
        six.print_('[Rookout] Python is missing modern SSL features. To rectify, please run:\n'
                   '  pip install rook[ssl_backport]')

from rook.com_ws import information
from rook.logger import logger
import rook.protobuf.messages_pb2 as messages_pb
import rook.protobuf.envelope_pb2 as envelope_pb
from rook.config import AgentComConfiguration, VersionConfiguration


def wrap_in_envelope(message):
    envelope = envelope_pb.Envelope()
    envelope.timestamp.GetCurrentTime()
    envelope.msg.Pack(message)

    return envelope


class ExitThreadSentinel(object):
    pass


class FlushMessagesEvent(object):
    def __init__(self):
        self.event = threading.Event()


class MessageCallback(object):
    def __init__(self, cb, persistent):
        self.cb = cb
        self.persistent = persistent


class AgentCom(object):
    def __init__(self, agent_id, host, port, proxy, token, labels, tags):
        self.id = agent_id

        self._thread = threading.Thread(name="rookout-" + type(self).__name__, target=self._connect)
        self._thread.daemon = True

        self._host = host if '://' in host else 'ws://' + host
        self._port = port
        self._proxy = proxy
        self._token = token
        self._token_valid = False
        self._labels = labels or {}
        self._tags = tags or []

        self._loop = None
        self._connection = None
        self._queue = Queue()

        self._running = True

        self._ready_event = threading.Event()
        self._connection_error = None

        self._callbacks = {}

        def set_ready_event(*args):
            self._ready_event.set()

        self.once('InitialAugsCommand', set_ready_event)

    def start(self):
        self._thread.start()

    def stop(self):
        self._running = False

        if self._connection is not None:
            self._connection.close(1000)

    def add(self, message):
        self._queue.put(wrap_in_envelope(message))

    def on(self, message_name, callback):
        self._register_callback(message_name, MessageCallback(callback, True))

    def once(self, message_name, callback):
        self._register_callback(message_name, MessageCallback(callback, False))

    def await_message(self, message_name):
        event = threading.Event()
        self.once(message_name, lambda _: event.set())

        return event

    def wait_for_ready(self, timeout=None):
        if not self._ready_event.wait(timeout):
            raise RookCommunicationException()
        else:
            if self._connection_error is not None:
                raise self._connection_error

    def _connect(self):
        retry = 0
        backoff = AgentComConfiguration.BACK_OFF
        connected = False
        last_successful_connection = 0

        while self._running:
            try:
                try:
                    if connected and time.time() >= last_successful_connection + AgentComConfiguration.RESET_BACKOFF_TIMEOUT:
                        retry = 0
                        backoff = AgentComConfiguration.BACK_OFF

                    self._connection = self._create_connection()

                    self._register_agent()

                except websocket.WebSocketBadStatusException as e:
                    if not self._token_valid and e.status_code == 403:  # invalid token
                        self._connection_error = RookInvalidToken(self._token)
                        self._ready_event.set()

                        logger.error('Connection failed; %s', self._connection_error.get_message())
                    raise
            except Exception as e:
                retry += 1
                backoff = min(backoff * 2, AgentComConfiguration.MAX_SLEEP)
                connected = False

                if hasattr(e, 'message') and e.message:
                    reason = e.message
                else:
                    reason = str(e)

                logger.info('Connection failed; reason = %s, retry = #%d, waiting %.3fs', reason, retry, backoff)

                time.sleep(backoff)
                continue
            else:
                connected = True
                last_successful_connection = time.time()

            logger.debug("WebSocket connected successfully")
            self._token_valid = True

            stop_socket_incoming, incoming_client_socket = socket.socketpair()
            outgoing_exit_sentinel = ExitThreadSentinel()

            def signal_stop_incoming_thread():
                # Logging is not safe here, interpreter might be shutting down
                try:
                    stop_socket_incoming.send(b'1')
                except socket.error as socket_error:
                    if socket_error.errno == errno.EPIPE:
                        return

                    logger.debug("Failed to signal stop", exc_info=1)
                except Exception:
                    logger.debug("Failed to signal stop", exc_info=1)
                finally:
                    stop_socket_incoming.close()

            def signal_stop_outgoing_thread():
                # Logging is not safe here, interpreter might be shutting down
                try:
                    incoming_client_socket.close()
                except:
                    pass

                try:
                    self._queue.put(outgoing_exit_sentinel)
                except Exception:
                    logger.debug("Failed to signal stop", exc_info=1)

            routines = [threading.Thread(name="rookout-incoming-thread", target=self._incoming, args=(incoming_client_socket, signal_stop_outgoing_thread)),
                        threading.Thread(name="rookout-outgoing-thread", target=self._outgoing, args=(outgoing_exit_sentinel, signal_stop_incoming_thread))]

            got_initial_augs = self.await_message('InitialAugsCommand')

            for routine in routines:
                routine.daemon = True
                routine.start()

            if got_initial_augs.wait(AgentComConfiguration.TIMEOUT):
                logger.info("Finished initialization")
            else:
                logger.warning("Timeout waiting for initial augs")

            for routine in routines:
                routine.join()

            logger.debug("Reconnecting")

    def _incoming(self, stop_socket, on_exit):
        try:
            while True:
                try:
                    rlist, _, xlist = select.select([self._connection, stop_socket], [], [self._connection, stop_socket], AgentComConfiguration.PING_TIMEOUT)
                    if stop_socket in rlist or stop_socket in xlist or self._connection in xlist:
                        break  # signaled to stop

                    if len(rlist) == 0 and len(xlist) == 0:
                        logger.debug("Incoming thread - ping timeout")
                        break  # select timed out - ping timeout

                    # it wasn't stop_socket, so it's self._connection -> we can read. we have to read including
                    # control frames, otherwise select might return and recv() wouldn't actually return anything
                    code, msg = self._connection.recv_data(control_frame=True)
                    if code != websocket.ABNF.OPCODE_BINARY:
                        continue

                    if msg is None:
                        # socket disconnected
                        logger.debug("Incoming thread - socket disconnected")
                        break

                    envelope = envelope_pb.Envelope()
                    envelope.ParseFromString(msg)
                    self._handle_incoming_message(envelope)
                except (socket.error, websocket.WebSocketConnectionClosedException):
                    logger.debug("Incoming thread - socket disconnected")
                    break
        except:
            logger.exception("Incoming thread failed")

        finally:
            on_exit()

    def flush_all_messages(self):
        flush_event = FlushMessagesEvent()
        self._queue.put(flush_event)
        flush_event.event.wait(AgentComConfiguration.FLUSH_TIMEOUT)

    def _outgoing(self, outgoing_exit_sentinel, on_exit):
        try:
            last_ping = time.time()
            self._connection.ping()

            while True:
                msg = None
                if (time.time() - last_ping) >= AgentComConfiguration.PING_INTERVAL:
                    last_ping = time.time()
                    self._connection.ping()

                try:
                    msg = self._queue.get(timeout=AgentComConfiguration.PING_INTERVAL)
                    if isinstance(msg, ExitThreadSentinel):
                        if msg is outgoing_exit_sentinel:
                            break
                        continue  # if it's an ExitThreadSentinel but not from this specific thread, just skip it
                    if isinstance(msg, FlushMessagesEvent):
                        msg.event.set()
                        continue
                    self._send(msg)
                except Empty:
                    continue
                except (socket.error, websocket.WebSocketConnectionClosedException):
                    if msg is not None:
                        self._queue.put(msg)
                    break
        except:
            logger.exception("Outgoing thread failed")

        finally:
            on_exit()

    def _create_connection(self):
        url = '{}:{}/v1'.format(self._host, self._port)
        headers = {
            'User-Agent': 'RookoutAgent/{}+{}'.format(VersionConfiguration.VERSION, VersionConfiguration.COMMIT)
        }

        if self._token is not None:
            headers["X-Rookout-Token"] = self._token

        proxy_host, proxy_port = self._get_proxy()

        connect_args = (url,)
        connect_kwargs = dict(header=headers,
                              timeout=AgentComConfiguration.TIMEOUT,
                              http_proxy_host=proxy_host, http_proxy_port=proxy_port)

        if os.environ.get('ROOKOUT_NO_HOST_HEADER_PORT') == '1':
            host = re.sub(':\d+$', '', urlparse(url).netloc)
        else:
            host = None

        try:
            # connect using system certificates
            conn = websocket.create_connection(*connect_args, host=host, **connect_kwargs)
        # In some very specific scenario, you cannot
        # reference ssl.CertificateError because it does
        # exist, so instead we get with with getattr
        # (None never matches an exception)
        except (ssl.SSLError, getattr(ssl, 'CertificateError', None)):
            # connect using certifi certificate bundle
            # (Python 2.7.15+ from python.org on macOS rejects our CA, see RK-3383)
            connect_kwargs['sslopt'] = dict(ca_certs=certifi.where())
            logger.debug("Got SSL error when connecting using system CA cert store, falling back to certifi")
            conn = websocket.create_connection(*connect_args, **connect_kwargs)
        conn.settimeout(None)
        return conn

    def _get_proxy(self):
        if self._proxy is None:
            return None, None

        try:
            if not self._proxy.startswith("http://"):
                self._proxy = "http://" + self._proxy

            url = urlparse(self._proxy, "http://")

            logger.debug("Connecting via proxy: %s", url.netloc)

            return url.hostname, url.port
        except ValueError:
            return None, None

    def _register_agent(self):
        logger.info('Registering agent with id %s', self.id)
        info = information.collect()
        info.agent_id = self.id
        info.labels = self._labels
        info.tags = self._tags

        m = messages_pb.NewAgentMessage()
        m.agent_info.CopyFrom(information.pack_agent_info(info))

        return self._send(wrap_in_envelope(m))

    AcceptedMessageTypes = [
        messages_pb.InitialAugsCommand,
        messages_pb.AddAugCommand,
        messages_pb.ClearAugsCommand,
        messages_pb.PingMessage,
        messages_pb.RemoveAugCommand
    ]

    def _handle_incoming_message(self, envelope):
        for message_type in self.AcceptedMessageTypes:
            if envelope.msg.Is(message_type.DESCRIPTOR):
                message = message_type()
                envelope.msg.Unpack(message)
                type_name = message.DESCRIPTOR.name

                callbacks = self._callbacks.get(type_name)

                if callbacks:
                    persistent_callbacks = []

                    # Trigger all persistent callbacks first
                    for callback in callbacks:
                        try:
                            if callback.persistent:
                                callback.cb(message)
                        except:
                            pass
                        finally:
                            if callback.persistent:
                                persistent_callbacks.append(callback)

                    # Trigger all non persistent callbacks
                    for callback in callbacks:
                        try:
                            if not callback.persistent:
                                callback.cb(message)
                        except:
                            pass

                    self._callbacks[type_name] = persistent_callbacks

    def _send(self, message):
        return self._connection.send_binary(message.SerializeToString())

    def _register_callback(self, message_name, callback):
        self._callbacks.setdefault(message_name, []).append(callback)
