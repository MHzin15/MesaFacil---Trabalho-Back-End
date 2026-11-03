"""Redação de capacidades privadas nos logs sob controle da aplicação."""
import logging
import re


INVITE = re.compile(r'(/convite/|/convites/)[^/?\s\"\']+', re.IGNORECASE)
PRIVATE_CONTEXT = re.compile(r'(atendimento_id=)[^&\s\"\']+', re.IGNORECASE)


def redact(value):
    text = INVITE.sub(r'\1[redigido]', str(value))
    return PRIVATE_CONTEXT.sub(r'\1[redigido]', text)


class PrivateTokenFilter(logging.Filter):
    def filter(self, record):
        record.msg = redact(record.getMessage())
        record.args = ()
        if record.exc_info:
            record.msg += '\n' + redact(logging.Formatter().formatException(record.exc_info))
            record.exc_info = None
            record.exc_text = None
        return True
