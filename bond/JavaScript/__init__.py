from bond import *
import os
import pkg_resources
import re


# JavaScript constants
JS_PROBE  = r'console.log("stage1".toUpperCase());'
JS_EOL_RE = r'\s*(?:///.*)?\n\s*'
JS_STAGE1 = pkg_resources.resource_string(__name__, 'stage1.js').decode('utf-8')
JS_STAGE2 = pkg_resources.resource_string(__name__, 'stage2.js').decode('utf-8')


class JavaScript(Bond):
    LANG = 'JavaScript'

    def __init__(self, cmd="nodejs", args="-i", xargs="", cwd=None, env=os.environ,
                 trans_except=False, timeout=None, logfile=None):
        cmd = ' '.join([cmd, args, xargs])
        proc = Spawn(cmd, cwd=cwd, env=env, timeout=timeout, logfile=logfile)
        stage1 = re.sub(JS_EOL_RE, '', JS_STAGE1)
        stage2 = self.dumps({'code': JS_STAGE2,
                             'func': '__PY_BOND_start',
                             'args': [trans_except]})
        self._init_2stage(proc, JS_PROBE, stage1, stage2, trans_except)
