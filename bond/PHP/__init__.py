from bond import *
import os
import pkg_resources
import re


# PHP constants
PHP_PROMPT      = 'php > '
PHP_PRELUDE     = 'prelude.php'
PHP_WRAP_PREFIX = '__PY_BOND'


def _strip_newlines(code):
    """Turn a PHP code block into one line, so that an interactive PHP prompt
    does not output cruft while interpreting it"""
    # TODO: this is buggy on several levels. We could pre-process code using
    #       `php -w`, but it sounds prohibitive. It's good enough for our
    #       prelude though, where we control the source.
    return re.sub(r'(?:///.*)?\n\s*', '', code)


class PHP(Bond):
    LANG = 'PHP'

    def __init__(self, cmd="php", args="-a", xargs="", cwd=None, env=os.environ,
                 trans_except=False, timeout=None, logfile=None):
        cmd = ' '.join([cmd, args, xargs])
        proc = Spawn(cmd, cwd=cwd, env=env, timeout=timeout, logfile=logfile)
        try:
            proc.expect(PHP_PROMPT)
        except pexpect.ExceptionPexpect as e:
            raise BondException(self.LANG, 'cannot get an interactive prompt using: ' + cmd)

        # inject our prelude
        code = pkg_resources.resource_string(__name__, PHP_PRELUDE)
        code = _strip_newlines(code)
        proc.sendline(r'{code}; {PHP_WRAP_PREFIX}_sendline();'.format(
            PHP_WRAP_PREFIX=PHP_WRAP_PREFIX, code=code))
        try:
            proc.expect(r'\r\n{prompt}'.format(prompt=PHP_PROMPT))
        except pexpect.ExceptionPexpect as e:
            raise BondException(self.LANG, 'cannot initialize interpreter')

        # start the inner repl
        proc.sendline(r'{PHP_WRAP_PREFIX}_start({trans_except});'.format(
            PHP_WRAP_PREFIX=PHP_WRAP_PREFIX, trans_except=int(trans_except)))
        super(PHP, self).__init__(proc, trans_except)
