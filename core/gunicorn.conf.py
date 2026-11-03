from gunicorn.glogging import Logger
from restaurante.logging import redact


class PrivateLogger(Logger):
    def atoms(self, resp, req, environ, request_time):
        return {key: redact(value) if isinstance(value, str) else value
                for key, value in super().atoms(resp, req, environ, request_time).items()}


logger_class = PrivateLogger
accesslog = '-'
errorlog = '-'
access_log_format = '%(h)s %(t)s "%(r)s" %(s)s %(b)s %(L)s'
