"""Native SQL permission cases for database_rehearsal.py (minimal Auth only).

Production static SQL is extracted from AST, prepared and executed unchanged.
No API/worker Python handlers, real JWTs, PostgREST or scoring algorithms run.
"""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
A = '10000000-0000-4000-8000-000000000001'
B = '10000000-0000-4000-8000-000000000002'
C = '10000000-0000-4000-8000-000000000003'
D = '10000000-0000-4000-8000-000000000004'
E = '10000000-0000-4000-8000-000000000005'
PUB = '20000000-0000-4000-8000-000000000001'
OTHER = '20000000-0000-4000-8000-000000000002'
DRAFT = '20000000-0000-4000-8000-000000000003'
ARCHIVED = '20000000-0000-4000-8000-000000000004'
JOB = '30000000-0000-4000-8000-000000000001'
JOB_B = '30000000-0000-4000-8000-000000000002'
QUEST = '40000000-0000-4000-8000-000000000001'
BADGE = '50000000-0000-4000-8000-000000000001'
API = 'vq_api'
WORKER = 'vq_worker'
CLIENT = 'rehearsal_student_a'


def production_query(path, function, contains):
    """Fail on source drift/ambiguity, instead of silently testing a copied query."""
    module = ast.parse((ROOT / path).read_text())
    functions = [n for n in ast.walk(module) if isinstance(n, (ast.AsyncFunctionDef, ast.FunctionDef))
                 and n.name == function]
    assert len(functions) == 1
    queries = [n.value.strip().rstrip(';') for n in ast.walk(functions[0])
               if isinstance(n, ast.Constant) and isinstance(n.value, str) and contains in n.value]
    assert len(queries) == 1, (path, function, contains)
    return queries[0]


def prepared(path, function, contains, arguments):
    query = production_query(path, function, contains)
    return 'PREPARE rehearsal_query AS ' + query + '; EXECUTE rehearsal_query(' + arguments + ');'


def snapshot(table):
    return "SELECT md5(coalesce(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text)::text,'[]')) FROM " + table + " t;"


