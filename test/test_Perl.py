from __future__ import print_function
import bond
from bond.Perl import Perl

def test_basic():
    perl = Perl(timeout=1)
    perl.close()


def test_call_marshalling():
    perl = Perl(timeout=1)

    perl.eval(r'sub test_str { "Hello world!"; }')
    assert(str(perl.call('test_str')) == "Hello world!")

    perl.eval(r'sub test_array { [42]; }')
    assert(perl.call('test_array') == [42])

    perl.eval(r'sub test_number { 42; }')
    assert(perl.call('test_number') == 42)

    perl.eval(r'sub test_nothing { undef; }')
    assert(perl.call('test_nothing') is None)

    perl.eval(r'sub test_identity { shift(); }')
    perl_identity = perl.callable('test_identity')
    for value in [True, False, 0, 1, "String", [], [u"String"]]:
        ret = perl_identity(value)
        print("{} => {}".format(value, ret))
        assert(str(ret) == str(value))

    perl.eval(r'sub test_multi_arg { sprintf("%s %s", @_); }')
    assert(str(perl.call('test_multi_arg', "Hello", "world!")) == "Hello world!")

    perl.eval(r'sub test_nested { test_identity(shift()); }')
    perl_nested = perl.callable('test_nested')
    for value in [True, False, 0, 1, "String", [], [u"String"]]:
        ret = perl_nested(value)
        print("{} => {}".format(value, ret))
        assert(str(ret) == str(value))


def test_call_simple():
    perl = Perl(timeout=1)
    perl.eval('sub test_simple { "Hello world!"; }')
    perl_simple = perl.callable('test_simple')
    ret = perl_simple()
    assert(str(ret) == "Hello world!")

    perl.eval('sub test_proto() { "Hello world!"; }')
    perl_proto = perl.callable('test_proto')
    ret = perl_proto()
    assert(str(ret) == "Hello world!")


def test_call_stm():
    perl = Perl(timeout=1)

    # test the call interface with a normal function
    perl.eval_block('sub copy { shift() }')
    ret = perl.call('copy', "Hello world!")
    assert(str(ret) == "Hello world!")

    # test the call interface with some random syntax
    ret = perl.call('&{ \&copy }', "Hello world!")
    assert(str(ret) == "Hello world!")

    # test calling a function bypassing the prototype
    ret = perl.call('&copy', "Hello world!")
    assert(str(ret) == "Hello world!")

    # check return values depending on the context
    ret = perl.call('scalar split', ' ', "Hello world!")
    assert(ret == 2)

    ret = perl.call('split', ' ', "Hello world!")
    assert(ret == ["Hello", "world!"])

    # try with some perl prototyped functions
    ret = perl.call('map { $_ }', "Hello world!")
    assert(str(ret) == "Hello world!")


def test_call_error():
    perl = Perl(timeout=1)
    perl.eval('sub test_simple { 1 / shift() }')
    ret = perl.call('test_simple', 1)
    assert(ret == 1)

    # make it fail
    failed = False
    try:
        perl.call('test_simple', 0)
    except bond.RemoteException as e:
        print(e)
        failed = True
    assert(failed)

    # check that the environment is still alive
    assert(perl.eval('1;') == 1)


def test_call_proto():
    perl = Perl(timeout=1)

    # without prototypes
    perl.eval('sub test_simple { "Hello world!"; }')
    perl_simple = perl.callable('test_simple')
    ret = perl_simple()
    assert(str(ret) == "Hello world!")
    ret = perl_simple(1)
    assert(str(ret) == "Hello world!")
    ret = perl_simple(1, 2)
    assert(str(ret) == "Hello world!")

    # with prototypes
    perl.eval('sub test_proto() { "Hello world!"; }')
    perl_proto = perl.callable('test_proto')
    ret = perl_proto()
    assert(str(ret) == "Hello world!")

    # broken statement
    failed = False
    try:
        perl_proto(1)
    except bond.RemoteException as e:
        print(e)
        failed = True
    assert(failed)


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

    # literal values
    assert(perl.eval('1') == 1)
    assert(perl.eval('undef') is None)
    assert(perl.eval_block('1;') is None)

    # expression
    assert(perl.eval('1 + 1') == 2)

    # check eval with unscoped variables
    perl.eval_block('$x = 1;')
    assert(perl.eval('$x // -1') == 1)

    # eval in Perl is scoped
    perl.eval_block('my $y = 1;')
    assert(perl.eval('$y // -1') == -1)

    # function definition
    perl.eval('sub test_perl { shift() + 1; }')
    assert(perl.eval('test_perl(0);') == 1)


