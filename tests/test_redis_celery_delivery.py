"""No live writes: production harness protocol/intent and credential-boundary checks."""
import base64
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch, Mock
from uuid import uuid4

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools import database_gate as gate
from tools import database_live_resources as resources
from tools.redis_celery_delivery import decode_message, validate_intent, DeliveryGate, CHECKS


class DeliveryTests(unittest.TestCase):
    def message(self):
        return {'headers':{'id':str(uuid4()),'task':'execute_hdl_submission'},
                'body':base64.b64encode(json.dumps([['row'],{},{}]).encode()).decode(),
                'properties':{'delivery_info':{'routing_key':'hdl_execution'}}}

    def test_actual_envelope_parser(self):
        m=self.message()
        self.assertEqual(decode_message(json.dumps(m),'execute_hdl_submission',['row'])['task_id'],m['headers']['id'])

    def test_incompatible_envelopes_rejected(self):
        for field in ('task','queue','args','id','base64'):
            m=self.message()
            if field=='task':m['headers']['task']='other'
            if field=='queue':m['properties']['delivery_info']['routing_key']='other'
            if field=='args':m['body']=base64.b64encode(b'[["other"],{},{}]').decode()
            if field=='id':m['headers']['id']='not-uuid'
            if field=='base64':m['body']='!'
            with self.subTest(field=field),self.assertRaises((gate.GateError,ValueError)):
                decode_message(json.dumps(m),'execute_hdl_submission',['row'])

    def test_intent_is_exact_and_target_bound(self):
        target={'Id':'current'}; manifest=gate.load_plan(); plan=resources.new_plan(target,manifest); n=plan['nonce']
        intent={'format':1,'resources':plan,
                'names':{k:'vq-delivery-'+k+'-'+n for k in ('redis','api','worker','probe','network')},
                'tags':{k:'vq-delivery-'+k+':'+n for k in ('api','worker')},
                'checks':{k:'vq-delivery-'+k+'-'+n for k in CHECKS},
                'idempotency_keys':['delivery-'+n+'-'+str(i) for i in range(3)]}
        validate_intent(intent,target,manifest)
        for key in ('names','tags','idempotency_keys'):
            changed=json.loads(json.dumps(intent)); changed[key]={} if key!='idempotency_keys' else []
            with self.assertRaises(gate.GateError):validate_intent(changed,target,manifest)
        with self.assertRaises(gate.GateError):validate_intent(intent,{'Id':'old'},manifest)

    def test_failed_assertion_is_not_success(self):
        runner=DeliveryGate('not-executed',Path('.'))
        with self.assertRaises(gate.GateError):runner.check(False,'negative regression')
        self.assertEqual(runner.report['assertions'],0)

    def test_sealed_intent_is_read_back_before_becoming_writable(self):
        runner=DeliveryGate('not-executed',Path('.')); saved={}; target={'Id':'current'}
        def seal(path,payload):
            self.assertIsNone(runner.intent)
            saved.update(payload)
        with patch('tools.redis_celery_delivery.private.sealed_write',side_effect=seal), \
             patch('tools.redis_celery_delivery.private.read_sealed',side_effect=lambda p:saved):
            runner.new_intent(target,gate.load_plan())
        self.assertEqual(runner.intent,saved)

    def test_persistence_failure_does_not_release_writes(self):
        runner=DeliveryGate('not-executed',Path('.'))
        with patch('tools.redis_celery_delivery.private.sealed_write',side_effect=OSError('disk failure')):
            with self.assertRaises(OSError):runner.new_intent({'Id':'current'},gate.load_plan())
        self.assertIsNone(runner.intent)

    def test_inspection_outage_is_not_resource_absence(self):
        runner=DeliveryGate('not-executed',Path('.'))
        runner.call=Mock(return_value=Mock(returncode=1,stderr=b'Cannot connect to Docker daemon'))
        with self.assertRaises(gate.GateError):runner.inspect('exact-resource')

    def test_inspection_reports_exact_missing_object(self):
        runner=DeliveryGate('not-executed',Path('.'))
        runner.call=Mock(return_value=Mock(returncode=1,stderr=b'Error: No such object: exact-resource'))
        self.assertIsNone(runner.inspect('exact-resource'))


if __name__=='__main__':unittest.main(verbosity=2)