def run_operations(sql):
    service = 'backend/app/submissions/service.py'
    admin = 'backend/app/admin/router.py'
    task = 'worker/tasks/hdl_task.py'
    xp = 'backend/app/gamification/xp.py'
    profiles = snapshot('public.profiles')
    progress = snapshot('public.user_challenge_progress')
    submissions = snapshot('public.submissions')
    challenges = snapshot('public.challenges')
    roles = snapshot('public.user_roles')
    ledger = snapshot('private.schema_migrations')
    secrets = snapshot('private.challenge_secrets')
    claim = "SET request.jwt.claim.sub='" + A + "';"

    # Real PG sessions for all roles; API/worker NOINHERIT logins remain unchanged.
    # Proxy client logins inherit only the real NOLOGIN Data API roles.
    sql("""CREATE ROLE rehearsal_student_a LOGIN INHERIT; GRANT authenticated TO rehearsal_student_a;
      CREATE ROLE rehearsal_student_b LOGIN INHERIT; GRANT authenticated TO rehearsal_student_b;
      CREATE ROLE rehearsal_anon LOGIN INHERIT; GRANT anon TO rehearsal_anon;""", label='stub client login proxies')
    for role in (API, WORKER, CLIENT, 'rehearsal_student_b', 'rehearsal_anon'):
        sql.equal('SELECT session_user=current_user AND current_user=\'' + role + '\';',
                  't', 'actual login identity: ' + role, role=role)

    sql(f"""INSERT INTO auth.users(id,email,raw_user_meta_data) VALUES
      ('{A}','same@invalid.test','{{"username":"collision","display_name":"  Learner A  ","role":"admin","xp":99999}}'),
      ('{B}','same@invalid.test','{{"username":"collision","display_name":17,"full_name":"Learner B"}}'),
      ('{C}','admin@invalid.test','{{}}'), ('{D}','empty@invalid.test','[]'),
      ('{E}','long@invalid.test',jsonb_build_object('display_name',repeat('x',150),'role','admin'));
      INSERT INTO public.user_roles(user_id,role) VALUES('{C}','admin');""", label='native stub signup trigger fixtures')
    sql.equal("""SELECT count(*)=5 AND bool_and(
      username='vq_user_'||replace(id::text,'-','') AND xp=0 AND level=1
      AND current_streak=0 AND longest_streak=0 AND total_solved=0
      AND easy_solved=0 AND medium_solved=0 AND hard_solved=0 AND total_attempts=0)
      FROM public.profiles;""", 't', 'signup protected defaults and unique UUID usernames')
    sql.equal(f"""SELECT
      (SELECT display_name='Learner A' FROM public.profiles WHERE id='{A}') AND
      (SELECT display_name='Learner B' FROM public.profiles WHERE id='{B}') AND
      (SELECT display_name='Student' FROM public.profiles WHERE id='{D}') AND
      (SELECT length(display_name)=100 FROM public.profiles WHERE id='{E}') AND
      (SELECT count(*)=5 FROM public.user_roles WHERE role='student') AND
      NOT EXISTS(SELECT 1 FROM public.user_roles WHERE user_id<>'{C}' AND role='admin');""",
      't', 'signup metadata cannot promote or score')
    sql('SELECT count(*) FROM public.profiles;', label='anonymous cannot read profiles', role='rehearsal_anon', error='42501')
    sql.equal(claim + 'SELECT count(*) FROM public.profiles;', '1', 'client own profile only', role=CLIENT)
    sql.equal("SET request.jwt.claim.sub='" + B + "'; SELECT count(*) FROM public.profiles;",
              '1', 'second client own profile only', role='rehearsal_student_b')
    sql.equal(claim + f"UPDATE public.profiles SET display_name='Allowed',bio='safe',avatar_url=NULL WHERE id='{A}' RETURNING display_name;",
              'Allowed', 'safe profile edit RETURNING and timestamp trigger', role=CLIENT)
    sql.equal(f"SELECT updated_at>created_at FROM public.profiles WHERE id='{A}';", 't', 'profile timestamp updated')
    sql.equal(claim + f"WITH changed AS (UPDATE public.profiles SET bio='intrusion' WHERE id='{B}' RETURNING id) SELECT count(*) FROM changed;",
              '0', 'other-user UPDATE RLS filters all rows', role=CLIENT)
    sql.equal(f"SELECT bio='' FROM public.profiles WHERE id='{B}';", 't', 'other-user display state unchanged')
    for column, value in (('xp','900'),('level','9'),('current_streak','9'),('longest_streak','9'),
                           ('total_solved','9'),('easy_solved','9'),('medium_solved','9'),
                           ('hard_solved','9'),('total_attempts','9'),('username',"'changed'"),
                           ('id',f"'{B}'")):
        sql.denied_unchanged(f"UPDATE public.profiles SET bio='mixed must rollback',{column}={value} WHERE id='{A}'",
                             profiles, 'client mixed protected ' + column, role=CLIENT, prefix=claim)
    sql.denied_unchanged(f"UPDATE public.profiles SET display_name=repeat('x',101) WHERE id='{A}'",
                         profiles, 'client display bound', role=CLIENT, error='23514', prefix=claim)
    sql.denied_unchanged(f"UPDATE public.profiles SET bio=repeat('x',2001) WHERE id='{A}'",
                         profiles, 'client bio bound', role=CLIENT, error='23514', prefix=claim)
    sql.denied_unchanged(f"UPDATE public.profiles SET avatar_url=repeat('x',2049) WHERE id='{A}'",
                         profiles, 'client avatar bound', role=CLIENT, error='23514', prefix=claim)
    sql.denied_unchanged(f"INSERT INTO public.profiles(id,username,display_name) VALUES('{A}','upsert','fake') ON CONFLICT(id) DO UPDATE SET display_name=excluded.display_name RETURNING id",
                         profiles, 'client profile ON CONFLICT denied', role=CLIENT, prefix=claim)
    sql.denied_unchanged(f"INSERT INTO public.user_roles(user_id,role) VALUES('{A}','admin')",
                         roles, 'client role escalation', role=CLIENT, prefix=claim)

    # Operator-owned fixture publication is NOT native grader validation.
    sql(f"""INSERT INTO public.challenges(id,slug,title,is_published,validation_status,is_archived) VALUES
      ('{PUB}','rehearsal-published','Published',true,'published',false),
      ('{OTHER}','rehearsal-other','Other published',true,'published',false),
      ('{DRAFT}','rehearsal-draft','Draft',false,'draft',false),
      ('{ARCHIVED}','rehearsal-archived','Archived',true,'published',true);
      INSERT INTO private.challenge_secrets(challenge_id,official_solution,hidden_testbench,private_notes)
        SELECT id,'synthetic solution','synthetic bench','operator notes' FROM public.challenges;
      INSERT INTO public.challenge_prerequisites(challenge_id,prerequisite_id) VALUES
        ('{PUB}','{OTHER}'),('{PUB}','{DRAFT}'),('{DRAFT}','{OTHER}'),('{PUB}','{ARCHIVED}');
      INSERT INTO public.quests(id,title,category) VALUES('{QUEST}','Rehearsal','Fundamentals');
      INSERT INTO public.quest_challenges(quest_id,challenge_id) SELECT '{QUEST}',id FROM public.challenges;
      INSERT INTO public.badges(id,name,rule_type,rule_config) VALUES('{BADGE}','Rehearsal','solved_count','{{"threshold":1}}');
      """, label='operator curriculum fixtures, not grading')
    for role in ('rehearsal_anon', CLIENT):
        sql.equal('SELECT count(*) FROM public.challenges;', '2', 'visible catalog: ' + role, role=role)
        sql.equal('SELECT count(*) FROM public.challenge_prerequisites;', '1', 'visible prerequisites: ' + role, role=role)
        sql.equal('SELECT count(*) FROM public.quest_challenges;', '2', 'visible quest links: ' + role, role=role)
        sql('SELECT hidden_testbench FROM private.challenge_secrets;', label='private read denied: ' + role, role=role, error='42501')
        sql('SELECT rule_config FROM public.badges;', label='private badge rule denied: ' + role, role=role, error='42501')
    sql(prepared(service,'create_submission','INSERT INTO public.submissions',
        f"'{JOB}','{A}','{PUB}','module stub; endmodule','idem-a',now()"),
        role=API, label='production API queued submission INSERT')
    sql(prepared(service,'create_submission','INSERT INTO public.submissions',
        f"'{JOB_B}','{B}','{PUB}','module stub; endmodule','idem-b',now()"),
        role=API, label='production API second-user submission INSERT')
    sql.equal(prepared(service,'create_submission','WHERE idempotency_key',
        f"'idem-a','{A}'"), JOB + '|queued', 'production API idempotent SELECT', role=API)
    upsert = prepared(service,'create_submission','INSERT INTO public.user_challenge_progress', f"'{A}','{PUB}'")
    sql(upsert, role=API, label='production API progress ON CONFLICT insert')
    sql(upsert, role=API, label='production API progress ON CONFLICT update')
    sql.equal(f"SELECT attempts||'|'||status FROM public.user_challenge_progress WHERE user_id='{A}' AND challenge_id='{PUB}';",
              '2|in_progress', 'API upsert attempts actually increment')
    sql.denied_unchanged(f"UPDATE public.user_challenge_progress SET status='completed',attempts=attempts+1 WHERE user_id='{A}' AND challenge_id='{PUB}'",
                         progress, 'API cannot forge completed progress', role=API, error='P0001', marker='Invalid API progress update')
    sql.denied_unchanged(f"INSERT INTO public.user_challenge_progress(user_id,challenge_id,status,attempts) VALUES('{B}','{PUB}','completed',1) ON CONFLICT(user_id,challenge_id) DO UPDATE SET status='completed'",
                         progress, 'API protected ON CONFLICT guard', role=API, error='P0001', marker='Invalid API progress insertion')
    sql.denied_unchanged(f"INSERT INTO public.submissions(id,user_id,challenge_id,status,submitted_code) VALUES('30000000-0000-4000-8000-000000000003','{A}','{PUB}','accepted','fake')",
                         submissions, 'API forged accepted INSERT RLS', role=API)
    sql.denied_unchanged(f"UPDATE public.submissions SET status='accepted' WHERE id='{JOB}'",
                         submissions, 'API forged accepted UPDATE RLS', role=API)
    sql.denied_unchanged(f"UPDATE public.submissions SET public_message='mixed',tests_passed=10,xp_awarded=999 WHERE id='{JOB}'",
                         submissions, 'API mixed protected result counts', role=API)
    sql.denied_unchanged(f"UPDATE public.profiles SET bio='mixed',xp=999 WHERE id='{A}'",
                         profiles, 'API protected profile score', role=API)
    sql.denied_unchanged(f"INSERT INTO public.xp_transactions(user_id,amount,reason) VALUES('{A}',999,'fake')",
                         snapshot('public.xp_transactions'), 'API cannot award XP', role=API)
    sql.denied_unchanged(f"UPDATE public.user_roles SET role='admin' WHERE user_id='{A}'",
                         roles, 'API cannot grant admin', role=API)
    sql.denied_unchanged(f"UPDATE public.submissions SET submitted_code='mutated' WHERE id='{JOB}'",
                         submissions, 'worker input immutability', role=WORKER)
    sql('SELECT private_notes FROM private.challenge_secrets;', label='worker notes denied', role=WORKER, error='42501')
    sql.denied_unchanged(f"UPDATE private.challenge_secrets SET hidden_testbench='tampered' WHERE challenge_id='{PUB}'",
                         secrets, 'worker evaluator immutable', role=WORKER)
    sql.denied_unchanged(f"UPDATE public.challenges SET is_published=true WHERE id='{DRAFT}'",
                         challenges, 'worker publication denied', role=WORKER)
    sql('SELECT role FROM public.user_roles;', label='worker role reads denied', role=WORKER, error='42501')
    sql('SELECT action FROM public.admin_audit_log;', label='worker audit reads denied', role=WORKER, error='42501')
    for role in (API, WORKER, CLIENT, 'rehearsal_anon'):
        sql.denied_unchanged("UPDATE private.schema_migrations SET sha256=repeat('0',64)", ledger,
                             'migration ledger denied: ' + role, role=role)
        sql('SET ROLE vq_owner;', label='owner escalation denied: ' + role, role=role, error='42501')
        sql('SELECT private.handle_new_user();', label='helper EXECUTE denied: ' + role, role=role, error='42501')
        sql.denied_unchanged('TRUNCATE public.profiles CASCADE', profiles, 'TRUNCATE denied: ' + role, role=role)
        sql.denied_unchanged(f"DELETE FROM public.profiles WHERE id='{A}'", profiles, 'DELETE denied: ' + role, role=role)

    # Actual production worker SQL: evidence/result writes and score permission
    # fixtures. No HDL execution or claim of accounting correctness.
    sql(prepared(task,'_execute_hdl_submission','SELECT s.id, s.user_id',
        f"'{JOB}'"), role=WORKER, label='production worker queued input JOIN')
    sql(prepared(task,'_execute_hdl_submission',"status = 'compiling'", f"'{JOB}','rehearsal-worker'"),
        role=WORKER, label='production worker compile stage')
    sql(prepared(task,'_execute_hdl_submission','SELECT official_solution, hidden_testbench',
        f"'{PUB}'"), role=WORKER, label='production worker evaluator read')
    sql(prepared(task,'_execute_hdl_submission',"status = 'running'", f"'{JOB}'"),
        role=WORKER, label='production worker simulation stage')
    sql(prepared(task,'_execute_hdl_submission','runtime_ms = $3',
        f"'{JOB}','accepted',10,100,4,4,0,NULL,'fixture','diagnostic'"),
        role=WORKER, label='production worker result write')
    sql(prepared(xp,'award_xp','INSERT INTO public.user_challenge_progress', f"'{A}','{PUB}'"),
        role=WORKER, label='production worker progress ON CONFLICT DO NOTHING')
    sql.equal('BEGIN; ' + prepared(xp,'award_xp','FOR UPDATE', f"'{A}','{PUB}'") + ' ROLLBACK;',
              'in_progress', 'production worker SELECT FOR UPDATE', role=WORKER)
    sql(prepared(xp,'award_xp','INSERT INTO public.xp_transactions', f"'{A}','{PUB}','{JOB}',50"),
        role=WORKER, label='production worker XP ledger INSERT')
    sql.equal(prepared(xp,'award_xp','SELECT COALESCE(SUM(amount)', f"'{A}'"),
              '50', 'production worker XP aggregate SELECT', role=WORKER)
    sql(f"""UPDATE public.profiles SET xp=50,level=1,total_solved=total_solved+1,
      easy_solved=easy_solved+1,total_attempts=total_attempts+1 WHERE id='{A}';""",
        role=WORKER, label='worker dynamic difficulty profile UPDATE shape')
    sql(prepared(xp,'award_xp',"SET status = 'completed'", f"'{A}','{PUB}','{JOB}'"),
        role=WORKER, label='production worker completed progress')
    sql(prepared(task,'_execute_hdl_submission','SET xp_awarded', f"'{JOB}',50"),
        role=WORKER, label='production worker submission award write')
    for index in range(2):
        sql(prepared(task,'_execute_hdl_submission','DO UPDATE SET attempts = user_challenge_progress.attempts + 1;', f"'{B}','{PUB}'"),
            role=WORKER, label='production worker wrong-answer attempt upsert ' + str(index))
    sql.equal(f"SELECT attempts||'|'||status FROM public.user_challenge_progress WHERE user_id='{B}' AND challenge_id='{PUB}';",
              '2|in_progress', 'worker wrong-answer attempt upsert executed')
    sql(prepared(task,'_execute_hdl_submission','SET total_attempts', f"'{B}'"),
        role=WORKER, label='production worker wrong-answer profile attempts')
    sql(upsert, role=API, label='production API resubmission upsert preserves completion')
    sql.equal(f"SELECT status='completed' AND attempts=3 AND best_submission_id='{JOB}' AND completed_at IS NOT NULL FROM public.user_challenge_progress WHERE user_id='{A}' AND challenge_id='{PUB}';",
              't', 'API completed evidence preserved')
    for index in range(2):
        sql(prepared(xp,'update_streak','INSERT INTO public.streak_activity', f"'{A}',CURRENT_DATE"),
            role=WORKER, label='production worker streak upsert ' + str(index))
    sql.equal(f"SELECT activity_count FROM public.streak_activity WHERE user_id='{A}';",
              '2', 'streak ON CONFLICT increments')
    sql(prepared(xp,'update_streak','SET current_streak', f"'{A}',1"),
        role=WORKER, label='production worker streak profile UPDATE')
    sql(prepared(xp,'check_quest_completion','SELECT q.id, q.title', f"'{A}','{PUB}'"),
        role=WORKER, label='production worker quest completion SELECT')
    sql(prepared(xp,'check_quest_completion','INSERT INTO public.xp_transactions', f"'{A}',25,'quest fixture'"),
        role=WORKER, label='production worker quest ledger INSERT')
    sql(prepared(xp,'check_badge_awards','SELECT b.id, b.name', f"'{A}'"),
        role=WORKER, label='production worker badge rule SELECT')
    for index in range(2):
        sql(prepared(xp,'check_badge_awards','INSERT INTO public.user_badges', f"'{A}','{BADGE}'"),
            role=WORKER, label='production worker badge ON CONFLICT ' + str(index))
    sql.equal(f"SELECT count(*) FROM public.user_badges WHERE user_id='{A}';", '1', 'badge upsert remains one row')
    # Existing stats/admin grants survive signup helper replay.
    before = sql(profiles, label='before signup trigger replay')
    before_roles = sql(roles, label='before signup role replay')
    sql(f"""CREATE TRIGGER rehearsal_signup_replay AFTER UPDATE ON auth.users
      FOR EACH ROW EXECUTE FUNCTION private.handle_new_user();
      UPDATE auth.users SET raw_user_meta_data='{{"role":"admin","xp":100000}}' WHERE id IN ('{A}','{C}');
      DROP TRIGGER rehearsal_signup_replay ON auth.users;""", label='stub trigger idempotency execution')
    sql.equal(profiles, before, 'signup replay retains scoring')
    sql.equal(roles, before_roles, 'signup replay retains trusted role grants')
    sql.equal(claim + 'SELECT count(*) FROM public.submissions;', '1', 'client history own row only', role=CLIENT)
    sql.equal(claim + 'SELECT count(*) FROM public.xp_transactions;', '2', 'client XP own rows', role=CLIENT)
    for table, expected in [('public.user_challenge_progress','1'),('public.streak_activity','1'),
                            ('public.user_badges','1'),('public.user_roles','1')]:
        sql.equal(claim + 'SELECT count(*) FROM ' + table + ';', expected, 'client own RLS: ' + table, role=CLIENT)
    sql.equal("SET request.jwt.claim.sub='" + B + "'; SELECT count(*) FROM public.xp_transactions;",
              '0', 'second client cannot read first client XP', role='rehearsal_student_b')
    sql(claim + 'SELECT submitted_code FROM public.submissions;', role=CLIENT, label='client submitted-code column denied', error='42501')
    for statement, state, label in (
        (f"INSERT INTO public.submissions(user_id,challenge_id,status,submitted_code) VALUES('{A}','{PUB}','accepted','fake')", submissions, 'client forged pregraded result'),
        (f"UPDATE public.submissions SET status='accepted',xp_awarded=999 WHERE id='{JOB}'", submissions, 'client result mutation'),
        (f"INSERT INTO public.xp_transactions(user_id,amount,reason) VALUES('{A}',999,'fake')", snapshot('public.xp_transactions'), 'client forged ledger'),
        (f"UPDATE public.user_challenge_progress SET status='completed' WHERE user_id='{B}'", progress, 'client progress mutation'),
        (f"INSERT INTO public.user_badges(user_id,badge_id) VALUES('{B}','{BADGE}') ON CONFLICT(user_id,badge_id) DO NOTHING", snapshot('public.user_badges'), 'client award upsert'),
        (f"UPDATE public.streak_activity SET activity_count=999 WHERE user_id='{A}'", snapshot('public.streak_activity'), 'client streak mutation'),
    ):
        sql.denied_unchanged(statement, state, label, role=CLIENT, prefix=claim)

    # Backend dispatch failure path remains writable, but not over worker-claimed jobs.
    sql(prepared(service,'record_publication_failure','UPDATE public.submissions',
        f"'{JOB_B}',false,'DISPATCH_FAILED','permission fixture'"), role=API, label='production API failure UPDATE')
    sql.equal(f"SELECT status||'|'||coalesce(error_code,'') FROM public.submissions WHERE id='{JOB_B}';",
              'system_error|DISPATCH_FAILED', 'failure persistence is truthful')
    before = sql(submissions, label='before API failure against finalized result')
    sql(prepared(service,'record_publication_failure','UPDATE public.submissions',
        f"'{JOB}',false,'DISPATCH_FAILED','must not overwrite'"), role=API, label='production failure ignores finalized job')
    sql.equal(submissions, before, 'worker-finalized result unchanged')

    # Actual admin SQL and RETURNING under the limited API/worker principals.
    created = sql(prepared(admin,'create_challenge','INSERT INTO public.challenges',
        "'rehearsal-created','Created','description','Fundamentals','Easy',1,50,15,'module stub; endmodule','','','[]','[]','[]','[]','objective'"),
        role=API, label='production admin INSERT RETURNING server ID')
    assert len(created) == 36
    sql(prepared(admin,'create_challenge','INSERT INTO private.challenge_secrets',
        f"'{created}','fixture solution','fixture bench','hidden_testbench','{{}}','notes'"),
        role=API, label='production admin private INSERT')
    sql(prepared(admin,'create_challenge','INSERT INTO public.admin_audit_log',
        f"'{C}','{created}','{{}}'"), role=API, label='production admin audit INSERT')
    sql.denied_unchanged(f"UPDATE public.challenges SET title='mixed',validation_status='validated',validated_at=now() WHERE id='{created}'",
                         challenges, 'API inventing validation denied', role=API, error='P0001', marker='Invalid API challenge transition')
    sql.equal(prepared(admin,'validate_challenge','RETURNING id', f"'{created}'"),
              created, 'production admin validation claim RETURNING', role=API)
    sql.equal(prepared(task,'_validate_challenge','RETURNING id', f"'{created}','validated'"),
              created, 'production worker validation RETURNING', role=WORKER)
    sql(prepared(task,'_validate_challenge','INSERT INTO public.admin_audit_log',
        f"'{C}','{created}','{{}}'"), role=WORKER, label='production worker validation audit INSERT')
    sql(prepared(admin,'publish_challenge','UPDATE public.challenges', f"'{created}'"),
        role=API, label='production admin publish validated only')
    sql.equal(f"SELECT is_published AND validation_status='published' FROM public.challenges WHERE id='{created}';",
              't', 'publication actual state')
    sql.denied_unchanged(f"UPDATE public.challenges SET title='mixed',is_published=true,validation_status='published' WHERE id='{DRAFT}'",
                         challenges, 'API draft direct publication denied', role=API, error='P0001', marker='Invalid API challenge transition')
    sql(f"UPDATE private.challenge_secrets SET hidden_testbench='changed fixture' WHERE challenge_id='{created}';",
        role=API, label='API secret edit invokes owner invalidation trigger')
    sql.equal(f"SELECT NOT is_published AND validation_status='draft' FROM public.challenges WHERE id='{created}';",
              't', 'secret trigger actually invalidates publication')
    # Worker state filter on a draft is a zero-row UPDATE, not a forged validation.
    before = sql(challenges, label='before worker validation on draft')
    sql.equal(prepared(task,'_validate_challenge','RETURNING id', f"'{created}','validated'"),
              '', 'worker validation excludes nonpending draft', role=WORKER)
    sql.equal(challenges, before, 'worker draft validation leaves state')
    sql.equal(prepared(admin,'validate_challenge','RETURNING id', f"'{created}'"),
              created, 'admin starts second validation', role=API)
    sql.equal(prepared(task,'_validate_challenge','RETURNING id', f"'{created}','validation_failed'"),
              created, 'worker failure transition RETURNING', role=WORKER)
    sql.equal(f"SELECT validation_status='validation_failed' AND validated_at IS NULL FROM public.challenges WHERE id='{created}';",
              't', 'failed validation timestamp cleared')
    for role in (API, WORKER):
        sql('CREATE TABLE public.forbidden_object(id integer);', role=role,
            label='runtime public DDL denied: ' + role, error='42501')
        sql('SELECT id FROM auth.users;', role=role, label='runtime Auth denied: ' + role, error='42501')
        sql('CREATE ROLE forbidden_role;', role=role, label='runtime role DDL denied: ' + role, error='42501')
    sql.equal("SELECT to_regclass('public.forbidden_object') IS NULL AND NOT EXISTS(SELECT 1 FROM pg_roles WHERE rolname='forbidden_role');",
              't', 'denied DDL leaves no objects')
