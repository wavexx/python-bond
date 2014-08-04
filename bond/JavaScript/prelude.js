// python-bond Javascript interface setup

// Channels and buffers
var __PY_BOND_BUFFERS = {
  "STDOUT": "",
  "STDERR": ""
};

var __PY_BOND_CHANNELS = {
  "STDIN": fs.openSync("/dev/stdin", "r"),
  "STDOUT": fs.openSync("/dev/stdout", "w"),
  "STDERR": fs.openSync("/dev/stderr", "w")
};


// Define our own i/o methods
function __PY_BOND_getline()
{
  var line = "";
  var buf = new Buffer(1);
  while(fs.readSync(__PY_BOND_CHANNELS["STDIN"], buf, 0, 1) > 0)
  {
    if(buf[0] == 10) break;
    line += buf;
  }
  return line;
}

function __PY_BOND_sendline(line)
{
  if(line == null) line = "";
  var buf = new Buffer(line + "\n");
  fs.writeSync(__PY_BOND_CHANNELS["STDOUT"], buf, 0, buf.length);
};


// Recursive repl
var __PY_BOND_TRANS_EXCEPT;

function __PY_BOND_sendstate(state, data)
{
  var enc_ret = null;
  try
  {
    enc_ret = JSON.stringify(data, function(key, value)
    {
      // ensure functions are not silently dropped
      var type = typeof value;
      if(typeof value === 'function' && value.toJSON === undefined)
	throw new TypeError("cannot serialize " + Object.getPrototypeOf(value));
      return value;
    });
  }
  catch(e)
  {
    state = "ERROR";
    enc_ret = JSON.stringify(e.toString());
  }
  __PY_BOND_sendline(state + " " + enc_ret);
}

function __PY_BOND_call(name, args)
{
  __PY_BOND_sendstate("CALL", [name, args]);
  return __PY_BOND_repl();
}

function __PY_BOND_export(name)
{
  global[name] = function()
  {
    var args = [];
    for(var k in arguments)
      args.push(arguments[k]);
    return __PY_BOND_call(name, args);
  };
}

function __PY_BOND_repl()
{
  var line;
  while((line = __PY_BOND_getline()))
  {
    line = /^([^ ]+)( (.*))?/.exec(line);
    var cmd = line[1];
    var args = (line[3] !== undefined? JSON.parse(line[3]): []);

    var ret = null;
    var err = null;
    switch(cmd)
    {
    case "EVAL":
      try { ret = eval.call(null, args); }
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
    case "ERROR":
      throw new Error(args);

    default:
      process.exit(1);
    }

    // redirected channels
    for(var chan in __PY_BOND_BUFFERS)
    {
      var buf = __PY_BOND_BUFFERS[chan];
      if(buf.length)
      {
	var enc_out = JSON.stringify([chan, buf]);
	__PY_BOND_sendline("OUTPUT " + enc_out);
	__PY_BOND_BUFFERS[chan] = "";
      }
    }

    // error state
    var state;
    if(err == null)
    {
      state = "RETURN";
      if(ret == null) ret = null;
    }
    else
    {
      state = "EXCEPT";
      ret = (__PY_BOND_TRANS_EXCEPT? err: err.toString());
    }

    __PY_BOND_sendstate(state, ret);
  }
  return 0;
}

function __PY_BOND_start(trans_except)
{
  // TODO: this is a hack
  process.stdout.write = function(buf) { __PY_BOND_BUFFERS["STDOUT"] += buf; };
  process.stderr.write = function(buf) { __PY_BOND_BUFFERS["STDERR"] += buf; };
  process.stdin = fs.open("/dev/null", "r");

  __PY_BOND_TRANS_EXCEPT = trans_except;
  __PY_BOND_sendline("READY");
  process.exit(__PY_BOND_repl());
};
