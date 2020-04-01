// This file is a stub to allow compiling without google logging

// Define logging macros
#define LOG(...) LogSink()
#define VLOG(...) LogSink()
#define DLOG(...) LogSink()

#define DCHECK(...) LogSink()
#define DCHECK_EQ(...) LogSink()
#define DCHECK_NE(...) LogSink()
#define DCHECK_LE(...) LogSink()

#include <string>

// Expose expected logging classes/functions
namespace google {

    const int INFO = 0;
    const int WARNING = 0;
    const int ERROR = 0;

    class LogSink {
        public:
        LogSink& operator<<(const std::string&) {
            return *this;
        }

        LogSink& operator <<(const int) {
            return *this;
        }

        LogSink& operator <<(void *) {
            return *this;
        }

        LogSink& operator <<(const char*) {
            return *this;
        }
    };

    class LogSeverity {
        public:
        LogSeverity(...) {
        }
    };

    class LogMessage {
        public:
        LogMessage(...) {
        }

        LogSink& stream() {
            return sink;
        }

        private:
        LogSink sink;
    };

    class AddLogSink {
    };

    class RemoveLogSink {
    };
}
