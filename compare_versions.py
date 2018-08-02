"""
Compare public functions of 2 RedisDict versions.
The versions are named "v1" and "v2". They are merely symbolic and do not point to a specific tag/branch..

How it works:
- prepare closure with function(s) to call on a RedisDict object
- execute with v1 instance, record any result/exception and final state of redis keys/values
- execute with v2 instance, record any result/exception and final state of redis keys/values
- assert that v2's API is consistent with v1 and that it behaves the same. So if v1 raises an 
  exception, v2 should do the same.
"""
import importlib
import os
import sys
import time
import unittest

from deepdiff import DeepDiff as ddiff
import redis

# Import the versions of RedisDict to test
rd_v1, rd_v2 = os.environ['V1'], os.environ['V2']
importlib.import_module('.redis_dict', rd_v1)
importlib.import_module('.redis_dict', rd_v2)

RedisDictV1 = sys.modules['{}.redis_dict'.format(rd_v1)].RedisDict
RedisDictV2 = sys.modules['{}.redis_dict'.format(rd_v2)].RedisDict

redis_config = {'host': '127.0.0.1'}
diff_view = 'tree'  # set to 'text' for more details


def requireFunctions(*functions):
    """Decorator to silently skip a test if RedisDict v1 does not have all
    the required functions. Prevents unittest errors when testing an older v1."""
    def decorator(testcase):
        def wrapper(self, *args, **kwargs):
            if any([not hasattr(self.d1, func) for func in functions]):
                self.skipTest("Base version doesn't have all required functions: {}".format(functions))
            else:
                testcase(self, *args, **kwargs)
        return wrapper
    return decorator


