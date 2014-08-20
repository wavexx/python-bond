from __future__ import print_function
import bond
from tests import *

def test_basic():
    py = bond.make_bond('Python', timeout=TIMEOUT)
    py.close()


def test_basic_rmt():
    py = bond.make_bond('Python', "ssh localhost python", timeout=TIMEOUT)
    py.close()


def _test_call_marshalling(py):
    py.eval_block(r'''def test_str():
        return "Hello world!"
    ''')
    assert(str(py.call('test_str')) == "Hello world!")

    py.eval_block(r'''def test_array():
        return [42]
    ''')
    assert(py.call('test_array') == [42])

    py.eval_block(r'''def test_number():
        return 42
    ''')
    assert(py.call('test_number') == 42)

    py.eval_block(r'''def test_nothing():
        pass
    ''')
    assert(py.call('test_nothing') is None)

    py.eval_block(r'''def test_identity(arg):
        return arg
    ''')
    py_identity = py.callable('test_identity')
    for value in [True, False, 0, 1, "String", [], [u"String"]]:
        ret = py_identity(value)
        print("{} => {}".format(value, ret))
        assert(str(ret) == str(value))

    py.eval_block(r'''def test_multi_arg(arg1, arg2):
        return arg1 + ' ' + arg2
    ''')
    assert(str(py.call('test_multi_arg', "Hello", "world!")) == "Hello world!")

    py.eval_block(r'''def test_nested(arg):
        return test_identity(arg)
    ''')
    py_nested = py.callable('test_nested')
    for value in [True, False, 0, 1, "String", [], [u"String"]]:
        ret = py_nested(value)
        print("{} => {}".format(value, ret))
        assert(str(ret) == str(value))

def test_call_marshalling_native():
    py = bond.make_bond('Python', timeout=TIMEOUT)
    _test_call_marshalling(py)

def test_call_marshalling_baseline():
    py = bond.make_bond('Python', protocol='JSON', timeout=TIMEOUT)
    _test_call_marshalling(py)


def test_call_simple():
    py = bond.make_bond('Python', timeout=TIMEOUT)

    # define a function and call it
    py.eval_block(r'''def test_simple():
        return "Hello world!"
    ''')
    py.eval('test_simple()')

    # test the call interface
    ret = py.call('test_simple')
    assert(str(ret) == "Hello world!")

    # call a built-in
    ret = py.eval('str("Hello world!")')
    assert(str(ret) == "Hello world!")

    # try 'callable'
    py_simple = py.callable('test_simple')
    ret = py_simple()
    assert(str(ret) == "Hello world!")


def test_call_stm():
    py = bond.make_bond('Python', timeout=TIMEOUT)

    # test the call interface with a normal function
    py.eval_block('from copy import copy')
    ret = py.call('copy', "Hello world!")
    assert(str(ret) == "Hello world!")

    # test the call interface with a module prefix
    py.eval_block("import copy")
    ret = py.call('copy.copy', "Hello world!")
    assert(str(ret) == "Hello world!")

    # now with a statement
    ret = py.call('lambda x: x', "Hello world!")
    assert(str(ret) == "Hello world!")


def test_call_error():
    py = bond.make_bond('Python', timeout=TIMEOUT)

    # define a function and call it
    py.eval_block(r'''def test_simple(arg):
        return arg
    ''')
    assert(py.call('test_simple', 1) == 1)

    # unknown function
    failed = False
    try:
        py.call('test_undefined')
    except bond.RemoteException as e:
        print(e)
        failed = True
    assert(failed)

    # check that the environment is still alive
    assert(py.eval('1') == 1)


def test_eval():
    py = bond.make_bond('Python', timeout=TIMEOUT)
    assert(py.eval('None') is None)
    assert(py.eval('1') == 1)

    # define a variable
    py.eval_block('x = 1')
    assert(py.eval('x') == 1)

    # define a function
    py.eval_block(r'''def test_bond(arg):
        return arg + 1
    ''')
    assert(py.eval('test_bond(0)') == 1)


def test_eval_sentinel():
    py = bond.make_bond('Python', timeout=TIMEOUT)

    # ensure the sentinel is not accessible
    failed = False
    try:
        py.eval('SENTINEL')
    except bond.RemoteException as e:
        print(e)
        failed = True
    assert(failed)


def test_eval_rec():
    py = bond.make_bond('Python', timeout=TIMEOUT)

    # in a recursive call, we should still be able to see our global scope
    def call_me():
        assert(py.eval('should_exist') == 1)

        failed = False
        try:
            py.eval('should_not_exist')
        except bond.RemoteException as e:
            print(e)
            failed = True
        assert(failed)

    py.export(call_me)
    py.eval_block('should_exist = 1')
    assert(py.eval('should_exist') == 1)
    py.call('call_me')


