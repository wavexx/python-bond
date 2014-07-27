from __future__ import print_function
import bond

def test_call_PHP_Perl():
    php = bond.PHP.PHP(timeout=1)
    perl = bond.Perl.Perl(timeout=1)
    assert(php and perl)

    php.eval_block(r'function func_php($arg) { return $arg + 1; }')
    php.proxy('func_php', perl)

    func_perl = perl.callable('func_php')
    ret = func_perl(0)
    assert(ret == 1)


def test_call_Perl_PHP():
    php = bond.PHP.PHP(timeout=1)
    perl = bond.Perl.Perl(timeout=1)
    assert(php and perl)

    perl.eval_block(r'sub func_perl { shift() + 1; }')
    perl.proxy('func_perl', php)

    func_php = php.callable('func_perl')
    ret = func_php(0)
    assert(ret == 1)
