from __future__ import print_function
from bond.PHP import PHP

# Spawn a new PHP interpreter
php = PHP()

# Show some remote output locally
php.eval(r'echo "Hello world from PHP!\n";')

# Let's call a remote function
ret = php.call('join', ' ', ['Hello', 'world', 'from', 'python?'])
print(ret)

# Let's define a new remote function and call it
php.eval(r'function add1($arg) { return $arg + 1; }')
ret = php.call('add1', 0)
print("Return of add1(0): {}".format(ret))

# Make the remote function transparent
add1 = php.callable('add1')
ret = add1(1)
print("Return of add1(1): {}".format(ret))

# Export an existing function *to* PHP
def python_function():
    print("Hello world from php?")

php.export(python_function, 'python_function')
php.eval('python_function();')

# Recursive invocation
def python_1():
    return "Hello world?!"

php.export(python_1, 'python_1')
php.eval(r'function php_1() { return python_1(); }')
remote_php_1 = php.callable('php_1')

def python_2():
    return remote_php_1()

php.export(python_2, 'python_2')
php.eval(r'function php_2() { return python_2(); }')
remote_php_2 = php.callable('php_2')
print("Who says {}".format(remote_php_2()))

# Bridge two interpreters
php2 = PHP()
php2.eval(r'function php_3() { return array(105, 110, 99, 101, 112, 116, 105, 111, 110); } ')
php2.proxy('php_3', php)
php.eval(r'''
foreach(php_3() as $i) {
  echo chr($i - 32);
}
echo "\n";
''')
