from bond import *
import os
import pkg_resources
import re


# Perl constants
PERL_PROBE  = r'print uc("stage1\n");'
PERL_EOL_RE = r'\s*(?:###.*)?\n\s*'
PERL_STAGE1 = pkg_resources.resource_string(__name__, 'stage1.pl').decode('utf-8')
PERL_STAGE2 = pkg_resources.resource_string(__name__, 'stage2.pl').decode('utf-8')


class Perl(Bond):
    LANG = 'Perl'

    def __init__(self, cmd="perl", args="-d -e1", xargs="", cwd=None, env=os.environ,
                 trans_except=False, timeout=None, logfile=None):
        cmd = ' '.join([cmd, args, xargs])
        proc = Spawn(cmd, cwd=cwd, env=env, timeout=timeout, logfile=logfile)
        stage1 = re.sub(PERL_EOL_RE, '', PERL_STAGE1)
        stage2 = self.dumps({'code': PERL_STAGE2,
                             'func': '__PY_BOND_start',
                             'args': [trans_except]})
        self._init_2stage(proc, PERL_PROBE, stage1, stage2, trans_except)
