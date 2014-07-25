from abc import ABCMeta, abstractmethod


class bond(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def eval(self, code):
        '''Evaluate "code" inside the interpreter'''
        pass

    @abstractmethod
    def eval_block(self, code):
        '''Evaluate "code" inside the interpreter, within an anonymous block'''
        pass

    @abstractmethod
    def close(self):
        '''Terminate the underlying interpreter'''
        pass

    @abstractmethod
    def call(self, name, *args):
        '''Call a function "name" using *args'''
        pass

    @abstractmethod
    def export(self, func, name):
        '''Export a local function "func" to be callable in the interpreter as "name"'''
        pass

    def callable(self, name):
        '''Return a function calling "name"'''
        return lambda *args: self.call(name, *args)
