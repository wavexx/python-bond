from bond import *
import os

def Python(cmd=None, args=None, xargs='', cwd=None, env=os.environ,
           trans_except=True, protocol=None, compat=None, timeout=None, logfile=None):
    return bond('Python', cmd, args, xargs, cwd=cwd, env=env,
                trans_except=trans_except, timeout=timeout, logfile=logfile)
