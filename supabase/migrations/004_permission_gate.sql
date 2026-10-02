-- 004: permission gate. Historical 001/002/003 remain untouched.
-- Must be part of the allowlisted atomic runner, never a permissive partial deployment.
DO $$ BEGIN
  IF current_user <> 'vq_owner' THEN RAISE EXCEPTION 'Dedicated application owner required'; END IF;
  IF EXISTS (SELECT 1 FROM pg_catalog.pg_roles WHERE rolname IN ('vq_api','vq_worker')
    AND (rolsuper OR rolbypassrls OR rolcreatedb OR rolcreaterole OR rolreplication OR rolinherit))
    OR (SELECT count(*) FROM pg_catalog.pg_roles WHERE rolname IN ('vq_api','vq_worker') AND rolcanlogin) <> 2
  THEN RAISE EXCEPTION 'Unsafe or missing runtime roles'; END IF;
END $$;
ALTER DEFAULT PRIVILEGES FOR ROLE vq_owner REVOKE EXECUTE ON FUNCTIONS FROM PUBLIC, anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES FOR ROLE vq_owner IN SCHEMA public REVOKE ALL ON TABLES FROM PUBLIC, anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES FOR ROLE vq_owner IN SCHEMA private REVOKE ALL ON TABLES FROM PUBLIC, anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES FOR ROLE vq_owner IN SCHEMA public REVOKE ALL ON SEQUENCES FROM PUBLIC, anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES FOR ROLE vq_owner IN SCHEMA private REVOKE ALL ON SEQUENCES FROM PUBLIC, anon, authenticated, service_role;
REVOKE ALL ON SCHEMA private FROM PUBLIC, anon, authenticated, service_role, vq_api, vq_worker;
GRANT USAGE ON SCHEMA private TO vq_api, vq_worker;
GRANT USAGE ON SCHEMA public TO vq_api, vq_worker;

-- Remove every legacy policy and table/column grant on the explicit application set.
DO $$ DECLARE obj text; cols text; pol record; BEGIN
 FOREACH obj IN ARRAY ARRAY['public.profiles','public.user_roles','public.challenges','public.challenge_prerequisites','private.challenge_secrets','public.user_challenge_progress','public.submissions','public.xp_transactions','public.quests','public.quest_challenges','public.badges','public.user_badges','public.streak_activity','public.admin_audit_log'] LOOP
  SELECT pg_catalog.string_agg(pg_catalog.quote_ident(attname),',') INTO cols
   FROM pg_catalog.pg_attribute WHERE attrelid=obj::regclass AND attnum>0 AND NOT attisdropped;
  EXECUTE pg_catalog.format('REVOKE ALL ON TABLE %s FROM PUBLIC,anon,authenticated,service_role,vq_api,vq_worker',obj);
  EXECUTE pg_catalog.format('REVOKE SELECT (%1$s),INSERT (%1$s),UPDATE (%1$s),REFERENCES (%1$s) ON TABLE %2$s FROM PUBLIC,anon,authenticated,service_role,vq_api,vq_worker',cols,obj);
  FOR pol IN SELECT policyname FROM pg_catalog.pg_policies WHERE schemaname=pg_catalog.split_part(obj,'.',1) AND tablename=pg_catalog.split_part(obj,'.',2) LOOP
   EXECUTE pg_catalog.format('DROP POLICY %I ON %s',pol.policyname,obj);
  END LOOP;
  EXECUTE 'ALTER TABLE '||obj||' ENABLE ROW LEVEL SECURITY';
 END LOOP;
END $$;

