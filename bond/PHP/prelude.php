/// python-bond PHP interface setup
/// NOTE: use /// for comments only, as this code is transformed into a single
///       line to be injected into the interpreter *without parsing*.

/// Define STDIN/STDOUT
define("__PY_BOND_STDIN", fopen("php://stdin","r"));
define("__PY_BOND_STDOUT", fopen("php://stdout","w"));

/// Use a custom output filter to redirect normal output
$__PY_BOND_BUFFER = '';

function __PY_BOND_output($buffer, $phase)
{
  global $__PY_BOND_BUFFER;
  $__PY_BOND_BUFFER .= $buffer;
}

ob_start('__PY_BOND_output');


/// Define our own i/o methods
function __PY_BOND_getline()
{
  return rtrim(fgets(__PY_BOND_STDIN));
}

function __PY_BOND_sendline($line = '')
{
  fwrite(__PY_BOND_STDOUT, $line . "\n");
  fflush(__PY_BOND_STDOUT);
}


/// Recursive repl
function __PY_BOND_remote($name, $args)
{
  $json = json_encode(array($name, $args));
  __PY_BOND_sendline("REMOTE $json");
  return __PY_BOND_repl();
}

function __PY_BOND_repl()
{
  global $__PY_BOND_BUFFER;
  while($line = __PY_BOND_getline())
  {
    $line = explode(" ", $line, 2);
    $cmd = $line[0];
    $args = (count($line) > 1? json_decode($line[1]): array());

    $ret = null;
    switch($cmd)
    {
    case "EVAL":
      /// TODO: handle eval errors
      $ret = eval($args);
      break;

    case "EVAL_BLOCK":
      /// TODO: handle eval errors
      $args = "return call_user_func(function(){ $args });";
      $ret = eval($args);
      break;

    case "EXPORT":
      $code = "function $args() { return __PY_BOND_remote('$args', func_get_args()); }";
      $ret = eval($code);
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
    $enc_out = json_encode($__PY_BOND_BUFFER);
    __PY_BOND_sendline("OUTPUT $enc_out");
    $__PY_BOND_BUFFER = '';

    $enc_ret = json_encode($ret);
    __PY_BOND_sendline("RETURN $enc_ret");
  }
  exit(0);
}

function __PY_BOND_start()
{
  __PY_BOND_sendline("READY");
  exit(__PY_BOND_repl());
}
