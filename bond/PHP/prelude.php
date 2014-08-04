/// python-bond PHP interface setup
/// NOTE: use /// for comments only, as this code is transformed into a single
///       line to be injected into the interpreter *without parsing*.

/// Redirect normal output
$__PY_BOND_BUFFERS = array(
    "STDOUT" => "",
    "STDERR" => ""
);

class __PY_BOND_BUFFERED
{
  public $name;

  public function stream_open($path, $mode, $options, &$opened_path)
  {
    global $__PY_BOND_BUFFERS;
    $path = strtoupper(substr(strstr($path, "://"), 3));
    if(!isset($__PY_BOND_BUFFERS[$path]))
      return false;
    $this->name = $path;
    return true;
  }

  public function stream_write($data)
  {
    global $__PY_BOND_BUFFERS;
    $buffer = &$__PY_BOND_BUFFERS[$this->name];
    $buffer .= $data;
    return strlen($data);
  }
}


/// Redefine standard streams
$__PY_BOND_CHANNELS = array(
    "STDIN" => fopen("php://stdin", "r"),
    "STDOUT" => fopen("php://stdout", "w"),
    "STDERR" => fopen("php://stderr", "w")
);

stream_wrapper_unregister("php");
stream_wrapper_register("php", "__PY_BOND_BUFFERED");

if(!defined("STDIN"))
  define('STDIN', null);
if(!defined("STDOUT"))
  define('STDOUT', fopen("php://stdout", "w"));
if(!defined("STDERR"))
  define('STDERR', fopen("php://stderr", "w"));


/// Define our own i/o methods
function __PY_BOND_output($buffer, $phase)
{
  fwrite(STDOUT, $buffer);
}

function __PY_BOND_getline()
{
  global $__PY_BOND_CHANNELS;
  return rtrim(fgets($__PY_BOND_CHANNELS['STDIN']));
}

function __PY_BOND_sendline($line = '')
{
  global $__PY_BOND_CHANNELS;
  $stdout = $__PY_BOND_CHANNELS['STDOUT'];
  fwrite($stdout, $line . "\n");
  fflush($stdout);
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
$__PY_BOND_TRANS_EXCEPT = null;

function __PY_BOND_sendstate($state, $data)
{
  $enc_ret = json_encode($data);
  if(json_last_error())
  {
    $state = "ERROR";
    $enc_ret = json_encode(@"cannot encode $data");
  }
  __PY_BOND_sendline("$state $enc_ret");
}

function __PY_BOND_call($name, $args)
{
  __PY_BOND_sendstate("CALL", array($name, $args));
  return __PY_BOND_repl();
}

function __PY_BOND_repl()
{
  global $__PY_BOND_BUFFERS, $__PY_BOND_TRANS_EXCEPT;

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
	$err = $e;
      }
      break;

    case "EVAL_BLOCK":
      try
      {
	__PY_BOND_clear_error();
	@eval($args);
	$err = __PY_BOND_get_error();
      }
      catch(Exception $e)
      {
	$err = $e;
      }
      break;

    case "EXPORT":
      $name = $args;
      if(function_exists($name))
	$err = "Function \"$name\" already exists";
      else
      {
	$code = "function $name() { return __PY_BOND_call('$args', func_get_args()); }";
	__PY_BOND_clear_error();
	@eval($code);
	$err = __PY_BOND_get_error();
      }
      break;

    case "CALL":
      try
      {
	$name = $args[0];

	__PY_BOND_clear_error();
	if(preg_match("/^[a-zA-Z_\x7f-\xff][a-zA-Z0-9_\x7f-\xff]*$/", $name) || is_callable($name))
	{
	  /// special-case regular functions to avoid fatal errors in PHP
	  $ret = @call_user_func_array($args[0], $args[1]);
	}
	else
	{
	  /// construct a string that we can interpret "function-like", to
	  /// handle also function references and method calls uniformly
	  $args_ = array();
	  foreach($args[1] as $el)
	    $args_[] = var_export($el, true);
	  $args_ = implode(", ", $args_);
	  $ret = @eval("return " . $name . "(" . $args_ . ");");
	}
	$err = __PY_BOND_get_error();
      }
      catch(Exception $e)
      {
	$err = $e;
      }
      break;

    case "RETURN":
      return $args;

    case "EXCEPT":
    case "ERROR":
      throw new Exception($args);

    default:
      exit(1);
    }

    /// redirected channels
    ob_flush();
    foreach($__PY_BOND_BUFFERS as $chan => &$buf)
    {
      if(strlen($buf))
      {
	$enc_out = json_encode(array($chan, $buf));
	__PY_BOND_sendline("OUTPUT $enc_out");
	$buf = "";
      }
    }

    /// error state
    $state = null;
    if(!$err) {
      $state = "RETURN";
    }
    else
    {
      $state = "EXCEPT";
      if($__PY_BOND_TRANS_EXCEPT)
	$ret = $err;
      else
	$ret = ($err instanceOf Exception? $err->getMessage(): @"$err");
    }

    __PY_BOND_sendstate($state, $ret);
  }
  return 0;
}

function __PY_BOND_start($trans_except)
{
  global $__PY_BOND_TRANS_EXCEPT;
  ob_start('__PY_BOND_output');
  $__PY_BOND_TRANS_EXCEPT = (bool)($trans_except);
  __PY_BOND_sendline("READY");
  exit(__PY_BOND_repl());
}