CREATE POLICY gate_1 ON public.challenges FOR SELECT TO anon USING (is_published AND NOT is_archived);
CREATE POLICY gate_2 ON public.quests FOR SELECT TO anon USING (is_active);
CREATE POLICY gate_3 ON public.badges FOR SELECT TO anon USING (is_active);
CREATE POLICY gate_4 ON public.challenge_prerequisites FOR SELECT TO anon USING (EXISTS (SELECT 1 FROM public.challenges c WHERE c.id=challenge_id AND c.is_published AND NOT c.is_archived) AND EXISTS (SELECT 1 FROM public.challenges c WHERE c.id=prerequisite_id AND c.is_published AND NOT c.is_archived));
CREATE POLICY gate_5 ON public.quest_challenges FOR SELECT TO anon USING (EXISTS (SELECT 1 FROM public.quests q WHERE q.id=quest_id AND q.is_active) AND EXISTS (SELECT 1 FROM public.challenges c WHERE c.id=challenge_id AND c.is_published AND NOT c.is_archived));
CREATE POLICY gate_6 ON public.challenges FOR SELECT TO authenticated USING (is_published AND NOT is_archived);
CREATE POLICY gate_7 ON public.quests FOR SELECT TO authenticated USING (is_active);
CREATE POLICY gate_8 ON public.badges FOR SELECT TO authenticated USING (is_active);
CREATE POLICY gate_9 ON public.challenge_prerequisites FOR SELECT TO authenticated USING (EXISTS (SELECT 1 FROM public.challenges c WHERE c.id=challenge_id AND c.is_published AND NOT c.is_archived) AND EXISTS (SELECT 1 FROM public.challenges c WHERE c.id=prerequisite_id AND c.is_published AND NOT c.is_archived));
CREATE POLICY gate_10 ON public.quest_challenges FOR SELECT TO authenticated USING (EXISTS (SELECT 1 FROM public.quests q WHERE q.id=quest_id AND q.is_active) AND EXISTS (SELECT 1 FROM public.challenges c WHERE c.id=challenge_id AND c.is_published AND NOT c.is_archived));
CREATE POLICY gate_11 ON public.profiles FOR SELECT TO authenticated USING (id=(SELECT auth.uid()));
CREATE POLICY gate_12 ON public.submissions FOR SELECT TO authenticated USING (user_id=(SELECT auth.uid()));
CREATE POLICY gate_13 ON public.user_challenge_progress FOR SELECT TO authenticated USING (user_id=(SELECT auth.uid()));
CREATE POLICY gate_14 ON public.xp_transactions FOR SELECT TO authenticated USING (user_id=(SELECT auth.uid()));
CREATE POLICY gate_15 ON public.user_badges FOR SELECT TO authenticated USING (user_id=(SELECT auth.uid()));
CREATE POLICY gate_16 ON public.streak_activity FOR SELECT TO authenticated USING (user_id=(SELECT auth.uid()));
CREATE POLICY gate_17 ON public.user_roles FOR SELECT TO authenticated USING (user_id=(SELECT auth.uid()));
CREATE POLICY gate_18 ON public.profiles FOR UPDATE TO authenticated USING (id=(SELECT auth.uid())) WITH CHECK (id=(SELECT auth.uid()));
CREATE POLICY gate_19 ON public.profiles FOR SELECT TO vq_api USING (true);
CREATE POLICY gate_20 ON public.profiles FOR UPDATE TO vq_api USING (true) WITH CHECK (true);
CREATE POLICY gate_21 ON public.challenges FOR SELECT TO vq_api USING (true);
CREATE POLICY gate_22 ON public.challenges FOR INSERT TO vq_api WITH CHECK (true);
CREATE POLICY gate_23 ON public.challenges FOR UPDATE TO vq_api USING (true) WITH CHECK (true);
CREATE POLICY gate_24 ON public.user_challenge_progress FOR SELECT TO vq_api USING (true);
CREATE POLICY gate_25 ON public.user_challenge_progress FOR INSERT TO vq_api WITH CHECK (true);
CREATE POLICY gate_26 ON public.user_challenge_progress FOR UPDATE TO vq_api USING (true) WITH CHECK (true);
CREATE POLICY gate_27 ON public.user_badges FOR SELECT TO vq_api USING (true);
CREATE POLICY gate_28 ON public.admin_audit_log FOR SELECT TO vq_api USING (true);
CREATE POLICY gate_29 ON public.admin_audit_log FOR INSERT TO vq_api WITH CHECK (true);
CREATE POLICY gate_30 ON public.badges FOR SELECT TO vq_api USING (true);
CREATE POLICY gate_31 ON public.xp_transactions FOR SELECT TO vq_api USING (true);
CREATE POLICY gate_32 ON public.user_roles FOR SELECT TO vq_api USING (true);
CREATE POLICY gate_33 ON public.submissions FOR SELECT TO vq_api USING (true);
CREATE POLICY gate_34 ON public.submissions FOR INSERT TO vq_api WITH CHECK (status='queued' AND started_at IS NULL AND completed_at IS NULL AND runtime_ms IS NULL AND simulation_ns IS NULL AND tests_total=0 AND tests_passed=0 AND tests_failed=0 AND xp_awarded=0 AND worker_id IS NULL AND error_code IS NULL AND public_message IS NULL AND compiler_output IS NULL);
CREATE POLICY gate_35 ON public.submissions FOR UPDATE TO vq_api USING (status='queued') WITH CHECK (status IN ('queued','system_error') AND started_at IS NULL AND runtime_ms IS NULL AND simulation_ns IS NULL AND tests_total=0 AND tests_passed=0 AND tests_failed=0 AND xp_awarded=0 AND worker_id IS NULL AND compiler_output IS NULL);
CREATE POLICY gate_36 ON private.challenge_secrets FOR SELECT TO vq_api USING (true);
CREATE POLICY gate_37 ON private.challenge_secrets FOR INSERT TO vq_api WITH CHECK (true);
CREATE POLICY gate_38 ON private.challenge_secrets FOR UPDATE TO vq_api USING (true) WITH CHECK (true);
CREATE POLICY gate_39 ON public.submissions FOR SELECT TO vq_worker USING (true);
CREATE POLICY gate_40 ON public.submissions FOR UPDATE TO vq_worker USING (true) WITH CHECK (true);
CREATE POLICY gate_41 ON public.challenges FOR SELECT TO vq_worker USING (true);
CREATE POLICY gate_42 ON public.challenges FOR UPDATE TO vq_worker USING (NOT is_published AND validation_status='validating') WITH CHECK (NOT is_published AND validation_status IN ('validated','validation_failed'));
CREATE POLICY gate_43 ON private.challenge_secrets FOR SELECT TO vq_worker USING (true);
CREATE POLICY gate_44 ON public.profiles FOR SELECT TO vq_worker USING (true);
CREATE POLICY gate_45 ON public.profiles FOR UPDATE TO vq_worker USING (true) WITH CHECK (true);
CREATE POLICY gate_46 ON public.user_challenge_progress FOR SELECT TO vq_worker USING (true);
CREATE POLICY gate_47 ON public.user_challenge_progress FOR INSERT TO vq_worker WITH CHECK (true);
CREATE POLICY gate_48 ON public.user_challenge_progress FOR UPDATE TO vq_worker USING (true) WITH CHECK (true);
CREATE POLICY gate_49 ON public.xp_transactions FOR SELECT TO vq_worker USING (true);
CREATE POLICY gate_50 ON public.xp_transactions FOR INSERT TO vq_worker WITH CHECK (true);
CREATE POLICY gate_51 ON public.quests FOR SELECT TO vq_worker USING (true);
CREATE POLICY gate_52 ON public.quest_challenges FOR SELECT TO vq_worker USING (true);
CREATE POLICY gate_53 ON public.badges FOR SELECT TO vq_worker USING (true);
CREATE POLICY gate_54 ON public.user_badges FOR SELECT TO vq_worker USING (true);
CREATE POLICY gate_55 ON public.user_badges FOR INSERT TO vq_worker WITH CHECK (true);
CREATE POLICY gate_56 ON public.streak_activity FOR SELECT TO vq_worker USING (true);
CREATE POLICY gate_57 ON public.streak_activity FOR INSERT TO vq_worker WITH CHECK (true);
CREATE POLICY gate_58 ON public.streak_activity FOR UPDATE TO vq_worker USING (true) WITH CHECK (true);
CREATE POLICY gate_59 ON public.admin_audit_log FOR INSERT TO vq_worker WITH CHECK (true);

