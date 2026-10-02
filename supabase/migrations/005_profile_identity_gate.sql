-- 005: atomic Auth-linked identity. No backfill, renaming, role promotion or scoring repair.
DO $$ BEGIN
 IF current_user <> 'vq_owner' THEN RAISE EXCEPTION 'Dedicated application owner required'; END IF;
 IF EXISTS (SELECT 1 FROM public.profiles
   WHERE pg_catalog.left(username,8)='vq_user_' AND username <> 'vq_user_'||pg_catalog.replace(id::text,'-','')) THEN
  RAISE EXCEPTION 'Reserved username collision; reviewed upgrade repair required';
 END IF;
END $$;

ALTER TABLE public.profiles ADD CONSTRAINT profile_display_bounds CHECK (
 (display_name IS NULL OR pg_catalog.char_length(display_name)<=100) AND
 (bio IS NULL OR pg_catalog.char_length(bio)<=2000) AND
 (avatar_url IS NULL OR pg_catalog.char_length(avatar_url)<=2048));
ALTER TABLE public.profiles ADD CONSTRAINT profile_counts_nonnegative CHECK (
 total_solved>=0 AND easy_solved>=0 AND medium_solved>=0 AND hard_solved>=0 AND total_attempts>=0);
ALTER TABLE public.profiles ADD CONSTRAINT profile_reserved_username CHECK (
 pg_catalog.left(username,8)<>'vq_user_' OR username='vq_user_'||pg_catalog.replace(id::text,'-',''));

CREATE FUNCTION private.handle_new_user()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path='' AS $$
DECLARE presentation text := 'Student'; metadata jsonb := NEW.raw_user_meta_data;
BEGIN
 IF pg_catalog.jsonb_typeof(metadata)='object' THEN
  IF pg_catalog.jsonb_typeof(metadata->'display_name')='string' THEN
   presentation=pg_catalog.left(pg_catalog.btrim(metadata->>'display_name'),100);
  ELSIF pg_catalog.jsonb_typeof(metadata->'full_name')='string' THEN
   presentation=pg_catalog.left(pg_catalog.btrim(metadata->>'full_name'),100);
  END IF;
 END IF;
 IF presentation IS NULL OR presentation='' THEN presentation='Student'; END IF;
 INSERT INTO public.profiles (
  id,username,display_name,level,xp,current_streak,longest_streak,total_solved,
  easy_solved,medium_solved,hard_solved,total_attempts)
 VALUES (NEW.id,'vq_user_'||pg_catalog.replace(NEW.id::text,'-',''),presentation,1,0,0,0,0,0,0,0,0)
 ON CONFLICT (id) DO NOTHING;
 INSERT INTO public.user_roles(user_id,role) VALUES(NEW.id,'student')
 ON CONFLICT(user_id,role) DO NOTHING;
 RETURN NEW;
END $$;
REVOKE ALL ON FUNCTION private.handle_new_user() FROM PUBLIC,anon,authenticated,service_role,vq_api,vq_worker;
-- DROP TRIGGER requires ownership of the platform Auth table, not merely its
-- temporary TRIGGER grant. Use the runner's trusted platform operator only for
-- this attachment; never transfer auth.users ownership to an application role.
RESET ROLE;
DO $$ BEGIN
 IF current_user <> 'supabase_admin' OR session_user <> 'supabase_admin' THEN
  RAISE EXCEPTION 'Trusted platform migration operator required';
 END IF;
END $$;
DROP TRIGGER on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created AFTER INSERT ON auth.users
 FOR EACH ROW EXECUTE FUNCTION private.handle_new_user();
SET LOCAL ROLE vq_owner;
DROP FUNCTION public.handle_new_user();
