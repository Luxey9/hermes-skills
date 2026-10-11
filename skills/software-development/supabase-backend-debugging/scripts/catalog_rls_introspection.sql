-- =============================================================================
--  READ-ONLY RLS / GRANT / POLICY INTROSPECTION
--
--  Use when you have a PostgREST key (anon / service_role) but NO DDL access:
--  service_role cannot read pg_catalog, and the OpenAPI spec exposes columns but
--  nothing about RLS, grants, policies, view owners or function bodies. Hand this
--  file to the user to paste into the Supabase SQL Editor.
--
--  EVERY statement below is SELECT-only: it cannot alter data or schema. Say so
--  when you hand it over.
--
--  RUN THE BLOCKS ONE AT A TIME. The Supabase SQL Editor renders only the LAST
--  statement's grid, so several statements in one block silently discard the
--  earlier results. Each block below is separated by a blank comment line.
-- =============================================================================

-- [A] OBJECT KIND + RLS FLAGS + POLICY COUNT  (r=table v=view m=matview p=partitioned)
SELECT c.relname AS objek, c.relkind AS jenis,
       c.relrowsecurity AS rls_on, c.relforcerowsecurity AS forced,
       pg_get_userbyid(c.relowner) AS owner,
       (SELECT count(*) FROM pg_policies p
         WHERE p.schemaname='public' AND p.tablename=c.relname) AS jml_policy
FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE n.nspname='public' AND c.relkind IN ('r','v','m','p')
ORDER BY c.relkind, c.relname;

-- [B] ALL POLICIES — look for roles='{anon}' with qual='true' (leaks despite RLS)
SELECT tablename, policyname, roles::text AS roles, cmd AS perintah,
       COALESCE(qual,'-') AS using_expr, COALESCE(with_check,'-') AS with_check
FROM pg_policies WHERE schemaname='public'
ORDER BY tablename, policyname;

-- [C] TABLE-LEVEL GRANTS — a grant on a VIEW is the whole leak; check grantees carefully
SELECT table_name, grantee,
       string_agg(DISTINCT privilege_type, ',' ORDER BY privilege_type) AS hak
FROM information_schema.role_table_grants
WHERE table_schema='public' AND grantee IN ('anon','authenticated','PUBLIC')
GROUP BY table_name, grantee ORDER BY table_name, grantee;

-- [D] COLUMN GRANTS — proves whether a sensitive column was really revoked (0 rows = revoked)
SELECT table_name, column_name, grantee, privilege_type
FROM information_schema.column_privileges
WHERE table_schema='public' AND grantee IN ('anon','authenticated')
  AND (column_name ILIKE '%password%' OR column_name ILIKE '%salt%'
       OR column_name ILIKE '%token%'    OR column_name ILIKE '%secret%')
ORDER BY table_name, column_name, grantee;

-- [E] VIEWS: owner + security_invoker  <-- the decisive query if anon reads a view's rows
--     owner 'postgres' + no security_invoker = the view bypasses the base table's RLS
SELECT c.relname AS view_name, pg_get_userbyid(c.relowner) AS owner,
       COALESCE(c.reloptions::text,'-') AS reloptions,
       COALESCE((SELECT option_value FROM pg_options_to_table(c.reloptions)
                  WHERE option_name='security_invoker'),'ABSEN -> hak OWNER') AS security_invoker,
       pg_get_viewdef(c.oid, true) AS definisi
FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE n.nspname='public' AND c.relkind='v' ORDER BY c.relname;

-- [F] FUNCTIONS: SECURITY DEFINER/INVOKER + search_path + body
--     DEFINER without a pinned search_path is a hardening finding; the body shows
--     the role literals and any column list that does not match the table
SELECT p.proname AS fungsi,
       CASE WHEN p.prosecdef THEN 'DEFINER' ELSE 'INVOKER' END AS mode,
       pg_get_userbyid(p.proowner) AS owner,
       COALESCE(array_to_string(p.proconfig, ', '), '-') AS config,
       pg_get_functiondef(p.oid) AS definisi
FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace
WHERE n.nspname='public'
ORDER BY p.prosecdef DESC, p.proname;
-- too long to read in one grid: keep proname/prosecdef/owner/config and fetch
-- pg_get_functiondef per function you actually care about.

-- [G] TRIGGERS — a BEFORE INSERT/UPDATE OF role trigger can rewrite the role on write
SELECT t.tgname, p.proname AS fungsi, t.tgenabled,
       pg_get_triggerdef(t.oid) AS definisi
FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid
JOIN pg_proc  p ON p.oid = t.tgfoid
WHERE c.relname='users' AND NOT t.tgisinternal;

-- [H] LIVE ROLE VOCABULARY — the stored values, next to any app-native shadow column
SELECT role, elearning_role, count(*) FROM public.users
GROUP BY role, elearning_role ORDER BY count(*) DESC;

-- [I] DEFAULT PRIVILEGES — will the next table created here be open from birth?
SELECT defaclrole::regrole AS role_pemilik, defaclnamespace::regnamespace AS schema,
       defaclobjtype, defaclacl FROM pg_default_acl ORDER BY 1,2,3;

-- =============================================================================
-- READING THE RESULTS
--   [A] rls_on=false + relkind='v' + owner=postgres        -> view bypasses base RLS
--   [B] roles='{anon}' and qual='true'                     -> leak despite RLS enabled
--   [C] anon grant on a VIEW while its base table has none -> that view is the only hole
--   [D] password/salt/token columns still listed for anon  -> the REVOKE never ran
--   [E] security_invoker ABSEN + owner=postgres            -> expected shape; fix with
--                                                             REVOKE ALL FROM anon +
--                                                             GRANT SELECT TO authenticated
--                                                             (NOT security_invoker=true)
--   [F] DEFINER + role literal 'koordinator' in the body    -> alias role (kordas/admin) denied
--   [G] trigger mapping a role into a MORE PRIVILEGED one  -> escalation path on next write
--   [H] a value in shadow column with 0 rows in role column -> dormant trigger, the intended shape
-- =============================================================================
