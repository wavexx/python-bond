from __future__ import print_function
from bond.PHP import PHP

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
