import nose.plugins.skip
import pexpect

def knownfail(func):
    def wrapper():
        try:
            return func()
        except Exception as e:
            raise nose.plugins.skip.SkipTest("known failure")

    wrapper.__name__ = func.__name__
    return wrapper


def bond_repl_depth(bond):
    depth = 0
    while True:
        try:
            bond.eval('1')
        except (pexpect.EOF, pexpect.TIMEOUT):
            break
        bond._proc.sendline('RETURN')
        depth += 1
    return depth
