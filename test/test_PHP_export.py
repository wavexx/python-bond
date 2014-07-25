from bond.PHP import PHP

def call_me():
    return 42

php = PHP(timeout=1)
php.export(call_me, 'call_me')
assert(php.call('call_me') == 42)
