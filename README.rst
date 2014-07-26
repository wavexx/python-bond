===============================
 python ``bond`` / ``bond.PHP``
===============================
transparent remote/recursive evaluation between Python/PHP
----------------------------------------------------------

.. contents::

Ambivalent bonds between Python and other languages:

.. code:: python

  # Let's bond with a PHP interpreter
  from bond.PHP import PHP
  php = PHP()
  php.eval('echo "Hello world!\n";')
  >>> Hello world!

  # Make an expensive split function using PHP's explode
  split = php.callable('explode')
  split('=', "Mind=blown!")
  >>> [u'Mind', u'blown!']

  # Call Python from PHP
  def call_me():
      print("Hi, this is Python talking!")

  php.export(call_me, 'call_me')
  php.eval('call_me()')
  >>> Hi, this is Python talking!

  # Bridge two worlds!
  remote_php = PHP('ssh remote php -a')
  php.eval('function local_php() { echo "Hi from " . system("hostname") . "!"; }')
  php.proxy('local_php', remote_php)
  remote_php.eval('local_php();')
  >>> Hi from localhost!


Authors and Copyright
=====================

| "python-bond" is distributed under GPL2 (see COPYING) WITHOUT ANY WARRANTY.
| Copyright(c) 2014 by wave++ "Yuri D'Elia" <wavexx@thregr.org>.

python-bond's GIT repository is publicly accessible at::

  git://src.thregr.org/python-bond

or at `GitHub <https://github.com/wavexx/python-bond>`_.
