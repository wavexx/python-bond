from bond import *
import os
import pkg_resources
import re


# JavaScript constants
JS_PROMPT      = r'> '
JS_PRELUDE     = 'prelude.js'
JS_WRAP_PREFIX = '__PY_BOND'


def _strip_newlines(code):
    """Turn a JavaScript code block into one line, so that the nodejs console
    doesn't output cruft while interpreting it"""
    # TODO: We used to encode the source using json.dumps() and "eval" it
    #       remotely, but it seems that the nodejs console is interpreting
    #       our input incorrectly.
    return re.sub(r'(?:///.*)?\n\s*', '', code)


class JavaScript(Bond):
    LANG = 'JavaScript'

    def __init__(self, cmd="nodejs", args="-e \"require('repl').start({ignoreUndefined: true, terminal: false})\"",
                 xargs="", cwd=None, env=os.environ, trans_except=False, timeout=None, logfile=None):
        cmd = ' '.join([cmd, args, xargs])
        proc = Spawn(cmd, cwd=cwd, env=env, timeout=timeout, logfile=logfile)
        try:
            proc.expect(JS_PROMPT)
        except pexpect.ExceptionPexpect:
            raise BondException(self.LANG, 'cannot get an interactive prompt using: ' + cmd)

        # inject our prelude
        code = pkg_resources.resource_string(__name__, JS_PRELUDE)
        code = _strip_newlines(code)
        proc.sendline_noecho(r'{code}; {JS_WRAP_PREFIX}_sendline();'.format(
            JS_WRAP_PREFIX=JS_WRAP_PREFIX, code=code))
        try:
            proc.expect(r'\r\n{prompt}'.format(prompt=JS_PROMPT))
        except pexpect.ExceptionPexpect:
            raise BondException(self.LANG, 'cannot initialize interpreter')

        # start the inner repl
        proc.sendline_noecho(r'{JS_WRAP_PREFIX}_start({trans_except});'.format(
            JS_WRAP_PREFIX=JS_WRAP_PREFIX, trans_except=int(trans_except)))
        super(JavaScript, self).__init__(proc, trans_except)
