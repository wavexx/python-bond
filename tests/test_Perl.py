from __future__ import print_function
import bond
from tests import *

def test_basic():
    perl = bond.make_bond('Perl', timeout=TIMEOUT)
    perl.close()


def test_basic_rmt():
    perl = bond.make_bond('Perl', "ssh localhost perl", timeout=TIMEOUT)
    perl.close()


def test_call_marshalling():
    perl = bond.make_bond('Perl', timeout=TIMEOUT)

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
    perl = bond.make_bond('Perl', timeout=TIMEOUT)
    perl.eval('sub test_simple { "Hello world!"; }')
    perl_simple = perl.callable('test_simple')
    ret = perl_simple()
    assert(str(ret) == "Hello world!")

    perl.eval('sub test_proto() { "Hello world!"; }')
    perl_proto = perl.callable('test_proto')
    ret = perl_proto()
    assert(str(ret) == "Hello world!")


def test_call_stm():
    perl = bond.make_bond('Perl', timeout=TIMEOUT)

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
    perl = bond.make_bond('Perl', timeout=TIMEOUT)
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
    perl = bond.make_bond('Perl', timeout=TIMEOUT)

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
    perl = bond.make_bond('Perl', timeout=TIMEOUT)

    # NOTE: sprintf is a built-in, and thus more compliated to call with
    #       the same semantics
    perl_sprintf = perl.callable('sprintf')
    ret = perl_sprintf("Hello world!")
    assert(str(ret) == "Hello world!")

    # no exception should be thrown here
    perl.call('print', 'Hellow world!')


def test_eval():
    perl = bond.make_bond('Perl', timeout=TIMEOUT)

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

    # 'our' scope
    perl.eval_block('our $z = 1;')
    assert(perl.eval('$z // -1') == 1)

    # function definition
    perl.eval('sub test_perl { shift() + 1; }')
    assert(perl.eval('test_perl(0);') == 1)


def test_eval_sentinel():
    perl = bond.make_bond('Perl', timeout=TIMEOUT)

    # ensure the sentinel is not accessible
    failed = False
    try:
        perl.eval('$SENTINEL')
    except bond.RemoteException as e:
        print(e)
        failed = True
    assert(True)


def test_eval_rec():
    perl = bond.make_bond('Perl', timeout=TIMEOUT)

    # in a recursive call, we should still be able to see our global scope
    def call_me():
        assert(perl.eval('$should_exist') == 1)
        assert(perl.eval('$should_not_exist // -1') == -1)

    perl.export(call_me)
    perl.eval_block('$should_exist = 1')
    assert(perl.eval('$should_exist') == 1)
    perl.call('call_me')


def test_ser_err():
    perl = bond.make_bond('Perl', timeout=TIMEOUT, trans_except=True)

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
    perl = bond.make_bond('Perl', timeout=TIMEOUT)

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
    perl = bond.make_bond('Perl', timeout=TIMEOUT)

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

    perl = bond.make_bond('Perl', timeout=TIMEOUT)
    perl.export(call_me, 'call_me')
    assert(perl.call('call_me') == 42)


def test_export_redef():
    perl = bond.make_bond('Perl', timeout=TIMEOUT)

    def call_me():
        return 42

    perl.export(call_me)
    try:
        perl.export(call_me)
    except:
        pass

    assert(perl.call('call_me') == 42)


def test_export_invalid():
    perl = bond.make_bond('Perl', timeout=TIMEOUT)

    def call_me():
        return 42

    try:
        perl.export(call_me, 'invalid name')
    except Exception as e:
        print(e)

    assert(perl.eval('1') == 1)


def test_export_recursive():
    perl = bond.make_bond('Perl', timeout=TIMEOUT)

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

    perl = bond.make_bond('Perl', timeout=TIMEOUT)
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


def test_export_except():
    perl = bond.make_bond('Perl', timeout=TIMEOUT)

    def gen_exception():
        raise Exception("test")

    perl.export(gen_exception)
    perl.eval_block(r'''
    sub test_exception
    {
        my $ret = 0;
        eval { gen_exception() };
        $ret = 1 if($@);
        return $ret;
    }''')

    assert(perl.call('test_exception') == True)


