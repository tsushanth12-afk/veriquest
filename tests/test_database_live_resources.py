"""Production resource-plan/recovery/telemetry checks; live proof is separate."""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import AsyncMock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools import database_live_resources as resource


class ResourcePlanTests(unittest.TestCase):
    def setUp(self):
        self.target={'Id':'synthetic-target'};self.manifest={'synthetic':True}
        self.plan=resource.new_plan(self.target,self.manifest)

    def test_fresh_intent_has_exact_natural_keys_and_distinct_ids(self):
        resource.validate_plan(self.plan,self.target,self.manifest)
        other=resource.new_plan(self.target,self.manifest)
        self.assertNotEqual(self.plan['emails'],other['emails'])
        self.assertEqual(len(set(sum([self.plan[k] for k in ('quests','badges','xp','awards','streaks')],[]))),11)

    def test_drift_and_broad_keys_refused(self):
        for key,value in [('container_id','other'),('emails',['vq%']),('slugs',['permission-%']),
                          ('nonce','not-a-nonce'),('quests',[self.plan['badges'][0]]*2)]:
            bad=copy.deepcopy(self.plan);bad[key]=value
            with self.assertRaises(resource.gate.GateError):resource.validate_plan(bad,self.target,self.manifest)


class NativeHelperTests(unittest.IsolatedAsyncioTestCase):
    async def test_timing_never_records_sql_values_or_exception_messages(self):
        conn=AsyncMock();conn.execute.side_effect=TimeoutError('synthetic-private-value')
        report={};timed=resource.TimedConnection(conn,report,'fixture_operator')
        with self.assertRaises(TimeoutError):
            await timed.execute("UPDATE public.profiles SET bio='synthetic-private-value'")
        self.assertNotIn('synthetic-private-value',json.dumps(report))
        self.assertEqual(next(iter(report['sql_timings'].values()))['errors'],{'TimeoutError':1})

    async def test_bounds_are_session_only_and_decrease_statement_timeout(self):
        conn=AsyncMock();await resource.bounded(conn)
        sql=conn.execute.call_args.args[0]
        self.assertIn("statement_timeout='10s'",sql)
        self.assertIn("lock_timeout='1500ms'",sql)
        self.assertNotIn('ALTER',sql)

    async def test_marker_mismatch_prevents_cleanup_sql(self):
        plan=resource.new_plan({'Id':'synthetic'},{})
        conn=AsyncMock();conn.fetch.return_value=[{'id':'unused','email':plan['emails'][0],'raw_user_meta_data':{'vq_gate_run':'other'}}]
        with self.assertRaises(resource.gate.GateError):await resource.resolve(conn,plan)
        conn.execute.assert_not_called()

    async def test_unused_intent_refuses_collision_before_creation(self):
        plan=resource.new_plan({'Id':'synthetic'},{})
        conn=AsyncMock();conn.fetch.return_value=[];conn.fetchval.return_value=1
        with self.assertRaises(resource.gate.GateError):await resource.assert_unused(conn,plan)
        conn.execute.assert_not_called()

    async def test_external_reference_guard_refuses_without_mutation(self):
        plan=resource.new_plan({'Id':'synthetic'},{})
        conn=AsyncMock();conn.fetchval.return_value=1
        with self.assertRaises(resource.gate.GateError):
            await resource.reject_external_references(conn,[],[],plan)
        conn.execute.assert_not_called()


if __name__=='__main__':unittest.main()
