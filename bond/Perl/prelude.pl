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
  #$json = json_encode(array($name, $args));
  #__PY_BOND_sendline("REMOTE $json");
  #return __PY_BOND_repl();
}

sub __PY_BOND_repl()
{
  my $json = JSON->new();
  $json->allow_nonref();

  while(my $line = __PY_BOND_getline())
  {
    my ($cmd, $args) = split(/ /, $line, 2);
    $args = $json->decode($args) if(defined($args));

    my $ret = undef;
    my $err = undef;
    if($cmd eq "EVAL" or $cmd eq "EVAL_BLOCK")
    {
      no strict;
      no warnings;
      $ret = eval($args);
      $err = $@;
    }
    elsif($cmd eq "EXPORT")
    {
      # $code = "function $args() { return __PY_BOND_remote('$args', func_get_args()); }";
      # $ret = eval($code);
    }
    elsif($cmd eq "CALL")
    {
      no strict 'refs';
      my $name = $args->[0];

      # NOTE: note that we use "dump" to evaluate the command as a pure string.
      #       This allows us to execute *some* perl special forms consistenly.
      # TODO: special-case builtins to allow transparent invocation and higher
      #       performance with regular functions.
      my @args = @{$args->[1]};
      my $args_ = dump(@args);
      $args_ = "($args_)" if(@args == 1);
      $ret = eval($name . $args_);
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
      my $enc_out = $json->encode(${$__PY_BOND_BUFFER->string_ref});
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

    my $enc_ret = $json->encode($ret);
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

#__PY_BOND_start();
