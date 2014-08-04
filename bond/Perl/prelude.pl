# python-bond Perl interface setup
# NOTE: use # for comments only, as this code is transformed into a single
#       line to be injected into the interpreter *without parsing*.
use strict;
use warnings;
use IO::Handle;
use IO::String;
use JSON;
use Data::Dump qw{dump};


# Channels and buffers
my %__PY_BOND_BUFFERS =
(
  "STDOUT" => IO::String->new(),
  "STDERR" => IO::String->new()
);

my %__PY_BOND_CHANNELS =
(
  "STDIN" => *STDIN,
  "STDOUT" => *STDOUT,
  "STDERR" => *STDERR
);


# Serialization methods
my $__PY_BOND_JSON = JSON->new();
$__PY_BOND_JSON->allow_nonref();

sub __PY_BOND_dumps
{
  return $__PY_BOND_JSON->encode(@_);
}

sub __PY_BOND_loads
{
  return $__PY_BOND_JSON->decode(@_);
}


# Define our own i/o methods
sub __PY_BOND_getline()
{
  my $stdin = $__PY_BOND_CHANNELS{STDIN};
  my $line = <$stdin>;
  chomp($line) if(defined($line));
  return $line;
}

sub __PY_BOND_sendline
{
  my $line = shift // "";
  my $stdout = $__PY_BOND_CHANNELS{STDOUT};
  print $stdout "$line\n";
  $stdout->flush();
}


# Recursive repl
my $__PY_BOND_TRANS_EXCEPT;

sub __PY_BOND_sendstate($$)
{
  my ($state, $data) = @_;
  my $enc_ret = eval { __PY_BOND_dumps($data); };
  if($@)
  {
    $state = "ERROR";
    $enc_ret = __PY_BOND_dumps("cannot encode $data");
  }
  __PY_BOND_sendline("$state $enc_ret");
}

sub __PY_BOND_call($$)
{
  my ($name, $args) = @_;
  __PY_BOND_sendstate("CALL", [$name, $args]);
  return __PY_BOND_repl();
}

sub __PY_BOND_repl()
{
  while(my $line = __PY_BOND_getline())
  {
    my ($cmd, $args) = split(/ /, $line, 2);
    $args = __PY_BOND_loads($args) if(defined($args));

    my $ret = undef;
    my $err = undef;
    if($cmd eq "EVAL")
    {
      no strict;
      no warnings;

      # NOTE: force evaluation in array context to avoid swallowing lists
      $ret = [eval($args)];
      $err = $@;
      $ret = $ret->[0] if @$ret == 1;
    }
    elsif($cmd eq "EVAL_BLOCK")
    {
      no strict;
      no warnings;

      # NOTE: discard return, as with Perl it would most likely be a CODE ref
      eval($args);
      $err = $@;
    }
    elsif($cmd eq "EXPORT")
    {
      my $code = "sub $args { __PY_BOND_call('$args', \\\@_); }";
      $ret = eval($code);
      $err = $@;
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
      $err = $@;
      $ret = $ret->[0] if @$ret == 1;
    }
    elsif($cmd eq "RETURN")
    {
      return $args;
    }
    elsif($cmd eq "EXCEPT" or $cmd eq "ERROR")
    {
      die($args);
    }
    else
    {
      exit(1);
    }

    # redirected channels
    while(my ($channel, $buffer) = each %__PY_BOND_BUFFERS)
    {
      if(tell($buffer))
      {
	my $output = ${$buffer->string_ref};
	my $enc_out = __PY_BOND_dumps([$channel, $output]);
	__PY_BOND_sendline("OUTPUT $enc_out");
	seek($buffer, 0, 0);
	truncate($buffer, 0);
      }
    }

    # error state
    my $state;
    if(!$err) {
      $state = "RETURN";
    }
    else
    {
      $state = "EXCEPT";
      $ret = ($__PY_BOND_TRANS_EXCEPT? $err: "$err");
    }

    __PY_BOND_sendstate($state, $ret);
  }
  return 0;
}

sub __PY_BOND_start($)
{
  my $trans_except = shift();

  *STDIN = IO::Handle->new();
  *STDOUT = $__PY_BOND_BUFFERS{STDOUT};
  *STDERR = $__PY_BOND_BUFFERS{STDERR};
  $SIG{__WARN__} = sub
  {
    print STDERR shift();
  };

  $__PY_BOND_TRANS_EXCEPT = $trans_except;
  __PY_BOND_sendline("READY");
  exit(__PY_BOND_repl());
}