-- Column grants, never table-wide mutation privileges.
GRANT SELECT (id,slug,title,description,category,difficulty,level_number,xp_reward,estimated_minutes,starter_code,input_description,output_description,constraints,public_examples,io_pins,hints,learning_objective,is_published,is_archived) ON public.challenges TO anon;
GRANT SELECT (id,challenge_id,prerequisite_id) ON public.challenge_prerequisites TO anon;
GRANT SELECT (id,title,description,category,xp_reward,is_active,sort_order,created_at,updated_at) ON public.quests TO anon;
GRANT SELECT (id,quest_id,challenge_id,sort_order) ON public.quest_challenges TO anon;
GRANT SELECT (id,name,description,category,icon,requirement,is_active) ON public.badges TO anon;
GRANT SELECT (id,slug,title,description,category,difficulty,level_number,xp_reward,estimated_minutes,starter_code,input_description,output_description,constraints,public_examples,io_pins,hints,learning_objective,is_published,is_archived) ON public.challenges TO authenticated;
GRANT SELECT (id,challenge_id,prerequisite_id) ON public.challenge_prerequisites TO authenticated;
GRANT SELECT (id,title,description,category,xp_reward,is_active,sort_order,created_at,updated_at) ON public.quests TO authenticated;
GRANT SELECT (id,quest_id,challenge_id,sort_order) ON public.quest_challenges TO authenticated;
GRANT SELECT (id,name,description,category,icon,requirement,is_active) ON public.badges TO authenticated;
GRANT SELECT (id,username,display_name,avatar_url,bio,level,xp,current_streak,longest_streak,total_solved,easy_solved,medium_solved,hard_solved,total_attempts,created_at,updated_at) ON public.profiles TO authenticated;
GRANT UPDATE (display_name,bio,avatar_url) ON public.profiles TO authenticated;
GRANT SELECT (id,user_id,challenge_id,status,attempts,best_submission_id,completed_at,created_at,updated_at) ON public.user_challenge_progress TO authenticated;
GRANT SELECT (id,user_id,challenge_id,submission_id,amount,reason,created_at) ON public.xp_transactions TO authenticated;
GRANT SELECT (id,user_id,badge_id,unlocked_at) ON public.user_badges TO authenticated;
GRANT SELECT (id,user_id,activity_date,activity_type,activity_count,created_at) ON public.streak_activity TO authenticated;
GRANT SELECT (id,user_id,challenge_id,status,submitted_at,completed_at,runtime_ms,simulation_ns,tests_total,tests_passed,tests_failed,error_code,public_message,compiler_output,xp_awarded) ON public.submissions TO authenticated;
GRANT SELECT (user_id,role) ON public.user_roles TO authenticated;
GRANT SELECT (id,username,display_name,avatar_url,bio,level,xp,current_streak,longest_streak,total_solved,easy_solved,medium_solved,hard_solved,total_attempts,created_at,updated_at) ON public.profiles TO vq_api;
GRANT UPDATE (display_name,bio,avatar_url) ON public.profiles TO vq_api;
GRANT SELECT (id,slug,title,description,category,difficulty,level_number,xp_reward,estimated_minutes,starter_code,input_description,output_description,constraints,public_examples,io_pins,hints,learning_objective,is_published,is_archived,validation_status,validated_at,published_at,created_at,updated_at) ON public.challenges TO vq_api;
GRANT INSERT (slug,title,description,category,difficulty,level_number,xp_reward,estimated_minutes,starter_code,input_description,output_description,constraints,public_examples,io_pins,hints,learning_objective,validation_status) ON public.challenges TO vq_api;
GRANT UPDATE (title,description,category,difficulty,level_number,xp_reward,estimated_minutes,starter_code,input_description,output_description,constraints,public_examples,io_pins,hints,learning_objective,validation_status,validated_at,is_published,published_at) ON public.challenges TO vq_api;
GRANT SELECT (id,user_id,challenge_id,status,attempts,best_submission_id,completed_at,created_at,updated_at) ON public.user_challenge_progress TO vq_api;
GRANT INSERT (user_id,challenge_id,status,attempts) ON public.user_challenge_progress TO vq_api;
GRANT UPDATE (status,attempts,updated_at) ON public.user_challenge_progress TO vq_api;
GRANT SELECT (id,user_id,badge_id,unlocked_at) ON public.user_badges TO vq_api;
GRANT SELECT (id,admin_user_id,action,target_type,target_id,details,created_at) ON public.admin_audit_log TO vq_api;
GRANT INSERT (admin_user_id,action,target_type,target_id,details) ON public.admin_audit_log TO vq_api;
GRANT SELECT (id,name,description,category,icon,requirement) ON public.badges TO vq_api;
GRANT SELECT (user_id,amount,created_at) ON public.xp_transactions TO vq_api;
GRANT SELECT (user_id,role) ON public.user_roles TO vq_api;
GRANT SELECT (id,user_id,challenge_id,status,idempotency_key,submitted_at,completed_at,runtime_ms,simulation_ns,tests_total,tests_passed,tests_failed,error_code,public_message,compiler_output,xp_awarded) ON public.submissions TO vq_api;
GRANT INSERT (id,user_id,challenge_id,status,submitted_code,idempotency_key,submitted_at) ON public.submissions TO vq_api;
GRANT UPDATE (status,completed_at,error_code,public_message) ON public.submissions TO vq_api;
GRANT SELECT (challenge_id,official_solution,hidden_testbench,evaluator_type,execution_profile,private_notes) ON private.challenge_secrets TO vq_api;
GRANT INSERT (challenge_id,official_solution,hidden_testbench,evaluator_type,execution_profile,private_notes) ON private.challenge_secrets TO vq_api;
GRANT UPDATE (official_solution,hidden_testbench,evaluator_type,execution_profile,private_notes) ON private.challenge_secrets TO vq_api;
GRANT SELECT (id,user_id,challenge_id,submitted_code,status) ON public.submissions TO vq_worker;
GRANT UPDATE (status,started_at,worker_id,completed_at,runtime_ms,simulation_ns,tests_total,tests_passed,tests_failed,error_code,public_message,compiler_output,xp_awarded) ON public.submissions TO vq_worker;
GRANT SELECT (id,xp_reward,difficulty,is_published,validation_status) ON public.challenges TO vq_worker;
GRANT UPDATE (validation_status,validated_at) ON public.challenges TO vq_worker;
GRANT SELECT (challenge_id,official_solution,hidden_testbench,evaluator_type,execution_profile) ON private.challenge_secrets TO vq_worker;
GRANT SELECT (id,xp,level,total_solved,easy_solved,medium_solved,hard_solved,total_attempts,current_streak,longest_streak) ON public.profiles TO vq_worker;
GRANT UPDATE (xp,level,total_solved,easy_solved,medium_solved,hard_solved,total_attempts,current_streak,longest_streak) ON public.profiles TO vq_worker;
GRANT SELECT (id,user_id,challenge_id,status,attempts,best_submission_id,completed_at,created_at,updated_at) ON public.user_challenge_progress TO vq_worker;
GRANT INSERT (user_id,challenge_id,status,attempts) ON public.user_challenge_progress TO vq_worker;
GRANT UPDATE (status,attempts,best_submission_id,completed_at,updated_at) ON public.user_challenge_progress TO vq_worker;
GRANT SELECT (id,user_id,challenge_id,submission_id,amount,reason,created_at) ON public.xp_transactions TO vq_worker;
GRANT INSERT (user_id,challenge_id,submission_id,amount,reason) ON public.xp_transactions TO vq_worker;
GRANT SELECT (id,title,description,category,xp_reward,is_active,sort_order,created_at,updated_at) ON public.quests TO vq_worker;
GRANT SELECT (id,quest_id,challenge_id,sort_order) ON public.quest_challenges TO vq_worker;
GRANT SELECT (id,name,description,category,icon,requirement,rule_type,rule_config,is_active,created_at) ON public.badges TO vq_worker;
GRANT SELECT (id,user_id,badge_id,unlocked_at) ON public.user_badges TO vq_worker;
GRANT INSERT (user_id,badge_id) ON public.user_badges TO vq_worker;
GRANT SELECT (id,user_id,activity_date,activity_type,activity_count,created_at) ON public.streak_activity TO vq_worker;
GRANT INSERT (user_id,activity_date,activity_type,activity_count) ON public.streak_activity TO vq_worker;
GRANT UPDATE (activity_count) ON public.streak_activity TO vq_worker;
GRANT INSERT (admin_user_id,action,target_type,target_id,details) ON public.admin_audit_log TO vq_worker;

