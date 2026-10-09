"""Focused actual harness/helper regressions; no live resources or accounts."""
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch,Mock
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tools.queued_native_grading import QueuedGate,validate_intent,observations,worker_capabilities_valid,monitored_publication
from tools import database_gate as gate,database_live_resources as resources


class QueuedTests(unittest.TestCase):
    def test_exact_intent_and_reward(self):
        runner=QueuedGate('unused',ROOT);target={'Id':'current'};manifest=gate.load_plan();saved={}
        def seal(path,data):
            self.assertIsNone(runner.intent);saved.update(data)
        with patch.object(runner,'inspect',return_value=None),patch('tools.queued_native_grading.private.sealed_write',side_effect=seal),patch('tools.queued_native_grading.private.read_sealed',side_effect=lambda p:saved):
            runner.new_intent(target,manifest)
        validate_intent(saved,target,manifest)
        for key,bad in [('reward',0),('reward',2),('names',{}),('tags',{}),('keys',[]),('redis_base_present',1)]:
            changed=json.loads(json.dumps(saved));changed[key]=bad
            with self.subTest(key=key),self.assertRaises(gate.GateError):validate_intent(changed,target,manifest)
        with self.assertRaises(gate.GateError):validate_intent(saved,{'Id':'other'},manifest)

    def test_journal_failure_never_releases_intent(self):
        runner=QueuedGate('unused',ROOT)
        with patch.object(runner,'inspect',return_value=None),patch('tools.queued_native_grading.private.sealed_write',side_effect=OSError('controlled failure')):
            with self.assertRaises(OSError):runner.new_intent({'Id':'current'},gate.load_plan())
        self.assertIsNone(runner.intent)

    def test_observer_metadata_parser(self):
        records=observations(b'ordinary worker text\nWARNING VQ_NATIVE_RESULT {"task_id":"t","exit_code":0}\n')
        self.assertEqual(records,[{'kind':'RESULT','task_id':'t','exit_code':0}])
        with self.assertRaises(ValueError):observations(b'VQ_NATIVE_RESULT {bad}')

    def test_observer_never_exports_output_or_nonce(self):
        spec=importlib.util.spec_from_file_location('passive_observer',ROOT/'tests/queued_native_observer.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        secret='b'*64
        raw={'resource_job':'a'*32,'stdout':'VQ_TRUSTED:'+secret+':ACCEPTED:4:4:0\nVERIQUEST_STATUS: ACCEPTED',
             'stderr':'private bench/source','verdict_nonce':secret,'exit_code':0,'failure_phase':'secret phase','rpc_events':[]}
        safe=module.safe_result(raw)
        self.assertNotIn(secret,json.dumps(safe));self.assertNotIn('private bench',json.dumps(safe))
        self.assertNotIn('secret phase',json.dumps(safe));self.assertEqual(safe['trusted_record_count'],1)
        self.assertTrue(safe['legacy_accepted_seen'])

    def test_negative_expectation_raises(self):
        with self.assertRaises(gate.GateError):QueuedGate('unused',ROOT).check(False,'failed assertion')

    def test_actual_capability_names_not_privilege_relaxation(self):
        self.assertTrue(worker_capabilities_valid({'CapDrop':['ALL'],'CapAdd':['CAP_CHOWN','CAP_FOWNER','CAP_DAC_OVERRIDE']}))
        self.assertTrue(worker_capabilities_valid({'CapDrop':['ALL'],'CapAdd':['CHOWN','FOWNER','DAC_OVERRIDE']}))
        self.assertFalse(worker_capabilities_valid({'CapDrop':['ALL'],'CapAdd':['CAP_SYS_ADMIN','CAP_CHOWN','CAP_FOWNER','CAP_DAC_OVERRIDE']}))
        self.assertFalse(worker_capabilities_valid({'CapDrop':[],'CapAdd':['CAP_CHOWN','CAP_FOWNER','CAP_DAC_OVERRIDE']}))

    def test_exact_volume_absence_not_transport_outage(self):
        runner=QueuedGate('unused',ROOT)
        runner.call=Mock(return_value=Mock(returncode=1,stderr=b'Error: get exact-volume: no such volume'))
        self.assertIsNone(runner.inspect('exact-volume','volume'))
        runner.call=Mock(return_value=Mock(returncode=1,stderr=b'Cannot connect to Docker daemon'))
        with self.assertRaises(gate.GateError):runner.inspect('exact-volume','volume')

    def test_real_monitor_quoting_without_queue_snapshot(self):
        wire=json.dumps({'headers':{'task':'execute_hdl_submission'},'body':'bounded'})
        line='1.00 [0 127.0.0.1:1] "LPUSH" "hdl_execution" '+json.dumps(wire)
        self.assertEqual(monitored_publication(line),wire)
        self.assertIsNone(monitored_publication('1.00 [0 local] "BRPOP" "hdl_execution" "1"'))
        self.assertIsNone(monitored_publication('1.00 [0 local] "LPUSH" "other_queue" "x"'))
        self.assertIsNone(monitored_publication(r'1.00 [0 local] "SADD" "_kombu.binding.hdl_execution" "hdl_execution\x06\x16"'))

    def test_consumed_message_still_calls_actual_wire_parser(self):
        import base64
        from uuid import uuid4
        runner=QueuedGate('unused',ROOT)
        tid=str(uuid4());sid=str(uuid4())
        runner.publications=[json.dumps({'headers':{'task':'execute_hdl_submission','id':tid},
            'body':base64.b64encode(json.dumps([[sid],{},{}]).encode()).decode(),
            'properties':{'delivery_info':{'routing_key':'hdl_execution'}}})]
        self.assertEqual(runner.message('execute_hdl_submission',[sid])['task_id'],tid)
        runner.publications.append(runner.publications[0])
        with self.assertRaises(gate.GateError):runner.message('execute_hdl_submission',['wrong row'])


if __name__=='__main__':unittest.main(verbosity=2)