def test_output_redirect():
    perl = bond.make_bond('Perl', timeout=TIMEOUT)

    # stdout
    perl.eval_block(r'print "stdout: Hello world!\n";')
    assert(perl.eval('1') == 1)

    # stderr
    perl.eval_block(r'print STDERR "stderr: Hello world!\n"')
    assert(perl.eval('1') == 1)

    # warnings
    perl.eval_block(r'use warnings; "$warning_expected_on_stderr";')
    assert(perl.eval('1') == 1)


def test_trans_except():
    perl_trans = bond.make_bond('Perl', timeout=TIMEOUT, trans_except=True)
    perl_not_trans = bond.make_bond('Perl', timeout=TIMEOUT, trans_except=False)

    code = r'''sub func() { die \&func; }'''

    # by default exceptions are transparent, so the following should try to
    # serialize the code block (and fail)
    perl_trans.eval_block(code)
    failed = False
    try:
        ret = perl_trans.call('func')
    except bond.SerializationException as e:
        print(e)
        failed = (e.side == "remote")
    assert(failed)

    # ensure the env didn't just die
    assert(perl_trans.eval('1') == 1)

    # this one though will just always forward the remote exception
    perl_not_trans.eval_block(code)
    failed = False
    try:
        ret = perl_not_trans.call('func')
    except bond.RemoteException as e:
        failed = True
    assert(failed)

    # ensure the env didn't just die
    assert(perl_not_trans.eval('1') == 1)


def test_export_trans_except():
    perl_trans = bond.make_bond('Perl', timeout=TIMEOUT, trans_except=True)
    perl_not_trans = bond.make_bond('Perl', timeout=TIMEOUT, trans_except=False)

    def call_me():
       raise RuntimeError("a runtime error")

    # by default exceptions are transparent, so the following should try to
    # serialize RuntimeError in JSON (and fail)
    perl_trans.export(call_me)
    perl_trans.eval_block(r'''
    sub test_exception()
    {
        my $ret = 0;
        eval { call_me(); };
        $ret = 1 if $@ =~ /SerializationException/;
        return $ret;
    }
    ''')
    assert(perl_trans.call('test_exception') == True)

    # this one though will just generate a string
    perl_not_trans.export(call_me)
    perl_not_trans.eval_block(r'''
    sub test_exception()
    {
        my $ret = 0;
        eval { call_me(); };
        $ret = 1 if $@ !~ /SerializationException/ && $@ =~ /a runtime error/;
        return $ret;
    }
    ''')
    assert(perl_not_trans.call('test_exception') == True)


def test_stack_depth():
    def no_exception():
        pass

    def gen_exception():
        raise Exception("test")

    def gen_ser_err():
        return lambda x: x

    # check normal stack depth
    perl = bond.make_bond('Perl', timeout=TIMEOUT)
    assert(bond_repl_depth(perl) == 1)

    # check stack depth after calling a normal function
    perl = bond.make_bond('Perl', timeout=TIMEOUT)
    perl.export(no_exception)
    perl.call('no_exception')
    assert(bond_repl_depth(perl) == 1)

    # check stack depth after returning a serializable exception
    perl = bond.make_bond('Perl', timeout=TIMEOUT)
    perl.export(gen_exception)
    got_except = False
    try:
        perl.call('gen_exception')
    except bond.RemoteException as e:
        print(e)
        got_except = True
    assert(got_except)
    assert(bond_repl_depth(perl) == 1)

    # check stack depth after a remote serialization error
    perl = bond.make_bond('Perl', timeout=TIMEOUT)
    perl.export(gen_ser_err)
    got_except = False
    try:
        perl.call('gen_ser_err')
    except bond.SerializationException as e:
        print(e)
        assert(e.side == "remote")
        got_except = True
    assert(got_except)
    assert(bond_repl_depth(perl) == 1)


def _test_buf_size(perl):
    perl.eval_block('sub id { shift() }')
    for size in [2 ** n for n in range(9, 16)]:
        print("testing buffer >= {} bytes".format(size))
        buf = "x" * size
        ret = perl.call('id', buf)
        assert(ret == str(ret))

def test_buf_size():
    perl = bond.make_bond('Perl', timeout=TIMEOUT)
    _test_buf_size(perl)

def test_buf_size_rmt():
    perl = bond.make_bond('Perl', "ssh localhost perl", timeout=TIMEOUT)
    _test_buf_size(perl)
