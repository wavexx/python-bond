from bond import *
import os
import pkg_resources
import re


# PHP constants
PHP_PROBE  = r'echo strtoupper("stage1\n");'
PHP_EOL_RE = r'\s*(?:///.*)?\n\s*'
PHP_STAGE1 = pkg_resources.resource_string(__name__, 'stage1.php').decode('utf-8')
PHP_STAGE2 = pkg_resources.resource_string(__name__, 'stage2.php').decode('utf-8')


class PHP(Bond):
    LANG = 'PHP'

    def __init__(self, cmd="php", args="-a", xargs="", cwd=None, env=os.environ,
                 trans_except=False, timeout=None, logfile=None):
        cmd = ' '.join([cmd, args, xargs])
        proc = Spawn(cmd, cwd=cwd, env=env, timeout=timeout, logfile=logfile)
        stage1 = re.sub(PHP_EOL_RE, '', PHP_STAGE1)
        stage2 = self.dumps({'code': PHP_STAGE2,
                             'func': '__PY_BOND_start',
                             'args': [trans_except]})
        self._init_2stage(proc, PHP_PROBE, stage1, stage2, trans_except)
