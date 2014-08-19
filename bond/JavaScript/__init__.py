from bond import *
import os
import shlex
import warnings

class JavaScript(Bond):
    warnings.warn("Language constructors are deprecated."
                  " Please use ``bond.make_bond()`` directly.",
                  DeprecationWarning)

    def __init__(self, *args, **kwargs):
        pass

    def __new__(cls, cmd=None, args=None, xargs='', cwd=None, env=os.environ,
                trans_except=False, protocol=None, compat=None, timeout=60,
                logfile=None):
        def_args = True
        if args is None:
            args = []
        else:
            def_args = False
            args = shlex.split(args)
        if xargs is not None:
            args = args + shlex.split(xargs)
        return make_bond('JavaScript', cmd, args, cwd=cwd, env=env, def_args=def_args,
                         trans_except=trans_except, timeout=timeout, logfile=logfile)
