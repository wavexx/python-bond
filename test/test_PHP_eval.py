from bond.PHP import PHP

php = PHP(timeout=1)
assert(php.eval_block('1;') is None)
assert(php.eval_block('return 1;') == 1)

php.eval('function test_php($arg) { return $arg + 1; }')
assert(php.eval('return test_php(0);') == 1)
assert(php.eval_block('return test_php(0);') == 1)
