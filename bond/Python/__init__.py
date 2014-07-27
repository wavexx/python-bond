from bond import *
import pkg_resources
import re


# Python constants
PY_PROMPT      = r'>>> '
PY_PRELUDE     = 'prelude.py'
PY_WRAP_PREFIX = '__PY_BOND'


class Python(Bond):
    LANG = 'Python'

    def __init__(self, python="python", args="", xargs="", timeout=None):
        cmd = ' '.join([python, args, xargs])
        proc = Spawn(cmd, timeout=timeout, logfile=open("log", "w"))
        try:
            proc.expect(PY_PROMPT)
        except pexpect.ExceptionPexpect as e:
            raise StateException('cannot start Python')

        # inject our prelude
        code = pkg_resources.resource_string(__name__, PY_PRELUDE)
        code = code + "\n{PY_WRAP_PREFIX}_sendline()\n".format(PY_WRAP_PREFIX=PY_WRAP_PREFIX)
        line = r"exec({code})".format(code=repr(code))
        proc.sendline(line)
        try:
            proc.expect(r'\r\n{prompt}'.format(prompt=PY_PROMPT))
        except pexpect.ExceptionPexpect as e:
            raise StateException('cannot initialize Python')

        # start the inner repl
        proc.sendline(r'{PY_WRAP_PREFIX}_start();'.format(
            PY_WRAP_PREFIX=PY_WRAP_PREFIX))
        super(Python, self).__init__(proc)
