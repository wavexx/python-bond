from __future__ import print_function
from bond.PHP import PHP

def test_basic():
    php = PHP(timeout=1)
    php.close()


def test_call():
    php = PHP(timeout=1)
    ret = php.call('sprintf', "Hello world!")
    assert(str(ret) == "Hello world!")


def test_call_marshalling():
    php = PHP(timeout=1)

    php.eval(r'function test_str() { return "Hello world!"; }')
    assert(str(php.call('test_str')) == "Hello world!")

    php.eval(r'function test_array() { return [42]; }')
    assert(php.call('test_array') == [42])

    php.eval(r'function test_number() { return 42; }')
    assert(php.call('test_number') == 42)

    php.eval(r'function test_bool() { return false; }')
    assert(php.call('test_bool') is False)

    php.eval(r'function test_nothing() { return null; }')
    assert(php.call('test_nothing') is None)

    php.eval(r'function test_identity($arg) { return $arg; }')
    php_identity = php.callable('test_identity')
    for value in [True, False, 0, 1, "String", [], [u"String"]]:
        ret = php_identity(value)
        print("{} => {}".format(value, ret))
        assert(str(ret) == str(value))

    php.eval(r'function test_multi_arg($arg1, $arg2) { return sprintf("%s %s", $arg1, $arg2); }')
    assert(str(php.call('test_multi_arg', "Hello", "world!")) == "Hello world!")

    php.eval(r'function test_nested($arg) { return test_identity($arg); }')
    php_nested = php.callable('test_nested')
    for value in [True, False, 0, 1, "String", [], [u"String"]]:
        ret = php_nested(value)
        print("{} => {}".format(value, ret))
        assert(str(ret) == str(value))


def test_call_simple():
    php = PHP(timeout=1)
    php_print = php.callable('sprintf')
    ret = php_print("Hello world!")
    assert(str(ret) == "Hello world!")


def test_eval():
    php = PHP(timeout=1)
    assert(php.eval_block('1;') is None)
    assert(php.eval_block('return 1;') == 1)

    php.eval('function test_php($arg) { return $arg + 1; }')
    assert(php.eval('return test_php(0);') == 1)
    assert(php.eval_block('return test_php(0);') == 1)


def test_eval_block():
    php = PHP(timeout=1)

    # ensure eval/eval_block work first
    assert(php.eval('return 1;') == 1)
    assert(php.eval_block('return 1;') == 1)

    # check eval
    php.eval('$x = 1;')
    assert(php.eval('return $x;') == 1)

    # check eval_block
    php.eval_block('$y = 1;')
    assert(php.eval_block('return isset($y)? $y: -1;') == -1)


def test_export():
    def call_me():
        return 42

    php = PHP(timeout=1)
    php.export(call_me, 'call_me')
    assert(php.call('call_me') == 42)


def test_export_recursive():
    php = PHP(timeout=1)

    # define a remote function
    php.eval(r'function func_php($arg) { return $arg + 1; }')
    func_php = php.callable('func_php')
    assert(func_php(0) == 1)

    # define a local function that calls the remote
    def func_python(arg):
        return func_php(arg + 1)

    assert(func_python(0) == 2)

    # export the function remotely and call it
    php.export(func_python, 'remote_func_python')
    remote_func_python = php.callable('remote_func_python')
    assert(remote_func_python(0) == 2)

    # define a remote function that calls us recursively
    php.eval(r'function func_php_rec($arg) { return remote_func_python($arg) + 1; }')
    func_php_rec = php.callable('func_php_rec')
    assert(func_php_rec(0) == 3)

    # inception
    def func_python_rec(arg):
        return func_php_rec(arg) + 1

    php.export(func_python_rec, 'remote_func_python_rec')
    php.eval(r'function func_php_rec_2($arg) { return remote_func_python_rec($arg) + 1; }')
    func_php_rec_2 = php.callable('func_php_rec_2')
    assert(func_php_rec_2(0) == 5)


def test_output_redirect():
    php = PHP(timeout=1)
    php.eval_block(r'echo "Hello world!\n";')


def test_proxy():
    php1 = PHP(timeout=1)
    php1.eval(r'function func_php1($arg) { return $arg + 1; }')

    php2 = PHP(timeout=1)
    php1.proxy('func_php1', php2)

    assert(php2.call('func_php1', 0) == 1)
