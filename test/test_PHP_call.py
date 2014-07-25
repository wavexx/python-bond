from bond.PHP import PHP

php = PHP(timeout=1)
ret = php.call('sprintf', "Hello world!")
assert(str(ret) == "Hello world!")
