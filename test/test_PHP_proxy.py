from bond.PHP import PHP

php1 = PHP(timeout=1)
php1.eval(r'function func_php1($arg) { return $arg + 1; }')

php2 = PHP(timeout=1)
php1.proxy('func_php1', php2)

assert(php2.call('func_php1', 0) == 1)