-- Trusted trigger side effects must not depend on student/worker policy authority.
CREATE OR REPLACE FUNCTION private.invalidate_challenge_on_secret_change()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path='' AS $$
BEGIN
 IF OLD.official_solution IS DISTINCT FROM NEW.official_solution OR
    OLD.hidden_testbench IS DISTINCT FROM NEW.hidden_testbench THEN
  UPDATE public.challenges SET is_published=false,validation_status='draft' WHERE id=NEW.challenge_id;
 END IF;
 RETURN NEW;
END $$;
DROP TRIGGER on_secret_changed_invalidate ON private.challenge_secrets;
CREATE TRIGGER on_secret_changed_invalidate AFTER UPDATE ON private.challenge_secrets
 FOR EACH ROW EXECUTE FUNCTION private.invalidate_challenge_on_secret_change();

CREATE OR REPLACE FUNCTION private.update_updated_at()
RETURNS trigger LANGUAGE plpgsql SET search_path='' AS $$
BEGIN NEW.updated_at=pg_catalog.now(); RETURN NEW; END $$;
DROP TRIGGER set_updated_at_profiles ON public.profiles;
DROP TRIGGER set_updated_at_challenges ON public.challenges;
DROP TRIGGER set_updated_at_progress ON public.user_challenge_progress;
DROP TRIGGER set_updated_at_secrets ON private.challenge_secrets;
DROP TRIGGER set_updated_at_quests ON public.quests;
CREATE TRIGGER set_updated_at_profiles BEFORE UPDATE ON public.profiles FOR EACH ROW EXECUTE FUNCTION private.update_updated_at();
CREATE TRIGGER set_updated_at_challenges BEFORE UPDATE ON public.challenges FOR EACH ROW EXECUTE FUNCTION private.update_updated_at();
CREATE TRIGGER set_updated_at_progress BEFORE UPDATE ON public.user_challenge_progress FOR EACH ROW EXECUTE FUNCTION private.update_updated_at();
CREATE TRIGGER set_updated_at_secrets BEFORE UPDATE ON private.challenge_secrets FOR EACH ROW EXECUTE FUNCTION private.update_updated_at();
CREATE TRIGGER set_updated_at_quests BEFORE UPDATE ON public.quests FOR EACH ROW EXECUTE FUNCTION private.update_updated_at();
DROP FUNCTION public.update_updated_at();

