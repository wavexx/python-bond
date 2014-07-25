from bond.PHP import PHP

php = PHP(timeout=1)
php.eval_block(r'echo "Hello world!\n";')
