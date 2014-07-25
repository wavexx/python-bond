from bond.PHP import PHP

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
