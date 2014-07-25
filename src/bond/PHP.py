from bond import *
import re


# PHP constants
PHP_PROMPT    = r'php > '
PHP_WRAP_PREFIX = '__PY_BOND'

# Some local constants and definitions
_PHP_FUN_DECL = re.compile(r'^\s*function\s+(\w+)')
_PHP_PRELUDE = r'''

# Define STDIN/STDOUT
define("%(PHP_WRAP_PREFIX)s_STDIN", fopen("php://stdin","r"));
define("%(PHP_WRAP_PREFIX)s_STDOUT", fopen("php://stdout","w"));

# Use a custom output filter to redirect normal output
function %(PHP_WRAP_PREFIX)s_output($buffer, $phase)
{
  if(!strlen($buffer)) return;
  $enc_ret = json_encode($buffer);
  %(PHP_WRAP_PREFIX)s_sendline("OUTPUT $enc_ret");
}

ob_start('%(PHP_WRAP_PREFIX)s_output');

# Define our own i/o methods
function %(PHP_WRAP_PREFIX)s_getline()
{
  return rtrim(fgets(%(PHP_WRAP_PREFIX)s_STDIN));
}

function %(PHP_WRAP_PREFIX)s_sendline($line = '')
{
  fwrite(%(PHP_WRAP_PREFIX)s_STDOUT, $line . "\n");
  fflush(%(PHP_WRAP_PREFIX)s_STDOUT);
}

# Recursive repl
function %(PHP_WRAP_PREFIX)s_remote($name, $args)
{
  $json = json_encode(array($name, $args));
  %(PHP_WRAP_PREFIX)s_sendline("REMOTE $json");
  return %(PHP_WRAP_PREFIX)s_repl();
}

function %(PHP_WRAP_PREFIX)s_repl()
{
  while($line = %(PHP_WRAP_PREFIX)s_getline())
  {
    $line = explode(" ", $line, 2);
    $cmd = $line[0];
    $args = (count($line) > 1? json_decode($line[1]): array());

    $ret = null;
    switch($cmd)
    {
    case "EVAL":
      $ret = eval($args);
      break;

    case "CALL":
      $ret = call_user_func_array($args[0], $args[1]);
      break;

    case "RETURN":
      return $args;

    default:
      exit(1);
    }

    ob_flush();
    $enc_ret = json_encode($ret);
    %(PHP_WRAP_PREFIX)s_sendline("RETURN $enc_ret");
  }
  exit(0);
}

function %(PHP_WRAP_PREFIX)s_start()
{
  %(PHP_WRAP_PREFIX)s_sendline("READY");
  exit(%(PHP_WRAP_PREFIX)s_repl());
}

''' % locals()


def _strip_newlines(code):
    """Turn a PHP code block into one line, so that an interactive PHP prompt
    does not output cruft while interpreting it"""
    # TODO: this is buggy on several levels. We could pre-process code using
    #       `php -w`, but it sounds prohibitive. But it's good enough for our
    #       prelude.
    return re.sub(r'(?:#.*)?\n\s*', '', code)


class PHP(bond):
    def __init__(self, php="php -a", timeout=None):
        proc = spawn(php, timeout=timeout)
        proc.silent_expect(PHP_PROMPT)

        # inject our prelude
        code = _strip_newlines(_PHP_PRELUDE)
        proc.silent_sendline(r'{code}; {PHP_WRAP_PREFIX}_sendline();'.format(
            PHP_WRAP_PREFIX=PHP_WRAP_PREFIX, code=code))
        proc.silent_expect(r'\r\n{prompt}'.format(prompt=PHP_PROMPT))

        # start the inner repl
        proc.silent_sendline(r'{PHP_WRAP_PREFIX}_start();'.format(
            PHP_WRAP_PREFIX=PHP_WRAP_PREFIX))
        super(PHP, self).__init__(proc)

    def eval_block(self, code):
        code = r'call_user_func(function(){ %(code)s; });' % {'code': code}
        return self.eval(code)

    def export(self, func, name):
        code = r'function %(name)s() { return %(PHP_WRAP_PREFIX)s_remote("%(name)s", func_get_args()); }' % {
            'PHP_WRAP_PREFIX': PHP_WRAP_PREFIX,
            'name': name}
        self.eval(code)
        super(PHP, self).export(func, name)
