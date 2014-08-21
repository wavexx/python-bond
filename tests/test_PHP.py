from __future__ import print_function
import bond
from tests import *

def test_basic():
    php = bond.make_bond('PHP', timeout=TIMEOUT)
    php.close()


def test_basic_rmt():
    php = bond.make_bond('PHP', "ssh localhost php", timeout=TIMEOUT)
    php.close()


def test_call_marshalling():
    php = bond.make_bond('PHP', timeout=TIMEOUT)

    php.eval_block(r'function test_str() { return "Hello world!"; }')
    assert(str(php.call('test_str')) == "Hello world!")

    php.eval_block(r'function test_array() { return array(42); }')
    assert(php.call('test_array') == [42])

    php.eval_block(r'function test_number() { return 42; }')
    assert(php.call('test_number') == 42)

    php.eval_block(r'function test_bool() { return false; }')
    assert(php.call('test_bool') is False)

    php.eval_block(r'function test_nothing() { return null; }')
    assert(php.call('test_nothing') is None)

    php.eval_block(r'function test_identity($arg) { return $arg; }')
    php_identity = php.callable('test_identity')
    for value in [True, False, 0, 1, "String", [], [u"String"]]:
        ret = php_identity(value)
        print("{} => {}".format(value, ret))
        assert(str(ret) == str(value))

    php.eval_block(r'function test_multi_arg($arg1, $arg2) { return sprintf("%s %s", $arg1, $arg2); }')
    assert(str(php.call('test_multi_arg', "Hello", "world!")) == "Hello world!")

    php.eval_block(r'function test_nested($arg) { return test_identity($arg); }')
    php_nested = php.callable('test_nested')
    for value in [True, False, 0, 1, "String", [], [u"String"]]:
        ret = php_nested(value)
        print("{} => {}".format(value, ret))
        assert(str(ret) == str(value))


def test_call_simple():
    php = bond.make_bond('PHP', timeout=TIMEOUT)
    php_print = php.callable('sprintf')
    ret = php_print("Hello world!")
    assert(str(ret) == "Hello world!")


def test_call_stm():
    php = bond.make_bond('PHP', timeout=TIMEOUT)

    # call a function reference
    php.eval_block('$fun = function($arg){ return $arg; };')
    ret = php.call('$fun', "Hello world!")
    assert(str(ret) == "Hello world!")

    # call a method
    php.eval_block(r'''
    class Test
    {
        public function call_me($arg)
        {
            return $arg;
        }
    }
    $obj = new Test();
    ''')
    ret = php.call('$obj->call_me', 1)
    assert(ret == 1)


def test_ser_err():
    php = bond.make_bond('PHP', timeout=TIMEOUT)

    # construct an unserializable type
    php.eval_block(r'''
    $fd = fopen("php://stdout", "w");
    function func()
    {
        return fopen("php://stdout", "w");
    }
    ''')

    # try to send it across
    failed = False
    try:
        php.eval('$fd')
    except bond.SerializationException as e:
        print(e)
        failed = (e.side == "remote")
    assert(failed)

    # ensure the env didn't just die
    assert(php.eval('1') == 1)

    # ... with call (return)
    failed = False
    try:
        php.call('func')
    except bond.SerializationException as e:
        print(e)
        failed = (e.side == "remote")
    assert(failed)

    # ensure the env didn't just die
    assert(php.eval('1') == 1)


def test_call_error():
    php = bond.make_bond('PHP', timeout=TIMEOUT)

    # test a regular working function
    php.eval_block('function test_simple($arg) { return 1 / $arg; }')
    ret = php.call('test_simple', 1)
    assert(ret == 1)

    # make it fail
    failed = False
    try:
        php.call('no_test_simple', 0)
    except bond.RemoteException as e:
        print(e)
        failed = True
    assert(failed)


@knownfail
def test_fatal_error():
    php = bond.make_bond('PHP', timeout=TIMEOUT)

    failed = True
    try:
        # We test for a RemoteException. If the bond dies without handling the
        # exception correctly you'll get a pexpect.TIMEOUT instead.
        php.eval_block('no_test_simple();')
    except bond.RemoteException as e:
        print(e)
        failed = True
    assert(failed)


