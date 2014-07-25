from bond.PHP import PHP

php = PHP(timeout=1)
php_print = php.callable('sprintf')
ret = php_print("Hello world!")
assert(str(ret) == "Hello world!")
