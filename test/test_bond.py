from __future__ import print_function
import bond
from bond.Python import Python

def test_proxy():
    py1 = Python(timeout=1)
    py1.eval_block(r'''def func_py1(arg):
        return arg + 1
    ''')

    py2 = Python(timeout=1)
    py1.proxy('func_py1', py2)

    assert(py2.call('func_py1', 0) == 1)
