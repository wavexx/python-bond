from bond import *
import os
import pkg_resources
import base64

try:
    import cPickle as pickle
except ImportError:
    import pickle


# Python constants
PY_PROMPT      = r'>>> '
PY_PRELUDE     = 'prelude.py'
PY_WRAP_PREFIX = '__PY_BOND'


class Python(Bond):
    LANG = 'Python'

    def __init__(self, cmd="python", args="-i", xargs="", cwd=None, env=os.environ,
                 trans_except=True, protocol=-1, compat=False, timeout=None, logfile=None):
        if compat:
            trans_except = False
            protocol = 0

        cmd = ' '.join([cmd, args, xargs])
        proc = Spawn(cmd, cwd=cwd, env=env, timeout=timeout, logfile=logfile)
        tty.setraw(proc)
        try:
            proc.expect_exact(PY_PROMPT)
        except pexpect.ExceptionPexpect:
            raise BondException(self.LANG, 'cannot get an interactive prompt using: ' + cmd)

        # inject our prelude
        code = pkg_resources.resource_string(__name__, PY_PRELUDE).decode('utf-8')
        proc.sendline_noecho("exec({code})".format(code=repr(code)))
        try:
            proc.expect_exact(PY_PROMPT)
        except pexpect.ExceptionPexpect:
            raise BondException(self.LANG, 'cannot initialize interpreter')

        # start the inner repl
        proc.sendline_noecho(r'{PY_WRAP_PREFIX}_start({trans_except}, {protocol});'.format(
            PY_WRAP_PREFIX=PY_WRAP_PREFIX, trans_except=trans_except, protocol=protocol))

        self.protocol = protocol
        super(Python, self).__init__(proc, trans_except)


    # Use pickle with Python
    def dumps(self, *args):
        return base64.b64encode(pickle.dumps(args, self.protocol))

    def loads(self, buf):
        return pickle.loads(base64.b64decode(buf))[0]
