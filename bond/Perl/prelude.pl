# python-bond Perl interface setup
# NOTE: use # for comments only, as this code is transformed into a single
#       line to be injected into the interpreter *without parsing*.
use strict;
use warnings;
use IO::Handle;
use IO::String;
use JSON;
use Data::Dump qw{dump};

# Redirect normal output
my $__PY_BOND_BUFFER = IO::String->new();
my $__PY_BOND_STDIN = *STDIN;
my $__PY_BOND_STDOUT = *STDOUT;


# Define our own i/o methods
my $__PY_BOND_JSON = JSON->new();
$__PY_BOND_JSON->allow_nonref();

sub __PY_BOND_getline()
{
  my $line = <$__PY_BOND_STDIN>;
  chomp($line) if(defined($line));
  return $line;
}

sub __PY_BOND_sendline
{
  my $line = shift // "";
  print $__PY_BOND_STDOUT "$line\n";
  $__PY_BOND_STDOUT->flush();
}


# Recursive repl
sub __PY_BOND_remote($$)
{
  my ($name, $args) = @_;
  my $json = $__PY_BOND_JSON->encode([$name, $args]);
  __PY_BOND_sendline("REMOTE $json");
  return __PY_BOND_repl();
}

sub __PY_BOND_repl()
{
  while(my $line = __PY_BOND_getline())
  {
    my ($cmd, $args) = split(/ /, $line, 2);
    $args = $__PY_BOND_JSON->decode($args) if(defined($args));

    my $ret = undef;
    my $err = undef;
    if($cmd eq "EVAL" or $cmd eq "EVAL_BLOCK")
    {
      no strict;
      no warnings;

      # NOTE: force evaluation in array context to avoid swallowing lists
      $ret = [eval($args)];
      $ret = $ret->[0] if @$ret == 1;
      $err = $@;
    }
    elsif($cmd eq "EXPORT")
    {
      my $code = "sub $args { __PY_BOND_remote('$args', \\\@_); }";
      $ret = eval($code);
    }
    elsif($cmd eq "CALL")
    {
      no strict 'refs';
      my $name = $args->[0];

      # NOTE: note that we use "dump" to evaluate the command as a pure string.
      #       This allows us to execute *most* perl special forms consistenly.
      # TODO: special-case builtins to allow transparent invocation and higher
      #       performance with regular functions.
      my @args = @{$args->[1]};
      my $args_ = dump(@args);
      $args_ = "($args_)" if(@args == 1);
      $ret = [eval($name . ' ' . $args_)];
      $ret = $ret->[0] if @$ret == 1;
      $err = $@;
    }
    elsif($cmd eq "RETURN")
    {
      return $args;
    }
    else
    {
      exit(1);
    }

    # redirected output
    if(tell($__PY_BOND_BUFFER))
    {
      my $output = ${$__PY_BOND_BUFFER->string_ref};
      my $enc_out = $__PY_BOND_JSON->encode(["STDOUT", $output]);
      __PY_BOND_sendline("OUTPUT $enc_out");
      truncate($__PY_BOND_BUFFER, 0);
    }

    # error state
    my $state;
    if(!$err) {
      $state = "RETURN";
    }
    else
    {
      $state = "ERROR";
      $ret = $err;
    }

    my $enc_ret = $__PY_BOND_JSON->encode($ret);
    __PY_BOND_sendline("$state $enc_ret");
  }
  exit(0);
}

sub __PY_BOND_start()
{
  *STDIN = IO::Handle->new();
  *STDOUT = $__PY_BOND_BUFFER;
  select($__PY_BOND_BUFFER);

  __PY_BOND_sendline("READY");
  exit(__PY_BOND_repl());
}