def test_eval_error():
    py = bond.make_bond('Python', timeout=TIMEOUT)

    # try a correct statement before
    assert(py.eval('1') == 1)

    # broken statement
    failed = False
    try:
        py.eval('"')
    except bond.RemoteException as e:
        print(e)
        failed = True
    assert(failed)

    # check that the environment is still alive
    assert(py.eval('1') == 1)


def _test_ser_err(py):
    # construct an unserializable type
    py.eval_block(r'''if True:
    import os

    x = lambda x: x

    def func():
        return x
    ''')

    # test the call interface with a normal function
    failed = False
    try:
        ret = py.eval('x')
    except bond.SerializationException as e:
        print(e)
        failed = (e.side == "remote")
    assert(failed)

    # ensure the env didn't just die
    assert(py.eval('1') == 1)

    # ... with call (return)
    failed = False
    try:
        py.call('func')
    except bond.SerializationException as e:
        print(e)
        failed = (e.side == "remote")
    assert(failed)

    # ensure the env didn't just die
    assert(py.eval('1') == 1)

    # ... with an exception
    failed = False
    try:
        py.eval_block('raise Exception(x)')
    except bond.SerializationException as e:
        print(e)
        failed = (e.side == "remote")
    assert(failed)

    # ensure the env didn't just die
    assert(py.eval('1') == 1)

def test_ser_err_native():
    py = bond.make_bond('Python', timeout=TIMEOUT)
    _test_ser_err(py)

def test_ser_err_baseline():
    py = bond.make_bond('Python', trans_except=True, protocol='JSON', timeout=TIMEOUT)
    _test_ser_err(py)


def test_exception():
    py = bond.make_bond('Python', timeout=TIMEOUT)

    # remote exception
    py.eval_block(r'''def exceptional():
    raise Exception('an exception')
    ''')

    # ... in eval
    failed = False
    try:
        py.eval('exceptional()')
    except bond.RemoteException as e:
        print(e)
        failed = True
    assert(failed)

    # ... in eval_block
    failed = False
    try:
        py.eval_block('exceptional()')
    except bond.RemoteException as e:
        print(e)
        failed = True
    assert(failed)

    # ... in call
    failed = False
    try:
        py.call('exceptional')
    except bond.RemoteException as e:
        print(e)
        failed = True
    assert(failed)


def test_export():
    def call_me():
        return 42

    py = bond.make_bond('Python', timeout=TIMEOUT)
    py.export(call_me, 'call_me')
    assert(py.call('call_me') == 42)


def test_export_redef():
    py = bond.make_bond('Python', timeout=TIMEOUT)

    def call_me():
        return 42

    py.export(call_me)
    try:
        py.export(call_me)
    except:
        pass

    assert(py.call('call_me') == 42)


def test_export_invalid():
    py = bond.make_bond('Python', timeout=TIMEOUT)

    def call_me():
        return 42

    try:
        # Interestingly enough, this works in Python, though it won't be
        # possible to call the function normally
        py.export(call_me, 'invalid name')
    except Exception as e:
        print(e)

    assert(py.eval('1') == 1)


def test_export_recursive():
    py = bond.make_bond('Python', timeout=TIMEOUT)

    # define a remote function
    py.eval_block(r'''def func_remote(arg):
        return arg + 1
    ''')
    func_remote = py.callable('func_remote')
    assert(func_remote(0) == 1)

    # define a local function that calls the remote
    def func_local(arg):
        return func_remote(arg + 1)

    assert(func_local(0) == 2)

    # export the function remotely and call it
    py.export(func_local, 'exported_func_local')
    exported_func_local = py.callable('exported_func_local')
    assert(exported_func_local(0) == 2)

    # define a remote function that calls us recursively
    py.eval_block(r'''def func_remote_rec(arg):
        return exported_func_local(arg) + 1
    ''')
    assert(py.eval('func_remote_rec(0)')) == 3
    assert(py.call('func_remote_rec', 0)) == 3

    func_remote_rec = py.callable('func_remote_rec')
    assert(func_remote_rec(0) == 3)

    # inception
    def func_local_rec(arg):
       return func_remote_rec(arg) + 1

    py.export(func_local_rec, 'exported_func_local_rec')
    py.eval_block(r'''def func_remote_rec_2(arg):
        return exported_func_local_rec(arg) + 1
    ''')
    func_remote_rec_2 = py.callable('func_remote_rec_2')
    assert(func_remote_rec_2(0) == 5)


def test_export_ser_err():
    def call_me(arg):
        pass

    py = bond.make_bond('Python', timeout=TIMEOUT)
    py.export(call_me, 'call_me')

    failed = False
    try:
        py.eval('call_me(lambda x: x)')
    except bond.SerializationException as e:
        print(e)
        failed = (e.side == "remote")
    assert(failed)

    # ensure the env didn't just die
    assert(py.eval('1') == 1)


def test_export_except():
    py = bond.make_bond('Python', timeout=TIMEOUT)

    def gen_exception():
        raise Exception("test")

    py.export(gen_exception)
    py.eval_block(r'''def test_exception():
    ret = False
    try:
        gen_exception()
    except Exception as e:
        print(e)
        ret = (str(e) == "test")
    return ret
    ''')

    assert(py.call('test_exception') == True)


