from bond import *
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
        cmd = ' '.join([cmd, args, xargs])
        proc = Spawn(cmd, cwd=cwd, env=env, timeout=timeout, logfile=logfile)
        stage1 = re.sub(PY_EOL_RE, '\n', PY_STAGE1)
        stage1 = "exec({code})".format(code=repr(stage1))
        stage2 = repr({'code': PY_STAGE2,
                       'func': '__PY_BOND_start',
                       'args': [trans_except]})
        self._init_2stage(proc, PY_PROBE, stage1, stage2, trans_except)


    # Use pickle with Python
    def dumps(self, *args):
        return repr(pickle.dumps(args, 0)).encode('utf-8')

    def loads(self, buf):
        dec = eval(buf.decode('utf-8'))
        if not isinstance(dec, bytes): dec = dec.encode('utf-8')
        return pickle.loads(dec)[0]
