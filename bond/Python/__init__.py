from bond import *
import base64
import os
import pkg_resources
import re

try:
    import cPickle as pickle
except ImportError:
    import pickle


# Python constants
PY_PROBE  = r'print("stage1\n".upper())'
PY_EOL_RE = r'(?:\s*(?:###.*)?\n)+'
PY_STAGE1 = pkg_resources.resource_string(__name__, 'stage1.py').decode('utf-8')
PY_STAGE2 = pkg_resources.resource_string(__name__, 'stage2.py').decode('utf-8')


class Python(Bond):
    LANG = 'Python'

    def __init__(self, cmd="python", args="-i", xargs="", cwd=None, env=os.environ,
                 trans_except=True, protocol=-1, compat=False, timeout=None, logfile=None):
        if compat:
            trans_except = False
            protocol = 0
        self.protocol = protocol

        cmd = ' '.join([cmd, args, xargs])
        proc = Spawn(cmd, cwd=cwd, env=env, timeout=timeout, logfile=logfile)
        stage1 = re.sub(PY_EOL_RE, '\n', PY_STAGE1)
        stage1 = "exec({code})".format(code=repr(stage1))
        stage2 = repr({'code': PY_STAGE2,
                       'func': '__PY_BOND_start',
                       'args': [trans_except, protocol]})
        self._init_2stage(proc, PY_PROBE, stage1, stage2, trans_except)


    # Use pickle with Python
    def dumps(self, *args):
        return base64.b64encode(pickle.dumps(args, self.protocol))

    def loads(self, buf):
        return pickle.loads(base64.b64decode(buf))[0]
