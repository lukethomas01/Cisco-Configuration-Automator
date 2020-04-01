import sys
import os

from .configuration import ConfigManager, ConfigurationScheme
from .version import VERSION


class LoggingConfiguration(ConfigurationScheme):
    LOGGER_NAME = "rook"
    FILE_NAME = "rookout/python-rook.log"
    LOG_TO_STDERR = False
    LOG_LEVEL = "INFO"
    PROPAGATE_LOGS = False
    LOG_TO_REMOTE = False
    DEBUG = False


class VersionConfiguration(ConfigurationScheme):
    VERSION = VERSION
    COMMIT = "CommitGoesHere"


class DefaultConfiguration(ConfigurationScheme):
    DEFAULT_CONFIG_FILE_NAME = "rookout-config.json"
    LOAD_FROM_APP_FOLDER = True
    IGNORE_FILE = "ignore-rookout-config"
    USER_CONFIGURATION_FILE = "rookout/rook-config.json"


class ErrorConfiguration(ConfigurationScheme):
    STACK_DEPTH = 10


class ProtobufConfiguration(ConfigurationScheme):
    NAMESPACE_SERIALIZER_DUMPING = r""


class ControllerAddress(ConfigurationScheme):
    HOST = 'wss://control.rookout.com'
    PORT = 443


class AgentComConfiguration(ConfigurationScheme):
    COMMAND_THREAD_NAME = "rookout_agent_com"
    MAX_MESSAGE_LENGTH = 100 * 1024 * 1024
    BACK_OFF = 0.2
    MAX_SLEEP = 60
    TIMEOUT = 2
    REQUEST_TIMEOUT_SECS = 30
    PING_TIMEOUT = 30
    PING_INTERVAL = 10
    RESET_BACKOFF_TIMEOUT = 3*60.0
    FLUSH_TIMEOUT = 3


class OutputConfiguration(ConfigurationScheme):
    FLUSH_TIME_INTERVAL = 0.25
    THREAD_NAME = "rookout_output_thread"
    MAX_ITEMS = 40
    MAX_LOG_ITEMS = 100
    MAX_STATUS_UPDATES = 100


class OutputWsConfiguration(ConfigurationScheme):
    MAX_STATUS_UPDATES = 200
    MAX_LOG_ITEMS = 200
    MAX_AUG_MESSAGES = 100
    BUCKET_REFRESH_RATE = 10


class InstrumentationConfig(ConfigurationScheme):
    ENGINE = "auto"
    MIN_TIME_BETWEEN_HITS_MS = 100
    MAX_AUG_TIME = 400


class ImportServiceConfig(ConfigurationScheme):
    USE_IMPORT_HOOK = True
    SYS_MODULES_QUERY_INTERVAL = 0.25
    THREAD_NAME = "rookout_import_service_thread"


class HttpServerServiceConfig(ConfigurationScheme):
    SERVICES_NAMES = ""


class GitConfig(ConfigurationScheme):
    GIT_COMMIT = None
    GIT_ORIGIN = None


manager = ConfigManager(sys.modules[__name__])