def test_eval():
    php = bond.make_bond('PHP', timeout=TIMEOUT)

    # check the distrinction
    assert(php.eval_block('1;') is None)
    assert(php.eval('1') == 1)

    # check a function definition
    php.eval_block('function test_php($arg) { return $arg + 1; }')
    assert(php.eval('test_php(0)') == 1)

    # check a variable definition
    php.eval_block('$x = 1;')
    assert(php.eval('$x') == 1)

    # unset a variable to stress our simulated global scope
    php.eval_block('unset($x);')
    assert(php.eval('!isset($x)') == 1)


def test_eval_sentinel():
    php = bond.make_bond('PHP', timeout=TIMEOUT)

    # ensure the sentinel is not accessible
    ret = php.eval('$SENTINEL')
    assert(ret != 1)


def test_eval_rec():
    php = bond.make_bond('PHP', timeout=TIMEOUT)

    # in a recursive call, we should still be able to see our global scope
    def call_me():
        assert(php.eval('$should_exist') == 1)
        assert(php.eval('!isset($should_not_exist)'))

    php.export(call_me)
    php.eval_block('$should_exist = 1;')
    assert(php.eval('$should_exist') == 1)
    php.call('call_me')


def test_eval_error():
    php = bond.make_bond('PHP', timeout=TIMEOUT)

    # try a correct statement before
    assert(php.eval('1') == 1)

    # broken statement
    failed = False
    try:
        php.eval('"')
    except bond.RemoteException as e:
        print(e)
        failed = True
    assert(failed)

    # check that the environment is still alive
    assert(php.eval('1') == 1)

    # broken eval_block
    failed = False
    try:
        php.eval_block('"')
    except bond.RemoteException as e:
        print(e)
        failed = True
    assert(failed)

    # check that the environment is still alive
    assert(php.eval('1') == 1)


def test_exception():
    php = bond.make_bond('PHP', timeout=TIMEOUT)

    # local exception
    php.eval_block('function exceptional() { throw new Exception("exception"); }')

    # ... in eval
    failed = False
    try:
        php.eval('exceptional()')
    except bond.RemoteException as e:
        print(e)
        failed = True
    assert(failed)

    # check that the environment is still alive
    assert(php.eval('1') == 1)

    # ... in eval_block
    failed = False
    try:
        php.eval_block('exceptional();')
    except bond.RemoteException as e:
        print(e)
        failed = True
    assert(failed)

    # check that the environment is still alive
    assert(php.eval('1') == 1)

    # ... in call
    failed = False
    try:
        php.call('exceptional')
    except bond.RemoteException as e:
        print(e)
        failed = True
    assert(failed)

    # check that the environment is still alive
    assert(php.eval('1') == 1)


def test_export():
    def call_me():
        return 42

    php = bond.make_bond('PHP', timeout=TIMEOUT)
    php.export(call_me, 'call_me')
    assert(php.call('call_me') == 42)


def test_export_redef():
    php = bond.make_bond('PHP', timeout=TIMEOUT)

    def call_me():
        return 42

    php.export(call_me)
    try:
        php.export(call_me)
    except:
        pass

    assert(php.call('call_me') == 42)


def test_export_invalid():
    php = bond.make_bond('PHP', timeout=TIMEOUT)

    def call_me():
        return 42

    try:
        php.export(call_me, 'invalid name')
    except Exception as e:
        print(e)

    assert(php.eval('1') == 1)


def test_export_recursive():
    php = bond.make_bond('PHP', timeout=TIMEOUT)

    # define a remote function
    php.eval_block(r'function func_php($arg) { return $arg + 1; }')
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
    php.eval_block(r'function func_php_rec($arg) { return remote_func_python($arg) + 1; }')
    func_php_rec = php.callable('func_php_rec')
    assert(func_php_rec(0) == 3)

    # inception
    def func_python_rec(arg):
        return func_php_rec(arg) + 1

    php.export(func_python_rec, 'remote_func_python_rec')
    php.eval_block(r'function func_php_rec_2($arg) { return remote_func_python_rec($arg) + 1; }')
    func_php_rec_2 = php.callable('func_php_rec_2')
    assert(func_php_rec_2(0) == 5)


