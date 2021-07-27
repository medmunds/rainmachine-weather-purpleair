# Intercept RainMachine logging (so it doesn't spam stdout)
import logging

from RMUtilsFramework.rmLogging import globalLogger


class CaptureHandler(logging.Handler):
    buffer = []

    def emit(self, record):
        formatted = self.format(record)
        self.buffer.append(formatted)

    def clear(self):
        self.buffer = []


capture_handler = CaptureHandler(logging.DEBUG)
globalLogger.logger.removeHandler(globalLogger.stdoutHandler)
globalLogger.logger.addHandler(capture_handler)


def get_log():
    return capture_handler.buffer


def clear_log():
    capture_handler.clear()
