from bond import *
import os
import shlex
import warnings

class Python(Bond):
    warnings.warn("Language constructors are deprecated."
                  " Please use ``bond.make_bond()`` directly.",
                  DeprecationWarning)

    def __init__(self, *args, **kwargs):
        pass

    def __new__(cls, cmd=None, args=None, xargs='', cwd=None, env=os.environ,
                trans_except=True, protocol=None, compat=None, timeout=60,
                logfile=None):
        if args is not None: args = shlex.split(args)
        if xargs is not None: xargs = shlex.split(xargs)
        return make_bond('Python', cmd, args, xargs, cwd=cwd, env=env,
                         trans_except=trans_except, timeout=timeout, logfile=logfile)
