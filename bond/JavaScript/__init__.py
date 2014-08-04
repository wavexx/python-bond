from bond import *
import os
import pkg_resources
import json


# JavaScript constants
JS_PROMPT      = r'> '
JS_PRELUDE     = 'prelude.js'
JS_WRAP_PREFIX = '__PY_BOND'


class JavaScript(Bond):
    LANG = 'JavaScript'

    def __init__(self, cmd="nodejs", args="-e \"require('repl').start({ignoreUndefined: true, terminal: false})\"",
                 xargs="", cwd=None, env=os.environ, trans_except=False, timeout=None, logfile=None):
        cmd = ' '.join([cmd, args, xargs])
        proc = Spawn(cmd, cwd=cwd, env=env, timeout=timeout, logfile=logfile)
        try:
            proc.expect(JS_PROMPT)
        except pexpect.ExceptionPexpect as e:
            raise BondException(self.LANG, 'cannot get an interactive prompt using: ' + cmd)

        # inject our prelude
        code = pkg_resources.resource_string(__name__, JS_PRELUDE)
        code = code + "\n{JS_WRAP_PREFIX}_sendline();\n".format(JS_WRAP_PREFIX=JS_WRAP_PREFIX)
        proc.sendline('eval({code});'.format(code=json.dumps(code)))
        try:
            proc.expect(r'\r\n{prompt}'.format(prompt=JS_PROMPT))
        except pexpect.ExceptionPexpect as e:
            raise BondException(self.LANG, 'cannot initialize interpreter')

        # start the inner repl
        proc.sendline(r'{JS_WRAP_PREFIX}_start({trans_except});'.format(
            JS_WRAP_PREFIX=JS_WRAP_PREFIX, trans_except=int(trans_except)))
        super(JavaScript, self).__init__(proc, trans_except)