def test_export_ser_err():
    def call_me(arg):
        pass

    php = bond.make_bond('PHP', timeout=TIMEOUT)
    php.export(call_me, 'call_me')
    php.eval_block('$fd = fopen("php://stdout", "w");')

    failed = False
    try:
        php.eval('call_me($fd)')
    except bond.SerializationException as e:
        print(e)
        failed = (e.side == "remote")
    assert(failed)

    # ensure the env didn't just die
    assert(php.eval('1') == 1)


def test_export_except():
    php = bond.make_bond('PHP', timeout=TIMEOUT)

    def gen_exception():
        raise Exception("test")

    php.export(gen_exception)
    php.eval_block(r'''
    function test_exception()
    {
        $ret = 0;
        try { gen_exception(); }
        catch(Exception $e) { $ret = 1; }
        return $ret;
    }''')

    assert(php.call('test_exception') == True)


def test_output_redirect():
    capture = OutputCapture()

    # standard output (echo)
    with capture:
        php = bond.make_bond('PHP', timeout=TIMEOUT)
        php.eval_block(r'echo "Hello world!\n";')
        assert(php.eval('1') == 1)
    ret = capture.stdout
    assert(str(ret) == "Hello world!\n")

    # standard output (STDOUT)
    with capture:
        php = bond.make_bond('PHP', timeout=TIMEOUT)
        php.eval_block(r'fwrite(STDOUT, "Hello world!\n");')
        assert(php.eval('1') == 1)
    ret = capture.stdout
    assert(str(ret) == "Hello world!\n")

    # standard output (php://stdout)
    with capture:
        php = bond.make_bond('PHP', timeout=TIMEOUT)
        php.eval_block(r'file_put_contents("php://stdout", "Hello world!\n");')
        assert(php.eval('1') == 1)
    ret = capture.stdout
    assert(str(ret) == "Hello world!\n")

    # standard error (STDERR)
    with capture:
        php = bond.make_bond('PHP', timeout=TIMEOUT)
        php.eval_block(r'fwrite(STDERR, "Hello world!\n");')
        assert(php.eval('1') == 1)
    ret = capture.stderr
    assert(str(ret) == "Hello world!\n")

    # standard error (php://stderr)
    with capture:
        php = bond.make_bond('PHP', timeout=TIMEOUT)
        php.eval_block(r'file_put_contents("php://stderr", "Hello world!\n");')
        assert(php.eval('1') == 1)
    ret = capture.stderr
    assert(str(ret) == "Hello world!\n")

    # error reporting (on)
    with capture:
        php = bond.make_bond('PHP', timeout=TIMEOUT)
        php.eval_block(r'ini_set("display_errors", "1");')
        php.eval_block(r'trigger_error("Hello world!");')
        assert(php.eval('1') == 1)
    ret = capture.stderr
    assert(str(ret).find("Hello world!") >= 0)

    # error reporting (off)
    with capture:
        php = bond.make_bond('PHP', timeout=TIMEOUT)
        php.eval_block(r'ini_set("display_errors", "0");')
        php.eval_block(r'trigger_error("Hello world!");')
        assert(php.eval('1') == 1)
    ret = capture.stderr
    assert(str(ret).find("Hello world!") < 0)


def test_BOND_error_reporting():
    php = bond.make_bond('PHP', timeout=TIMEOUT)

    # test that the default reporting level is non-zero
    ret = php.call('_BOND_error_reporting')
    assert(ret)

    # ensure changes are maintained
    ret = php.call('_BOND_error_reporting', 22527)
    ret = php.call('_BOND_error_reporting')
    assert(ret == 22527)


@knownfail
def test_error_reporting_default():
    php = bond.make_bond('PHP', timeout=TIMEOUT)

    # test that the default reporting level is non-zero
    ret = php.call('error_reporting')
    assert(ret)


@knownfail
def test_error_reporting_noise():
    php = bond.make_bond('PHP', timeout=TIMEOUT)

    # ensure no noise is generated in the I/O stream, ever
    try:
        php.eval_block('error_reporting(E_ALL); echo $undefined;')
    except bond.RemoteException as e:
        print(e)
        pass
    assert(php.eval('1') == 1)


