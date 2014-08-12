from bond import *
import os

def PHP(cmd=None, args=None, xargs='', cwd=None, env=os.environ,
        trans_except=False, protocol=None, compat=None, timeout=None, logfile=None):
    return bond('PHP', cmd, args, xargs, cwd=cwd, env=env,
                trans_except=trans_except, timeout=timeout, logfile=logfile)
