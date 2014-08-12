# PICKLE protocol
try:
    import cPickle as pickle
except ImportError:
    import pickle

class PICKLE(object):
    @staticmethod
    def dumps(*args):
        return repr(pickle.dumps(args, 0)).encode('utf-8')

    @staticmethod
    def loads(buf):
        dec = eval(buf.decode('utf-8'))
        if not isinstance(dec, bytes): dec = dec.encode('utf-8')
        return pickle.loads(dec)[0]


# JSON protocol
import json

class JSON(object):
    @staticmethod
    def loads(buf):
        return json.loads(buf.decode('utf-8'))

    @staticmethod
    def dumps(*args):
        return json.dumps(*args, skipkeys=False).encode('utf-8')
