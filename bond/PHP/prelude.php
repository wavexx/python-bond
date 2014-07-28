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


/// some utilities to get/reset the error state
function __PY_BOND_clear_error()
{
  set_error_handler(null, 0);
  @trigger_error(null);
  restore_error_handler();
}

function __PY_BOND_get_error()
{
  $err = error_get_last();
  if($err) $err = $err["message"];
  return $err;
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
    $err = null;
    switch($cmd)
    {
    case "EVAL":
      try
      {
	__PY_BOND_clear_error();
	$ret = @eval("return $args;");
	$err = __PY_BOND_get_error();
      }
      catch(Exception $e)
      {
	$err = $e->getMessage();
      }
      break;

    case "EVAL_BLOCK":
      try
      {
	__PY_BOND_clear_error();
	$ret = @eval($args);
	$err = __PY_BOND_get_error();
      }
      catch(Exception $e)
      {
	$err = $e->getMessage();
      }
      break;

    case "EXPORT":
      $code = "function $args() { return __PY_BOND_remote('$args', func_get_args()); }";
      $ret = eval($code);
      break;

    case "CALL":
      try
      {
	__PY_BOND_clear_error();
	$ret = @call_user_func_array($args[0], $args[1]);
	$err = __PY_BOND_get_error();
      }
      catch(Exception $e)
      {
	$err = $e->getMessage();
      }
      break;

    case "RETURN":
      return $args;

    default:
      exit(1);
    }

    ob_flush();
    if(strlen($__PY_BOND_BUFFER))
    {
      $enc_out = json_encode(array("STDOUT", $__PY_BOND_BUFFER));
      __PY_BOND_sendline("OUTPUT $enc_out");
      $__PY_BOND_BUFFER = '';
    }

    /// error state
    $state = null;
    if(!$err) {
      $state = "RETURN";
    }
    else
    {
      $state = "ERROR";
      $ret = $err;
    }

    $enc_ret = json_encode($ret);
    __PY_BOND_sendline("$state $enc_ret");
  }
  exit(0);
}

function __PY_BOND_start()
{
  ob_start('__PY_BOND_output');
  __PY_BOND_sendline("READY");
  exit(__PY_BOND_repl());
}
