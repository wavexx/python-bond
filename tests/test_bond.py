from __future__ import print_function
import bond
from tests import *

def test_ser_err():
    py = bond.make_bond('Python', timeout=TIMEOUT)

    # test a local serialization error
    x = lambda x: x
    failed = False
    try:
        py.call('print', x)
    except bond.SerializationException as e:
        print(e)
        failed = (e.side == "local")
    assert(failed)


def test_export():
    py = bond.make_bond('Python', timeout=TIMEOUT)

    def call_me():
        return 42

    # check that export without a name
    py.export(call_me)
    assert(py.call('call_me') == 42)

    # check that export with explicit name
    py.export(call_me, 'call_me_again')
    assert(py.call('call_me_again') == 42)


def test_export_noret():
    def call_me():
        pass

    py = bond.make_bond('Python', timeout=TIMEOUT)
    py.export(call_me)
    assert(py.call('call_me') is None)


def test_proxy():
    py1 = bond.make_bond('Python', timeout=TIMEOUT)
    py1.eval_block(r'''def func_py1(arg):
        return arg + 1
    ''')

    py2 = bond.make_bond('Python', timeout=TIMEOUT)
    py1.proxy('func_py1', py2)

    assert(py2.call('func_py1', 0) == 1)
