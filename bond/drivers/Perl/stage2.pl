# python-bond Perl interface setup
use strict;
use warnings;
require IO::Handle;
require IO::String;
require JSON;
require Data::Dump;
require Scalar::Util;


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


# Our minimal exception signature
{
  package _PY_BOND_SerializationException;

  use overload '""' => sub { __PACKAGE__ . ': ' . ${shift()} . '\n' };

  sub new
  {
    my ($self, $message) = @_;
    return bless \$message, $self;
  }
}


# Serialization methods
my $__PY_BOND_JSON = JSON->new()->allow_nonref();

sub __PY_BOND_dumps
{
  my $data = shift;
  my $code = eval { $__PY_BOND_JSON->encode($data) };
  die _PY_BOND_SerializationException->new("cannot encode $data") if $@;
  return $code;
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
  chomp($line) if defined($line);
  return $line;
}

sub __PY_BOND_sendline
{
  my $line = shift // "";
  my $stdout = $__PY_BOND_CHANNELS{STDOUT};
  print $stdout "$line\n";
}


# Recursive repl
my $__PY_BOND_TRANS_EXCEPT;

sub __PY_BOND_call($$)
{
  my ($name, $args) = @_;
  my $code = __PY_BOND_dumps([$name, $args]);
  __PY_BOND_sendline("CALL $code");
  return __PY_BOND_repl();
}

sub __PY_BOND_repl()
{
  my $SENTINEL = 1;
  while(my $line = __PY_BOND_getline())
  {
    my ($cmd, $args) = split(/ /, $line, 2);
    $args = __PY_BOND_loads($args) if defined($args);

    my $ret = undef;
    my $err = undef;
    if($cmd eq "EVAL")
    {
      no strict;
      no warnings;

      # NOTE: force evaluation in array context to avoid swallowing lists
      $ret = [eval $args];
      $err = $@;
      $ret = $ret->[0] if @$ret == 1;
    }
    elsif($cmd eq "EVAL_BLOCK")
    {
      no strict;
      no warnings;

      # NOTE: discard return, as with Perl it would most likely be a CODE ref
      eval $args;
      $err = $@;
    }
    elsif($cmd eq "EXPORT")
    {
      my $code = "sub $args { __PY_BOND_call('$args', \\\@_) }";
      $ret = eval $code;
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
      my $args_ = Data::Dump::dump(@args);
      $args_ = "($args_)" if @args == 1;
      $ret = [eval ($name . ' ' . $args_)];
      $err = $@;
      $ret = $ret->[0] if @$ret == 1;
    }
    elsif($cmd eq "RETURN")
    {
      return $args;
    }
    elsif($cmd eq "EXCEPT")
    {
      die $args;
    }
    elsif($cmd eq "ERROR")
    {
      die _PY_BOND_SerializationException->new($args);
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
	my $code = __PY_BOND_dumps([$channel, $output]);
	__PY_BOND_sendline("OUTPUT $code");
	seek($buffer, 0, 0);
	truncate($buffer, 0);
      }
    }

    # error state
    my $state = "RETURN";
    if($err)
    {
      if(Scalar::Util::blessed($err) && $err->isa('_PY_BOND_SerializationException'))
      {
	$state = "ERROR";
	$ret = $$err;
      }
      else
      {
	$state = "EXCEPT";
	$ret = ($__PY_BOND_TRANS_EXCEPT? $err: "$err");
      }
    }
    my $code = eval { __PY_BOND_dumps($ret) };
    if($@)
    {
      $state = "ERROR";
      $code = __PY_BOND_dumps(${$@});
    }
    __PY_BOND_sendline("$state $code");
  }
  return 0;
}

sub __PY_BOND_start($$)
{
  my ($proto, $trans_except) = @_;

  *STDIN = IO::Handle->new();
  *STDOUT = $__PY_BOND_BUFFERS{STDOUT};
  *STDERR = $__PY_BOND_BUFFERS{STDERR};
  $SIG{__WARN__} = sub
  {
    print STDERR shift;
  };

  $__PY_BOND_TRANS_EXCEPT = $trans_except;
  __PY_BOND_sendline("READY");
  my $ret = __PY_BOND_repl();
  __PY_BOND_sendline("BYE");
  exit($ret);
}
