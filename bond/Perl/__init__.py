from bond import *
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

    def __init__(self, perl="perl", args="-d -e1", xargs="", timeout=None, logfile=None):
        cmd = ' '.join([perl, args, xargs])
        proc = Spawn(cmd, timeout=timeout, logfile=logfile)
        try:
            proc.expect(PERL_PROMPT)
        except pexpect.ExceptionPexpect as e:
            raise BondException('cannot start Perl')

        # inject our prelude
        code = pkg_resources.resource_string(__name__, PERL_PRELUDE)
        code = _strip_newlines(code)
        proc.sendline(r'{code}; "";'.format(
            PERL_WRAP_PREFIX=PERL_WRAP_PREFIX, code=code))
        try:
            proc.expect(r'\r\n{prompt}'.format(prompt=PERL_PROMPT))
        except pexpect.ExceptionPexpect as e:
            raise BondException('cannot initialize Perl')

        # start the inner repl
        proc.sendline(r'{PERL_WRAP_PREFIX}_start();'.format(
            PERL_WRAP_PREFIX=PERL_WRAP_PREFIX))
        super(Perl, self).__init__(proc)
