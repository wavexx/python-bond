from bond import *
import os
import pkg_resources
import re


# Perl constants
PERL_PROMPT      = r'  DB<\d+> '
PERL_PRELUDE     = 'prelude.pl'
PERL_WRAP_PREFIX = '__PY_BOND'


def _strip_newlines(code):
    """Turn a Perl code block into one line to be interpreted by an interactive prompt"""
    # TODO: this is buggy on several levels, but it's good enough for our
    #       prelude where we control the source.
    return re.sub(r'(?:#.*)?\n\s*', '', code)


class Perl(Bond):
    LANG = 'Perl'

    def __init__(self, cmd="perl", args="-d -e1", xargs="", cwd=None, env=os.environ,
                 trans_except=False, timeout=None, logfile=None):
        cmd = ' '.join([cmd, args, xargs])
        proc = Spawn(cmd, cwd=cwd, env=env, timeout=timeout, logfile=logfile)
        try:
            proc.expect(PERL_PROMPT)
        except pexpect.ExceptionPexpect:
            raise BondException(self.LANG, 'cannot get an interactive prompt using: ' + cmd)

        # inject our prelude
        code = pkg_resources.resource_string(__name__, PERL_PRELUDE)
        code = _strip_newlines(code)
        proc.sendline_noecho(r'{code}; "";'.format(
            PERL_WRAP_PREFIX=PERL_WRAP_PREFIX, code=code))
        try:
            proc.expect(r'\r\n{prompt}'.format(prompt=PERL_PROMPT))
        except pexpect.ExceptionPexpect:
            raise BondException(self.LANG, 'cannot initialize interpreter')

        # start the inner repl
        proc.sendline_noecho(r'{PERL_WRAP_PREFIX}_start({trans_except});'.format(
            PERL_WRAP_PREFIX=PERL_WRAP_PREFIX, trans_except=int(trans_except)))
        super(Perl, self).__init__(proc, trans_except)