def test_export_except_ser_err():
    py = bond.make_bond('Python', timeout=TIMEOUT)

    def call_me():
        return lambda x: x

    py.export(call_me)
    py.eval_block(r'''def test_ser_err():
    ret = False
    try:
        call_me()
    except Exception as e:
        print(e)
        ret = True
    return ret
    ''')

    assert(py.call('test_ser_err') == True)


def test_output_redirect():
    capture = OutputCapture()

    # stdout
    with capture:
        py = bond.make_bond('Python', timeout=TIMEOUT)
        py.eval_block(r'import sys')
        py.eval_block(r'sys.stdout.write("Hello world!\n")')
        assert(py.eval('1') == 1)
    ret = capture.stdout
    assert(str(ret) == "Hello world!\n")

    # stderr
    with capture:
        py = bond.make_bond('Python', timeout=TIMEOUT)
        py.eval_block(r'import sys')
        py.eval_block(r'sys.stderr.write("Hello world!\n")')
        assert(py.eval('1') == 1)
    ret = capture.stderr
    assert(str(ret) == "Hello world!\n")


def test_trans_except():
    py_trans = bond.make_bond('Python', timeout=TIMEOUT, trans_except=True)
    py_not_trans = bond.make_bond('Python', timeout=TIMEOUT, trans_except=False)

    code = r'''def func():
        raise RuntimeError("a runtime error")
    '''

    # by default exceptions are transparent, so the following should correctly
    # restore the RuntimeError in RemoteException.data
    py_trans.eval_block(code)
    failed = False
    try:
        ret = py_trans.call('func')
    except bond.RemoteException as e:
        failed = isinstance(e.data, RuntimeError)
    assert(failed)

    # ensure the env didn't just die
    assert(py_trans.eval('1') == 1)

    # this one though will just always forward the remote exception
    py_not_trans.eval_block(code)
    failed = False
    try:
        ret = py_not_trans.call('func')
    except bond.RemoteException as e:
        failed = isinstance(e.data, str)
    assert(failed)

    # ensure the env didn't just die
    assert(py_not_trans.eval('1') == 1)


def test_export_trans_except():
    py_trans = bond.make_bond('Python', timeout=TIMEOUT, trans_except=True)
    py_not_trans = bond.make_bond('Python', timeout=TIMEOUT, trans_except=False)

    def call_me():
       raise RuntimeError("a runtime error")

    # by default exceptions are transparent, so the following should correctly
    # restore the RuntimeError in RemoteException.data
    py_trans.export(call_me)
    py_trans.eval_block(r'''if True:
    failed = False
    try:
        call_me()
    except RuntimeError:
        failed = True
    ''')
    assert(py_trans.eval('failed') == True)

    # this one though will just generate a general Exception
    py_not_trans.export(call_me)
    py_not_trans.eval_block(r'''if True:
    failed = False
    try:
        call_me()
    except Exception as e:
        failed = not isinstance(e, RuntimeError)
    ''')
    assert(py_not_trans.eval('failed') == True)


def test_stack_depth():
    def no_exception():
        pass

    def gen_exception():
        raise Exception("test")

    def gen_ser_err():
        return lambda x: x

    # check normal stack depth
    py = bond.make_bond('Python', timeout=TIMEOUT)
    assert(bond_repl_depth(py) == 1)

    # check stack depth after calling a normal function
    py = bond.make_bond('Python', timeout=TIMEOUT)
    py.export(no_exception)
    py.call('no_exception')
    assert(bond_repl_depth(py) == 1)

    # check stack depth after returning a serializable exception
    py = bond.make_bond('Python', timeout=TIMEOUT)
    py.export(gen_exception)
    got_except = False
    try:
        py.call('gen_exception')
    except bond.RemoteException as e:
        print(e)
        got_except = True
    assert(got_except)
    assert(bond_repl_depth(py) == 1)

    # check stack depth after a remote serialization error
    py = bond.make_bond('Python', timeout=TIMEOUT)
    py.export(gen_ser_err)
    got_except = False
    try:
        py.call('gen_ser_err')
    except bond.SerializationException as e:
        print(e)
        assert(e.side == "remote")
        got_except = True
    assert(got_except)
    assert(bond_repl_depth(py) == 1)


def _test_buf_size(py):
    for size in [2 ** n for n in range(9, 16)]:
        print("testing buffer >= {} bytes".format(size))
        buf = "x" * size
        ret = py.call('str', buf)
        assert(ret == str(ret))

def test_buf_size():
    py = bond.make_bond('Python', timeout=TIMEOUT)
    _test_buf_size(py)

def test_buf_size_rmt():
    py = bond.make_bond('Python', "ssh localhost python", timeout=TIMEOUT)
    _test_buf_size(py)