-- Preserve source-required attempt upserts without granting API completion authority.
CREATE FUNCTION private.guard_api_challenge()
RETURNS trigger LANGUAGE plpgsql SET search_path='' AS $$
BEGIN
 IF current_user='vq_api' THEN
  IF TG_OP='INSERT' THEN
   IF NEW.validation_status<>'draft' OR NEW.is_published OR NEW.is_archived OR NEW.validated_at IS NOT NULL OR NEW.published_at IS NOT NULL THEN
    RAISE EXCEPTION 'API challenge creation must be an unvalidated draft';
   END IF;
  ELSIF NEW.validation_status IS DISTINCT FROM OLD.validation_status THEN
   IF NOT ((NEW.validation_status='validating' AND NOT OLD.is_published AND NOT NEW.is_published) OR
      (NEW.validation_status='validation_failed' AND OLD.validation_status='validating' AND NOT NEW.is_published) OR
      (NEW.validation_status='published' AND OLD.validation_status='validated' AND NEW.is_published)) THEN
    RAISE EXCEPTION 'Invalid API challenge transition';
   END IF;
  ELSIF NEW.is_published AND NOT OLD.is_published THEN
   RAISE EXCEPTION 'Publication requires a validated transition';
  END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER guard_api_challenge BEFORE INSERT OR UPDATE ON public.challenges
 FOR EACH ROW EXECUTE FUNCTION private.guard_api_challenge();

