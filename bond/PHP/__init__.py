from bond import *
import os
import pkg_resources
import re


# PHP constants
PHP_PS1         = 'php > '
PHP_PS2         = 'php [({] '
PHP_CHUNK_SIZE  = 4096 - 2
PHP_EOL_RE      = r'(?:///.*)?\n\s*'
PHP_PRELUDE     = 'prelude.php'
PHP_WRAP_PREFIX = '__PY_BOND'


class PHP(Bond):
    LANG = 'PHP'

    def __init__(self, cmd="php", args="-a", xargs="", cwd=None, env=os.environ,
                 trans_except=False, timeout=None, logfile=None):
        cmd = ' '.join([cmd, args, xargs])
        proc = Spawn(cmd, cwd=cwd, env=env, timeout=timeout, logfile=logfile)
        try:
            proc.expect(PHP_PS1)
        except pexpect.ExceptionPexpect:
            raise BondException(self.LANG, 'cannot get an interactive prompt using: ' + cmd)

        # inject our prelude in small chunks (due to the line discipline input buffer limit)
        # TODO: this requires a better approach
        code = pkg_resources.resource_string(__name__, PHP_PRELUDE)
        chunks = re.split(PHP_EOL_RE, code)
        try:
            line = ""
            for chunk in chunks:
                if len(chunk) + len(line) > PHP_CHUNK_SIZE:
                    proc.sendline_noecho(line);
                    proc.expect([PHP_PS1, PHP_PS2])
                    line = ""
                line = line + chunk
            if line:
                proc.sendline_noecho(line);
                proc.expect(PHP_PS1)
        except pexpect.ExceptionPexpect:
            raise BondException(self.LANG, 'cannot initialize interpreter')

        # start the inner repl
        proc.sendline_noecho(r'{PHP_WRAP_PREFIX}_start({trans_except});'.format(
            PHP_WRAP_PREFIX=PHP_WRAP_PREFIX, trans_except=int(trans_except)))
        super(PHP, self).__init__(proc, trans_except)
