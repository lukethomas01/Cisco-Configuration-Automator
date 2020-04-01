from .namespace import Namespace
from .container_namespace import ContainerNamespace
from .python_object_namespace import PythonObjectNamespace

from rook.exceptions import RookAttributeNotFound, RookDependencyError, RookDependencyMissing


class TraceNamespace(Namespace):
    def __init__(self):
        super(TraceNamespace, self).__init__(self.METHODS)
        self.context = None

    def dump(self, args):
        self._load()
        return ContainerNamespace(
            {
                "service": self.read_attribute("service"),
                "meta": self.read_attribute("meta"),
                "resource": self.read_attribute("resource"),
                "name": self.read_attribute("name"),
                "type": self.read_attribute("type"),
            }
        )

    def read_attribute(self, name):
        self._load()

        if name == "meta":
            return PythonObjectNamespace(self.context.get_current_root_span().meta)
        elif name == "service":
            return PythonObjectNamespace(self.context.get_current_root_span().service)
        elif name == "resource":
            return PythonObjectNamespace(self.context.get_current_root_span().resource)
        elif name == "name":
            return PythonObjectNamespace(self.context.get_current_root_span().name)
        elif name == "type":
            return PythonObjectNamespace(self.context.get_current_root_span().type)

        raise RookAttributeNotFound(name)

    def _load(self):
        if self.context is not None:
            return

        try:
            import opentracing
            self.context = opentracing.tracer.get_call_context()
        except ImportError:
            try:
                import ddtrace
                self.context = ddtrace.tracer.get_call_context()
            except ImportError as import_err:
                raise RookDependencyMissing('opentracing/ddtrace', import_err)

    METHODS = (dump, )
