from bond import *
import os
import pkg_resources
import base64
import cPickle


# Python constants
PY_PROMPT      = r'>>> '
PY_PRELUDE     = 'prelude.py'
PY_WRAP_PREFIX = '__PY_BOND'


class Python(Bond):
    LANG = 'Python'

    def __init__(self, cmd="python", args="", xargs="", cwd=None, env=os.environ,
                 trans_except=True, protocol=-1, timeout=None, logfile=None):
        cmd = ' '.join([cmd, args, xargs])
        proc = Spawn(cmd, cwd=cwd, env=env, timeout=timeout, logfile=logfile)
        try:
            proc.expect(PY_PROMPT)
        except pexpect.ExceptionPexpect as e:
            raise BondException(self.LANG, 'cannot get an interactive prompt using: ' + cmd)

        # inject our prelude
        code = pkg_resources.resource_string(__name__, PY_PRELUDE)
        code = code + "\n{PY_WRAP_PREFIX}_sendline()\n".format(PY_WRAP_PREFIX=PY_WRAP_PREFIX)
        proc.sendline("exec({code})".format(code=repr(code)))
        try:
            proc.expect(r'\r\n{prompt}'.format(prompt=PY_PROMPT))
        except pexpect.ExceptionPexpect as e:
            raise BondException(self.LANG, 'cannot initialize interpreter')

        # start the inner repl
        proc.sendline(r'{PY_WRAP_PREFIX}_start({trans_except}, {protocol});'.format(
            PY_WRAP_PREFIX=PY_WRAP_PREFIX, trans_except=trans_except, protocol=protocol))

        self.protocol = protocol
        super(Python, self).__init__(proc, trans_except)


    # Use pickle with Python
    def dumps(self, *args):
        return base64.b64encode(cPickle.dumps(args, self.protocol))

    def loads(self, string):
        return cPickle.loads(base64.b64decode(string))[0]