def test_trans_except():
    php_trans = bond.make_bond('PHP', timeout=TIMEOUT, trans_except=True)
    php_not_trans = bond.make_bond('PHP', timeout=TIMEOUT, trans_except=False)

    code = r'''
    if(PHP_VERSION_ID >= 50400)
    {
        class MyException extends Exception implements jsonSerializable
        {
            public function jsonSerialize()
            {
                return "MyException";
            }
        }

        function func()
        {
            throw new MyException("an exception");
        }
    }
    else
    {
        function func()
        {
            throw new Exception("an exception");
        }
    }
    '''

    # with transparent exceptions the following should try to serialize the
    # code block and call our jsonSerialize method
    php_trans.eval_block(code)
    failed = False
    try:
        ret = php_trans.call('func')
    except bond.RemoteException as e:
        print(e)
        failed = (str(e.data) == "MyException" or str(e.data) == "{}")
    assert(failed)

    # ensure the env didn't just die
    assert(php_trans.eval('1') == 1)

    # this one though will just forward the text
    php_not_trans.eval_block(code)
    failed = False
    try:
        ret = php_not_trans.call('func')
    except bond.RemoteException as e:
        print(e)
        failed = (str(e.data) == "an exception")
    assert(failed)

    # ensure the env didn't just die
    assert(php_not_trans.eval('1') == 1)


def test_export_trans_except():
    php_trans = bond.make_bond('PHP', timeout=TIMEOUT, trans_except=True)
    php_not_trans = bond.make_bond('PHP', timeout=TIMEOUT, trans_except=False)

    def call_me():
       raise RuntimeError("a runtime error")

    # by default exceptions are transparent, so the following should try to
    # serialize RuntimeError in JSON (and fail)
    php_trans.export(call_me)
    php_trans.eval_block(r'''
    function test_exception()
    {
        $ret = false;
        try { call_me(); }
        catch(Exception $e)
        {
          $ret = (strstr($e->getMessage(), "SerializationException") !== false);
        }
        return $ret;
    }
    ''')
    assert(php_trans.call('test_exception') == True)

    # this one though will just generate a string
    php_not_trans.export(call_me)
    php_not_trans.eval_block(r'''
    function test_exception()
    {
        $ret = false;
        try { call_me(); }
        catch(Exception $e)
        {
          $ret = ($e->getMessage() == "a runtime error");
        }
        return $ret;
    }
    ''')
    assert(php_not_trans.call('test_exception') == True)


def test_stack_depth():
    def no_exception():
        pass

    def gen_exception():
        raise Exception("test")

    def gen_ser_err():
        return lambda x: x

    # check normal stack depth
    php = bond.make_bond('PHP', timeout=TIMEOUT)
    assert(bond_repl_depth(php) == 1)

    # check stack depth after calling a normal function
    php = bond.make_bond('PHP', timeout=TIMEOUT)
    php.export(no_exception)
    php.call('no_exception')
    assert(bond_repl_depth(php) == 1)

    # check stack depth after returning a serializable exception
    php = bond.make_bond('PHP', timeout=TIMEOUT)
    php.export(gen_exception)
    got_except = False
    try:
        php.call('gen_exception')
    except bond.RemoteException as e:
        print(e)
        got_except = True
    assert(got_except)
    assert(bond_repl_depth(php) == 1)

    # check stack depth after a remote serialization error
    php = bond.make_bond('PHP', timeout=TIMEOUT)
    php.export(gen_ser_err)
    got_except = False
    try:
        php.call('gen_ser_err')
    except bond.SerializationException as e:
        print(e)
        assert(e.side == "remote")
        got_except = True
    assert(got_except)
    assert(bond_repl_depth(php) == 1)


def _test_buf_size(php):
    php.eval_block('function id($arg) { return $arg; }')

    for size in [2 ** n for n in range(9, 16)]:
        print("testing buffer >= {} bytes".format(size))
        buf = "x" * size
        ret = php.call('id', buf)
        assert(ret == str(ret))

def test_buf_size():
    php = bond.make_bond('PHP', timeout=TIMEOUT)
    _test_buf_size(php)

def test_buf_size_rmt():
    php = bond.make_bond('PHP', "ssh localhost php", timeout=TIMEOUT)
    _test_buf_size(php)
