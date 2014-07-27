from __future__ import print_function
import bond
from bond.Python import Python

def test_basic():
    py = Python(timeout=1)
    py.close()


def test_call_marshalling():
    py = Python(timeout=1)

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


def test_call_simple():
    py = Python(timeout=1)

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


def test_call_error():
    py = Python(timeout=1)

    # define a function and call it
    py.eval_block(r'''def test_simple(arg):
        return 1 / arg
    ''')
    py.eval('test_simple(1)')

    # make it fail
    fail = False
    try:
        py.call('test_simple', 0)
    except bond.RemoteException as e:
        print(e)
        failed = True
    assert(failed)


def test_eval():
    py = Python(timeout=1)
    assert(py.eval('None') is None)
    assert(py.eval('1') == 1)

    # define a variable
    py.eval_block('x = 1')
    assert(py.eval('x') == 1)

    # define a function
    py.eval_block(r'''def test_python(arg):
        return arg + 1
    ''')
    assert(py.eval('test_python(0)') == 1)


def test_eval_error():
    py = Python(timeout=1)

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


# def test_export():
#     def call_me():
#         return 42

#     py = Python(timeout=1)
#     py.export(call_me, 'call_me')
#     assert(py.call('call_me') == 42)


# def test_export_recursive():
#     py = Python(timeout=1)

#     # define a remote function
#     py.eval(r'sub func_perl { shift() + 1; }')
#     func_py = py.callable('func_perl')
#     assert(func_perl(0) == 1)

#     # define a local function that calls the remote
#     def func_python(arg):
#         return func_perl(arg + 1)

#     assert(func_python(0) == 2)

#     # export the function remotely and call it
#     py.export(func_python, 'remote_func_python')
#     remote_func_python = py.callable('remote_func_python')
#     assert(remote_func_python(0) == 2)

#     # define a remote function that calls us recursively
#     py.eval(r'sub func_perl_rec { remote_func_python(shift()) + 1; }')
#     func_perl_rec = py.callable('func_perl_rec')
#     assert(func_perl_rec(0) == 3)

#     # inception
#     def func_python_rec(arg):
#         return func_perl_rec(arg) + 1

#     py.export(func_python_rec, 'remote_func_python_rec')
#     py.eval(r'sub func_perl_rec_2 { remote_func_python_rec(shift()) + 1; }')
#     func_perl_rec_2 = py.callable('func_perl_rec_2')
#     assert(func_perl_rec_2(0) == 5)


def test_output_redirect():
    py = Python(timeout=1)
    py.eval_block(r'print "Hello world!\n"')


# def test_proxy():
#     py1 = Python(timeout=1)
#     py1.eval(r'sub func_perl1 { shift() + 1; }')

#     py2 = Python(timeout=1)
#     py1.proxy('func_perl1', perl2)

#     assert(perl2.call('func_perl1', 0) == 1)
