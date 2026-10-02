"""Private-driver regression checks; not a substitute for real database tests."""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools import database_live_gate as driver


class PrivateDriverTests(unittest.TestCase):
    def test_live_intent_is_sealed_before_container_dispatch(self):
        events=[];artifacts={}
        def seal(path,payload):
            events.append('receipt' if path.name.startswith('receipt-') else 'intent')
            artifacts[path]=payload
        def read(path):
            return {'api_password':'a'*40,'worker_password':'b'*40} if path.name=='runtime-credentials.dpapi' else artifacts[path]
        def dispatch(command,**kwargs):
            events.append('dispatch')
            self.assertIn('--journal',command)
            for value in ('a'*40,'b'*40):self.assertNotIn(value,' '.join(command))
            return type('Result',(),{'returncode':0,'stdout':b'{"failed":false,"cleanup":{}}'})()
        with patch.object(driver,'validate_snapshot'),patch.object(driver,'secure_directory'), \
             patch.object(driver.gate,'verify_target',return_value={'Id':'synthetic'}), \
             patch.object(driver.gate,'load_plan',return_value={}), \
             patch.object(driver.gate,'preflight',return_value={'state':'complete'}), \
             patch.object(driver.gate,'psql'),patch.object(driver,'sealed_write',side_effect=seal), \
             patch.object(driver,'read_sealed',side_effect=read), \
             patch.object(driver.subprocess,'run',side_effect=dispatch):
            result=driver.live('docker',Path('private'),'image')
        self.assertEqual(events,['intent','dispatch','receipt'])
        intent=next(v for k,v in artifacts.items() if k.name.startswith('journal-'))
        self.assertNotIn(intent['nonce'],Path(result['journal_path']).name)

    def test_journal_persistence_failure_prevents_dispatch(self):
        with patch.object(driver,'validate_snapshot'),patch.object(driver,'secure_directory'), \
             patch.object(driver.gate,'verify_target',return_value={'Id':'synthetic'}), \
             patch.object(driver.gate,'load_plan',return_value={}), \
             patch.object(driver.gate,'preflight',return_value={'state':'complete'}), \
             patch.object(driver.gate,'psql'), \
             patch.object(driver,'sealed_write',side_effect=driver.gate.GateError('Synthetic disk failure')), \
             patch.object(driver.subprocess,'run') as dispatch:
            with self.assertRaises(driver.gate.GateError):driver.live('docker',Path('private'),'image')
            dispatch.assert_not_called()

    @unittest.skipUnless(sys.platform=='win32','Windows CurrentUser DPAPI')
    def test_dpapi_roundtrip_and_tampering(self):
        plain=b'nonsecret regression payload'
        sealed=driver.dpapi(plain)
        self.assertNotIn(plain,sealed)
        self.assertEqual(driver.dpapi(sealed,decrypt=True),plain)
        with self.assertRaises(driver.gate.GateError):
            driver.dpapi(sealed[:-1]+bytes([sealed[-1]^1]),decrypt=True)

    def test_missing_authorization_refuses_before_any_operation(self):
        with patch.object(sys,'argv',['driver','--docker','unused','--phase','snapshot']), \
             patch.object(driver,'snapshot') as operation:
            self.assertEqual(driver.main(),2)
            operation.assert_not_called()

    def test_documented_runner_keeps_credentials_out_of_arguments(self):
        credentials={'api_password':'a'*40,'worker_password':'b'*40}
        result=type('Result',(),{'returncode':0,'stdout':json.dumps({'success':True}).encode()})()
        with patch.object(driver.subprocess,'run',return_value=result) as called:
            self.assertEqual(driver.documented_runner('docker','bootstrap',credentials)['exit_code'],0)
        command=called.call_args.args[0]
        self.assertIn('--authorize-local-write',command)
        for value in credentials.values():self.assertNotIn(value,' '.join(command))
        self.assertEqual(called.call_args.kwargs['input'],b'a'*40+b'\n'+b'b'*40+b'\n')
        self.assertTrue(called.call_args.kwargs['capture_output'])

    def test_target_drift_blocks_snapshot_use(self):
        with patch.object(driver,'read_sealed',return_value={'project':'other'}), \
             patch.object(driver.gate,'verify_target',return_value={}), \
             patch.object(driver,'restore_readability') as restore:
            with self.assertRaises(driver.gate.GateError):
                driver.validate_snapshot('docker',Path('unused'))
            restore.assert_not_called()


if __name__=='__main__':unittest.main()