class TestRedisDictAPI(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.d1 = RedisDictV1(namespace='rd_compare_v1', **redis_config)
        cls.d2 = RedisDictV2(namespace='rd_compare_v2', **redis_config)
        cls.redisdb = redis.StrictRedis(**redis_config)
        cls.clear_test_namespace()

    @classmethod
    def clear_test_namespace(cls):
        with cls.redisdb.pipeline():
            for key in cls.redisdb.scan_iter('rd_compare_*'):
                cls.redisdb.delete(key)

    def tearDown(self):
        self.clear_test_namespace()

    def run_closure(self, closure, rd):
        """Takes a function and RedisDict instance
        Executes the function with rd as parameter
        Capture output/exception, redis state
        """
        result = exc = redis_state = None
        try:
            result = closure(rd)
        except Exception as e:
            # TODO just pass exception object when deepdiff issue is resolved https://github.com/seperman/deepdiff/issues/109
            exc = {'object': e, 'message': e.message}
        finally:
            redis_state = rd.to_dict()
            # Quick sanity check for RedisDict.to_dict
            to_rm = len(rd.namespace.split(':')[0]) + 1
            raw_keys = [key[to_rm:] for key in self.redisdb.scan_iter('{}*'.format(rd.namespace))]
            self.assertEqual(sorted(raw_keys), sorted(redis_state.keys()))  
            # Cleanup
            self.clear_test_namespace()
        return {'result': result, 'exception': exc, 'state': redis_state}
    
    def test_set_key(self):

        def set_key(rd):
            rd['foo'] = 'bar'

        output_d1 = self.run_closure(set_key, self.d1)
        output_d2 = self.run_closure(set_key, self.d2)
        diff = ddiff(output_d1, output_d2, view=diff_view)
        self.assertEqual(diff, {})

    def test_set_and_get_key(self):

        def set_and_get_key(rd):
            rd['foo'] = 'bar'
            return rd['foo']

        output_d1 = self.run_closure(set_and_get_key, self.d1)
        output_d2 = self.run_closure(set_and_get_key, self.d2)
        diff = ddiff(output_d1, output_d2, view=diff_view)
        self.assertEqual(diff, {})

    def test_set_and_get_key_integer(self):

        def set_and_get_key_integer(rd):
            rd['foo'] = 1234
            return rd['foo']

        output_d1 = self.run_closure(set_and_get_key_integer, self.d1)
        output_d2 = self.run_closure(set_and_get_key_integer, self.d2)
        diff = ddiff(output_d1, output_d2, view=diff_view)
        self.assertEqual(diff, {})

    def test_get_keyerror(self):

        def get_keyerror(rd):
            return rd['foo']

        output_d1 = self.run_closure(get_keyerror, self.d1)
        output_d2 = self.run_closure(get_keyerror, self.d2)
        diff = ddiff(output_d1, output_d2, view=diff_view)
        self.assertEqual(diff, {})

    def test_del_keyerror(self):

        def del_keyerror(rd):
            del rd['foo']

        output_d1 = self.run_closure(del_keyerror, self.d1)
        output_d2 = self.run_closure(del_keyerror, self.d2)
        diff = ddiff(output_d1, output_d2, view=diff_view)
        self.assertEqual(diff, {})

    @requireFunctions('multi_get')
    def test_set_and_mget(self):

        def set_and_mget(rd):
            rd['foo1'] = 'bar'
            rd['foo2'] = 'baz'
            return rd.multi_get('foo')

        output_d1 = self.run_closure(set_and_mget, self.d1)
        #print 'set_and_mget output_d1',output_d1
        output_d2 = self.run_closure(set_and_mget, self.d2)
        diff = ddiff(output_d1, output_d2, view=diff_view)
        self.assertEqual(diff, {})

    @requireFunctions('chain_set')
    def test_chain_set(self):

        def chain_set(rd):
            return rd.chain_set(['layer1', 'layer2'], 'melons')

        output_d1 = self.run_closure(chain_set, self.d1)
        output_d2 = self.run_closure(chain_set, self.d2)
        diff = ddiff(output_d1, output_d2, view=diff_view)
        self.assertEqual(diff, {})

    @requireFunctions('chain_set', 'chain_get')
    def test_chain_set_and_get(self):

        def chain_set_and_get(rd):
            rd.chain_set(['layer1', 'layer2'], 'melons')
            return rd.chain_get(['layer1', 'layer2'])

        output_d1 = self.run_closure(chain_set_and_get, self.d1)
        #print 'test_chain_set_and_get output_d1', output_d1
        output_d2 = self.run_closure(chain_set_and_get, self.d2)
        diff = ddiff(output_d1, output_d2, view=diff_view)
        self.assertEqual(diff, {})

    @requireFunctions('chain_del')
    def test_chain_del(self):

        def chain_del(rd):
            return rd.chain_del(['layer1', 'layer2'])

        output_d1 = self.run_closure(chain_del, self.d1)
        output_d2 = self.run_closure(chain_del, self.d2)
        diff = ddiff(output_d1, output_d2, view=diff_view)
        self.assertEqual(diff, {})

    @requireFunctions('chain_set', 'chain_del')
    def test_chain_set_and_del(self):

        def chain_del(rd):
            rd.chain_set(['layer1', 'layer2'], 'melons')
            return rd.chain_del(['layer1', 'layer2'])
 
        output_d1 = self.run_closure(chain_del, self.d1)
        output_d2 = self.run_closure(chain_del, self.d2)
        diff = ddiff(output_d1, output_d2, view=diff_view)
        self.assertEqual(diff, {})

    @requireFunctions('keys')
    def test_keys(self):

        def keys(rd):
            rd['foo'] = 'bar'
            rd['john'] = 'doe'
            return rd.keys()

        output_d1 = self.run_closure(keys, self.d1)
        output_d2 = self.run_closure(keys, self.d2)
        diff = ddiff(output_d1, output_d2, view=diff_view)
        self.assertEqual(diff, {})

    @requireFunctions('keys')
    def test_many_keys(self):

        def many_keys(rd):
            for i in range(100):
                rd[str(i)] = i
            return sorted(rd.keys())

        output_d1 = self.run_closure(many_keys, self.d1)
        output_d2 = self.run_closure(many_keys, self.d2)
        diff = ddiff(output_d1, output_d2, view=diff_view)
        self.assertEqual(diff, {})


if __name__ == '__main__':
    unittest.main()
