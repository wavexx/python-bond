from bond import *
import pkg_resources
import base64
import cPickle


# Python constants
PY_PROMPT      = r'>>> '
PY_PRELUDE     = 'prelude.py'
PY_WRAP_PREFIX = '__PY_BOND'


class Python(Bond):
    LANG = 'Python'

    def __init__(self, python="python", args="", xargs="", timeout=None,
                 logfile=None, protocol=-1):
        cmd = ' '.join([python, args, xargs])
        proc = Spawn(cmd, timeout=timeout, logfile=logfile)
        try:
            proc.expect(PY_PROMPT)
        except pexpect.ExceptionPexpect as e:
            raise BondException('cannot start Python')

        # inject our prelude
        code = pkg_resources.resource_string(__name__, PY_PRELUDE)
        code = code + "\n{PY_WRAP_PREFIX}_sendline()\n".format(PY_WRAP_PREFIX=PY_WRAP_PREFIX)
        line = r"exec({code})".format(code=repr(code))
        proc.sendline(line)
        try:
            proc.expect(r'\r\n{prompt}'.format(prompt=PY_PROMPT))
        except pexpect.ExceptionPexpect as e:
            raise BondException('cannot initialize Python')

        # start the inner repl
        proc.sendline(r'{PY_WRAP_PREFIX}_start({protocol});'.format(
            PY_WRAP_PREFIX=PY_WRAP_PREFIX,
            protocol=protocol))

        self.protocol = protocol
        super(Python, self).__init__(proc)


    # Use pickle with Python
    def dumps(self, *args):
        return base64.b64encode(cPickle.dumps(args, self.protocol))

    def loads(self, string):
        return cPickle.loads(base64.b64decode(string))[0]
