// python-bond PHP interface setup

// Redirect normal output
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


// Redefine standard streams
$__PY_BOND_CHANNELS = array(
    "STDIN" => $__PY_BOND_STDIN,
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


// Define our own i/o methods
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


// Serialization methods
class _PY_BOND_SerializationException extends Exception {}

function __PY_BOND_dumps($data)
{
  $code = json_encode($data);
  if(json_last_error())
    throw new _PY_BOND_SerializationException(@"cannot encode $data");
  return $code;
}

function __PY_BOND_loads($string)
{
  return json_decode($string);
}


// some utilities to get/reset the error state
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


// Recursive repl
$__PY_BOND_TRANS_EXCEPT = null;

function __PY_BOND_call($name, $args)
{
  $code = __PY_BOND_dumps(array($name, $args));
  __PY_BOND_sendline("CALL $code");
  return __PY_BOND_repl();
}

function __PY_BOND_eval($code)
{
  // encase "code" in an anonymous block, hiding our local variables and
  // simulating the global scope
  $SENTINEL = 1;
  __PY_BOND_clear_error();
  $ret = @eval("return call_user_func(function()
  {
    extract(\$GLOBALS);
    return ($code);
  }, null);");
  $err = __PY_BOND_get_error();
  if($err) throw new Exception($err);
  return $ret;
}

function __PY_BOND_exec($code)
{
  $SENTINEL = 1;
  $prefix = "__PY_BOND";
  $prefix_len = strlen($prefix);
  $prefix = var_export($prefix, true);

  // like "eval", but exports any local definition to the global scope
  __PY_BOND_clear_error();
  @eval("call_user_func(function()
  {
    extract(\$GLOBALS);
    { $code }
    \$__PY_BOND_vars = get_defined_vars();
    foreach(\$__PY_BOND_vars as \$k => &\$v)
      \$GLOBALS[\$k] = &\$v;
    foreach(array_keys(\$GLOBALS) as \$k)
      if(!isset(\$__PY_BOND_vars[\$k]))
        unset(\$GLOBALS[\$k]);
  }, null);");
  $err = __PY_BOND_get_error();
  if($err) throw new Exception($err);
}

function __PY_BOND_repl()
{
  global $__PY_BOND_BUFFERS, $__PY_BOND_TRANS_EXCEPT;
  while($line = __PY_BOND_getline())
  {
    $line = explode(" ", $line, 2);
    $cmd = $line[0];
    $args = (count($line) > 1? __PY_BOND_loads($line[1]): array());

    $ret = null;
    $err = null;
    switch($cmd)
    {
    case "EVAL":
      try { $ret = __PY_BOND_eval($args); }
      catch(Exception $e) { $err = $e; }
      break;

    case "EVAL_BLOCK":
      try { __PY_BOND_exec($args); }
      catch(Exception $e) { $err = $e; }
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
	if(preg_match("/^[a-zA-Z_\x7f-\xff][a-zA-Z0-9_\x7f-\xff]*$/", $name) || is_callable($name))
	{
	  // special-case regular functions to avoid fatal errors in PHP
	  __PY_BOND_clear_error();
	  $ret = @call_user_func_array($args[0], $args[1]);
	  $err = __PY_BOND_get_error();
	}
	else
	{
	  // construct a string that we can interpret "function-like", to
	  // handle also function references and method calls uniformly
	  $args_ = array();
	  foreach($args[1] as $el)
	    $args_[] = var_export($el, true);
	  $args_ = implode(", ", $args_);
	  $ret = __PY_BOND_eval("$name($args_)");
	}
      }
      catch(Exception $e)
      {
	$err = $e;
      }
      break;

    case "RETURN":
      return $args;

    case "EXCEPT":
      throw new Exception($args);

    case "ERROR":
      throw new _PY_BOND_SerializationException($args);

    default:
      exit(1);
    }

    // redirected channels
    ob_flush();
    foreach($__PY_BOND_BUFFERS as $chan => &$buf)
    {
      if(strlen($buf))
      {
	$code = __PY_BOND_dumps(array($chan, $buf));
	__PY_BOND_sendline("OUTPUT $code");
	$buf = "";
      }
    }

    // error state
    $state = "RETURN";
    if($err)
    {
      if($err instanceOf _PY_BOND_SerializationException)
      {
	$state = "ERROR";
	$ret = $err->getMessage();
      }
      else
      {
	$state = "EXCEPT";
	if($err instanceOf Exception)
	  $ret = ($__PY_BOND_TRANS_EXCEPT? $err: $err->getMessage());
	else
	  $ret = @"$err";
      }
    }
    $code = null;
    try
    {
      $code = __PY_BOND_dumps($ret);
    }
    catch(Exception $e)
    {
      $state = "ERROR";
      $code = __PY_BOND_dumps($e->getMessage());
    }
    __PY_BOND_sendline("$state $code");
  }
  return 0;
}

function __PY_BOND_start($proto, $trans_except)
{
  global $__PY_BOND_TRANS_EXCEPT;
  ob_start('__PY_BOND_output');
  $__PY_BOND_TRANS_EXCEPT = (bool)($trans_except);
  __PY_BOND_sendline("READY");
  $ret = __PY_BOND_repl();
  __PY_BOND_sendline("BYE");
  exit($ret);
}