CREATE FUNCTION private.guard_api_progress()
RETURNS trigger LANGUAGE plpgsql SET search_path='' AS $$
BEGIN
 IF current_user='vq_api' THEN
  IF TG_OP='INSERT' THEN
   IF NEW.status<>'in_progress' OR NEW.attempts<>1 OR NEW.best_submission_id IS NOT NULL OR NEW.completed_at IS NOT NULL THEN
    RAISE EXCEPTION 'Invalid API progress insertion';
   END IF;
  ELSIF NEW.attempts<>OLD.attempts+1 OR
   NEW.status IS DISTINCT FROM (CASE WHEN OLD.status='completed' THEN 'completed' ELSE 'in_progress' END) OR
   NEW.best_submission_id IS DISTINCT FROM OLD.best_submission_id OR NEW.completed_at IS DISTINCT FROM OLD.completed_at THEN
   RAISE EXCEPTION 'Invalid API progress update';
  END IF;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER guard_api_progress BEFORE INSERT OR UPDATE ON public.user_challenge_progress
 FOR EACH ROW EXECUTE FUNCTION private.guard_api_progress();

REVOKE ALL ON FUNCTION private.invalidate_challenge_on_secret_change(),private.update_updated_at(),private.guard_api_progress(),private.guard_api_challenge(),public.handle_new_user() FROM PUBLIC,anon,authenticated,service_role,vq_api,vq_worker;
-- Legacy signup function is removed by 005 in the same transaction.
ALTER FUNCTION public.handle_new_user() SET search_path='';

