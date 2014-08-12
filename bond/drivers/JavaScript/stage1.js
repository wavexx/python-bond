/// python-bond Javascript interface setup
/// NOTE: use /// for comments only, as this code is transformed into a single
///       line to be injected into the interpreter *without parsing*.
var fs = require("fs");

/// Define some constants/methods that will be used also in stage2
var __PY_BOND_STDIN = fs.openSync("/dev/stdin", "r");

function __PY_BOND_getline()
{
  var line = "";
  var buf = new Buffer(1);
  while(fs.readSync(__PY_BOND_STDIN, buf, 0, 1) > 0)
  {
    if(buf[0] == 10) break;
    line += buf;
  }
  return line.trimRight();
}


/// Actual loader
(function()
{
  console.log("STAGE2");
  var line = __PY_BOND_getline();
  var stage2 = JSON.parse(line);
  eval.call(null, stage2.code);
  __PY_BOND_start.apply(null, stage2.start);
}).call(null);
