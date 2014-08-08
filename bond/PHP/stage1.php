/// python-bond PHP interface loader
/// NOTE: use /// for comments *only*, as this code is transformed into a
///       single line to be injected into the interpreter *without parsing*.

echo "STAGE2\n";
$__PY_BOND_STDIN = fopen("php://stdin", "r");
$__PY_BOND_STAGE2 = json_decode(rtrim(fgets($__PY_BOND_STDIN)));
eval($__PY_BOND_STAGE2->code);
call_user_func_array($__PY_BOND_STAGE2->func, $__PY_BOND_STAGE2->args);