def test_ser_err():
    perl = Perl(timeout=1)

    # construct an unserializable type
    perl.eval_block(r'''
    use IO::File;
    $fd = IO::File->new();
    sub func { $fd; }
    ''')

    # try to send it across
    failed = False
    try:
        perl.eval('$fd')
    except bond.SerializationException as e:
        print(e)
        failed = (e.side == "remote")
    assert(failed)

    # ensure the env didn't just die
    assert(perl.eval('1') == 1)

    # ... with call (return)
    failed = False
    try:
        perl.call('func')
    except bond.SerializationException as e:
        print(e)
        failed = (e.side == "remote")
    assert(failed)

    # ensure the env didn't just die
    assert(perl.eval('1') == 1)

    # ... with an exception
    failed = False
    try:
        perl.eval('die $fd')
    except bond.SerializationException as e:
        print(e)
        failed = (e.side == "remote")
    assert(failed)

    # ensure the env didn't just die
    assert(perl.eval('1') == 1)


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


def test_exception():
    perl = Perl(timeout=1)

    # remote exception
    perl.eval_block('sub exceptional() { die $@; }')

    # ... in eval
    failed = False
    try:
        perl.eval('exceptional()')
    except bond.RemoteException as e:
        print(e)
        failed = True
    assert(failed)

    # ... in eval_block
    failed = False
    try:
        perl.eval_block('exceptional()');
    except bond.RemoteException as e:
        print(e)
        failed = True
    assert(failed)

    # ... in call
    failed = False
    try:
        perl.call('exceptional')
    except bond.RemoteException as e:
        print(e)
        failed = True
    assert(failed)


def test_export():
    def call_me():
        return 42

    perl = Perl(timeout=1)
    perl.export(call_me, 'call_me')
    assert(perl.call('call_me') == 42)


def test_export_recursive():
    perl = Perl(timeout=1)

    # define a remote function
    perl.eval(r'sub func_perl { shift() + 1; }')
    func_perl = perl.callable('func_perl')
    assert(func_perl(0) == 1)

    # define a local function that calls the remote
    def func_python(arg):
        return func_perl(arg + 1)

    assert(func_python(0) == 2)

    # export the function remotely and call it
    perl.export(func_python, 'remote_func_python')
    remote_func_python = perl.callable('remote_func_python')
    assert(remote_func_python(0) == 2)

    # define a remote function that calls us recursively
    perl.eval(r'sub func_perl_rec { remote_func_python(shift()) + 1; }')
    func_perl_rec = perl.callable('func_perl_rec')
    assert(func_perl_rec(0) == 3)

    # inception
    def func_python_rec(arg):
        return func_perl_rec(arg) + 1

    perl.export(func_python_rec, 'remote_func_python_rec')
    perl.eval(r'sub func_perl_rec_2 { remote_func_python_rec(shift()) + 1; }')
    func_perl_rec_2 = perl.callable('func_perl_rec_2')
    assert(func_perl_rec_2(0) == 5)


def test_export_ser_err():
    def call_me(arg):
        pass

    perl = Perl(timeout=1)
    perl.export(call_me, 'call_me')
    perl.eval_block(r'''
    use IO::File;
    $fd = IO::File->new();
    ''')

    failed = False
    try:
        perl.eval('call_me($fd)')
    except bond.SerializationException as e:
        print(e)
        failed = (e.side == "remote")
    assert(failed)

    # ensure the env didn't just die
    assert(perl.eval('1') == 1)


def test_output_redirect():
    perl = Perl(timeout=1)

    # stdout
    perl.eval_block(r'print "Hello world!\n";')
    assert(perl.eval('1') == 1)

    # stderr
    perl.eval_block(r'print STDERR "Hello world!\n"')
    assert(perl.eval('1') == 1)

    # warnings
    perl.eval_block(r'use warnings; "$undefined";')
    assert(perl.eval('1') == 1)
