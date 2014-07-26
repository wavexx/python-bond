from __future__ import print_function
import bond
from bond.Perl import Perl

def test_basic():
    perl = Perl(timeout=1)
    perl.close()


## def test_call():
##     perl = Perl(timeout=1)
##     ret = perl.call('sprintf', "Hello world!")
##     assert(str(ret) == "Hello world!")


## def test_call_marshalling():
##     perl = Perl(timeout=1)

##     perl.eval(r'function test_str() { return "Hello world!"; }')
##     assert(str(perl.call('test_str')) == "Hello world!")

##     perl.eval(r'function test_array() { return [42]; }')
##     assert(perl.call('test_array') == [42])

##     perl.eval(r'function test_number() { return 42; }')
##     assert(perl.call('test_number') == 42)

##     perl.eval(r'function test_bool() { return false; }')
##     assert(perl.call('test_bool') is False)

##     perl.eval(r'function test_nothing() { return null; }')
##     assert(perl.call('test_nothing') is None)

##     perl.eval(r'function test_identity($arg) { return $arg; }')
##     perl_identity = perl.callable('test_identity')
##     for value in [True, False, 0, 1, "String", [], [u"String"]]:
##         ret = perl_identity(value)
##         print("{} => {}".format(value, ret))
##         assert(str(ret) == str(value))

##     perl.eval(r'function test_multi_arg($arg1, $arg2) { return sprintf("%s %s", $arg1, $arg2); }')
##     assert(str(perl.call('test_multi_arg', "Hello", "world!")) == "Hello world!")

##     perl.eval(r'function test_nested($arg) { return test_identity($arg); }')
##     perl_nested = perl.callable('test_nested')
##     for value in [True, False, 0, 1, "String", [], [u"String"]]:
##         ret = perl_nested(value)
##         print("{} => {}".format(value, ret))
##         assert(str(ret) == str(value))


def test_call_simple():
    perl = Perl(timeout=1)
    perl.eval('sub test_perl() { return "Hello world!"; }')
    perl_func = perl.callable('test_perl')
    ret = perl_func();
    assert(str(ret) == "Hello world!")


def test_call_builtin():
    perl = Perl(timeout=1)

    # NOTE: sprintf is a built-in, and thus more compliated to call with
    #       the same semantics
    perl_sprintf = perl.callable('sprintf')
    ret = perl_sprintf("Hello world!")
    assert(str(ret) == "Hello world!")

    # no exception should be thrown here
    perl.call('print', 'Hellow world!')


def test_eval():
    perl = Perl(timeout=1)
    assert(perl.eval_block('undef;') is None)
    assert(perl.eval_block('1;') == 1)

    perl.eval('sub test_perl { shift() + 1; }')
    assert(perl.eval('test_perl(0);') == 1)
    assert(perl.eval_block('return test_perl(0);') == 1)


def test_eval_error():
    perl = Perl(timeout=1)

    # try a correct statement before
    assert(perl.eval('1;') == 1)

    # broken statement
    failed = False
    try:
        perl.eval_block('"')
    except bond.RemoteException as e:
        print(e)
        failed = True
    assert(failed)

    # check that the environment is still alive
    assert(perl.eval('1;') == 1)


def test_eval_block():
    perl = Perl(timeout=1)

    # ensure eval/eval_block work first
    assert(perl.eval('1;') == 1)
    assert(perl.eval_block('1;') == 1)

    # check eval with unscoped variables
    perl.eval('$x = 1;')
    assert(perl.eval('$x;') == 1)

    # eval/eval_block in Perl are *both* scoped
    perl.eval('my $y = 1;')
    assert(perl.eval('$y // -1') == -1)

    perl.eval_block('my $y = 1;')
    assert(perl.eval_block('$y // -1') == -1)


## def test_export():
##     def call_me():
##         return 42

##     perl = Perl(timeout=1)
##     perl.export(call_me, 'call_me')
##     assert(perl.call('call_me') == 42)


## def test_export_recursive():
##     perl = Perl(timeout=1)

##     # define a remote function
##     perl.eval(r'function func_perl($arg) { return $arg + 1; }')
##     func_perl = perl.callable('func_perl')
##     assert(func_perl(0) == 1)

##     # define a local function that calls the remote
##     def func_python(arg):
##         return func_perl(arg + 1)

##     assert(func_python(0) == 2)

##     # export the function remotely and call it
##     perl.export(func_python, 'remote_func_python')
##     remote_func_python = perl.callable('remote_func_python')
##     assert(remote_func_python(0) == 2)

##     # define a remote function that calls us recursively
##     perl.eval(r'function func_perl_rec($arg) { return remote_func_python($arg) + 1; }')
##     func_perl_rec = perl.callable('func_perl_rec')
##     assert(func_perl_rec(0) == 3)

##     # inception
##     def func_python_rec(arg):
##         return func_perl_rec(arg) + 1

##     perl.export(func_python_rec, 'remote_func_python_rec')
##     perl.eval(r'function func_perl_rec_2($arg) { return remote_func_python_rec($arg) + 1; }')
##     func_perl_rec_2 = perl.callable('func_perl_rec_2')
##     assert(func_perl_rec_2(0) == 5)


def test_output_redirect():
    perl = Perl(timeout=1)
    perl.eval_block(r'print "Hello world!\n";')


## def test_proxy():
##     perl1 = Perl(timeout=1)
##     perl1.eval(r'function func_perl1($arg) { return $arg + 1; }')

##     perl2 = Perl(timeout=1)
##     perl1.proxy('func_perl1', perl2)

##     assert(perl2.call('func_perl1', 0) == 1)
