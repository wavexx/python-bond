import nose.plugins.skip
import bond
import io
import os
import pexpect
import sys

# We keep the global timeout for testing way shorter than the default of 60.
# This is done to limit execution time when tests are broken and also to spot
# performance regressions.
TIMEOUT = int(os.environ.get('BOND_TIMEOUT', 1))


def knownfail(func):
    def wrapper():
        try:
            return func()
        except Exception as e:
            raise nose.plugins.skip.SkipTest("known failure")

    wrapper.__name__ = func.__name__
    return wrapper


def bond_repl_depth(repl):
    depth = 0
    while True:
        try:
            repl.eval('1')
        except bond.TerminatedException:
            break
        repl._proc.sendline('RETURN')
        depth += 1
    return depth


def _buffer_stdio(obj):
    if isinstance(obj, io.TextIOBase):
        ret = io.TextIOWrapper(io.BytesIO())
        ret.getvalue = lambda: ret.buffer.getvalue().decode(ret.encoding)
    else:
        import cStringIO
        ret = cStringIO.StringIO()
    return ret


class OutputCapture(object):
    def __enter__(self):
        self._stdout = sys.stdout
        self._stderr = sys.stderr
        sys.stdout = _buffer_stdio(self._stdout)
        sys.stderr = _buffer_stdio(self._stderr)

    def __exit__(self, type, value, traceback):
        sys.stdout.flush()
        sys.stderr.flush()
        self.stdout = sys.stdout.getvalue()
        self.stderr = sys.stderr.getvalue()
        sys.stdout = self._stdout
        sys.stderr = self._stderr
