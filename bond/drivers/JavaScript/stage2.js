// python-bond Javascript interface setup
var util = require("util");

// Channels and buffers
var __PY_BOND_BUFFERS = {
  "STDOUT": "",
  "STDERR": ""
};

var __PY_BOND_CHANNELS = {
  "STDIN": __PY_BOND_STDIN,
  "STDOUT": fs.openSync("/dev/stdout", "w"),
  "STDERR": fs.openSync("/dev/stderr", "w")
};


// Define our own i/o methods
function __PY_BOND_sendline(line)
{
  if(line == null) line = "";
  var buf = new Buffer(line + "\n");
  fs.writeSync(__PY_BOND_CHANNELS["STDOUT"], buf, 0, buf.length);
}


// Our minimal exception signature
function _PY_BOND_SerializationException(message)
{
  this.message = message;
}

util.inherits(_PY_BOND_SerializationException, TypeError);
_PY_BOND_SerializationException.prototype.name = "_PY_BOND_SerializationException";


// Serialization methods
function __PY_BOND_typecheck(key, value)
{
  if(typeof value === 'function' && value.toJSON == null)
    throw new TypeError("cannot serialize " + Object.getPrototypeOf(value));
  return value;
}

function __PY_BOND_dumps(data)
{
  var ret;
  try { ret = JSON.stringify(data, __PY_BOND_typecheck); }
  catch(e) { throw new _PY_BOND_SerializationException(e.toString()); }
  return ret;
}

function __PY_BOND_loads(string)
{
  return JSON.parse(string);
}


// Recursive repl
var __PY_BOND_TRANS_EXCEPT;

function __PY_BOND_call(name, args)
{
  var code = __PY_BOND_dumps([name, args]);
  __PY_BOND_sendline("CALL " + code);
  return __PY_BOND_repl();
}

function __PY_BOND_export(name)
{
  global[name] = function()
  {
    return __PY_BOND_call(name, Array.prototype.slice.call(arguments));
  };
}

function __PY_BOND_repl()
{
  var SENTINEL = 1;
  var line;
  while((line = __PY_BOND_getline()))
  {
    line = /^([^ ]+)( (.*))?/.exec(line);
    var cmd = line[1];
    var args = (line[3] !== undefined? __PY_BOND_loads(line[3]): []);

    var ret = null;
    var err = null;
    switch(cmd)
    {
    case "EVAL":
      try { ret = eval.call(null, "(" + args + ")"); }
      catch(e) { err = e; }
      break;

    case "EVAL_BLOCK":
      try { eval.call(null, args); }
      catch(e) { err = e; }
      break;

    case "EXPORT":
      __PY_BOND_export(args);
      break;

    case "CALL":
      try
      {
	// NOTE: we add an extra set of parenthesis to allow anonymous
	//       functions to be parsed without an assignment
	var func = eval.call(null, "(" + args[0] + ")");
	ret = func.apply(null, args[1]);
      }
      catch(e)
      {
	err = e;
      }
      break;

    case "RETURN":
      return args;

    case "EXCEPT":
      throw new Error(args);

    case "ERROR":
      throw new _PY_BOND_SerializationException(args);

    default:
      process.exit(1);
    }

    // redirected channels
    for(var chan in __PY_BOND_BUFFERS)
    {
      var buf = __PY_BOND_BUFFERS[chan];
      if(buf.length)
      {
	var code = __PY_BOND_dumps([chan, buf]);
	__PY_BOND_sendline("OUTPUT " + code);
	__PY_BOND_BUFFERS[chan] = "";
      }
    }

    // error state
    var state = "RETURN";
    if(err != null)
    {
      if(err instanceof _PY_BOND_SerializationException)
      {
	state = "ERROR";
	ret = err.message;
      }
      else
      {
	state = "EXCEPT";
	ret = (__PY_BOND_TRANS_EXCEPT? err: err.toString());
      }
    }
    var code;
    try
    {
      if(ret == null) ret = null;
      code = __PY_BOND_dumps(ret);
    }
    catch(e)
    {
      state = "ERROR";
      code = __PY_BOND_dumps(e.message);
    }
    __PY_BOND_sendline(state + " " + code);
  }
  return 0;
}

function __PY_BOND_start(proto, trans_except)
{
  // TODO: this is a hack
  process.stdout.write = function(buf) { __PY_BOND_BUFFERS["STDOUT"] += buf; };
  process.stderr.write = function(buf) { __PY_BOND_BUFFERS["STDERR"] += buf; };
  process.stdin.read = function() { return undefined; };

  __PY_BOND_TRANS_EXCEPT = trans_except;
  __PY_BOND_sendline("READY");
  var ret = __PY_BOND_repl();
  __PY_BOND_sendline("BYE");
  process.exit(ret);
}
