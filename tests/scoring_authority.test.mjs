import assert from 'node:assert/strict';
import React from 'react';
import { createServer } from 'vite';

// Production components rendered with a minimal hook dispatcher. This is a
// simulated session/component test, not browser reconciliation or live auth.
function harness(Component, context = {}) {
  const slots = [], effects = [];
  let cursor = 0, tree;
  const dispatcher = {
    useState(initial) {
      const i = cursor++;
      if (!(i in slots)) slots[i] = typeof initial === 'function' ? initial() : initial;
      return [slots[i], value => { slots[i] = typeof value === 'function' ? value(slots[i]) : value; }];
    },
    useRef(initial) { const i = cursor++; return slots[i] ??= { current: initial }; },
    useCallback(fn) { cursor++; return fn; },
    useContext() { return context; },
    useEffect(fn, deps) {
      const i = cursor++, old = slots[i];
      if (!old || !deps || deps.some((v, j) => v !== old.deps[j])) {
        effects.push(() => { old?.cleanup?.(); slots[i] = { deps, cleanup: fn() }; });
      }
    },
  };
  return {
    slots,
    render(props = {}) {
      cursor = 0;
      const internals = React.__CLIENT_INTERNALS_DO_NOT_USE_OR_WARN_USERS_THEY_CANNOT_UPGRADE;
      const previous = internals.H;
      internals.H = dispatcher;
      try { tree = Component(props); return tree; } finally { internals.H = previous; }
    },
    flush() { while (effects.length) effects.shift()(); },
    dispose() { for (const s of slots) s?.cleanup?.(); },
  };
}
function elements(tree) {
  if (Array.isArray(tree)) return tree.flatMap(elements);
  if (!tree || typeof tree !== 'object') return [];
  return [tree, ...elements(tree.props?.children)];
}
const ok = data => ({ data, error: null });
const failure = code => ({ data: null, error: { code, message: `${code} test failure` } });
const deferred = () => { let resolve; const promise = new Promise(r => { resolve = r; }); return { promise, resolve }; };
const settle = () => new Promise(r => setTimeout(r, 0));
let count = 0;
function check(condition, message) { assert(condition, message); count++; }
async function rejects(promise, pattern) { await assert.rejects(promise, pattern); count++; }
const server = await createServer({ server: { host: '127.0.0.1', port: 0 }, configFile: './vite.config.ts' });
const originalFetch = globalThis.fetch;
const originalWindow = globalThis.window;
const originalDocument = globalThis.document;
const disposables = [];
try {
  await server.listen();
  const address = server.httpServer.address();
  const base = `http://127.0.0.1:${address.port}`;
  console.log(`Temporary Vite: ${base}`);
  const { api } = await server.ssrLoadModule('/src/api/client.ts');
  const productionSubmit = api.submissions.submitSolution;
  const { submissionApi } = await server.ssrLoadModule('/src/api/submissionApi.ts');
  const boundary = await server.ssrLoadModule('/src/api/sessionBoundary.ts');
  const { supabase } = await server.ssrLoadModule('/src/lib/supabase.ts');
  const { AppProvider } = await server.ssrLoadModule('/src/context/AppContext.tsx');
  const { emptyProfile } = await server.ssrLoadModule('/src/context/profileState.ts');
  const { AdminView } = await server.ssrLoadModule('/src/views/AdminView.tsx');
  const { WorkspaceView } = await server.ssrLoadModule('/src/views/WorkspaceView.tsx');
  const { ActivityCard } = await server.ssrLoadModule('/src/components/dashboard/ActivityCard.tsx');
  const { HeroQuestCard } = await server.ssrLoadModule('/src/components/dashboard/HeroQuestCard.tsx');
  const { AppSidebar } = await server.ssrLoadModule('/src/components/layout/AppSidebar.tsx');
  const { App } = await server.ssrLoadModule('/src/App.tsx');
  const { challengeApi } = await server.ssrLoadModule('/src/api/challengeApi.ts');
  const { MOCK_USER } = await server.ssrLoadModule('/src/api/mockData.ts');
  const baseline = JSON.stringify(MOCK_USER);
  let evaluatorCalls = 0;
  globalThis.fetch = (url, options) => {
    if (String(url).startsWith('/api/internal/')) { evaluatorCalls++; return originalFetch(base + url, options); }
    throw new Error('No external network is allowed by this test');
  };
  boundary.changeSessionIdentity('A');
  const errors = ['UNAUTHORIZED', 'FORBIDDEN', 'VALIDATION_ERROR', 'RATE_LIMITED', 'SYSTEM_ERROR', 'NETWORK_ERROR'];
  for (const code of errors) {
    api.submissions.submitSolution = async () => failure(code);
    await rejects(submissionApi.submitSolution('and-gate-demo', 'bad'), new RegExp(code));
    api.submissions.getSubmission = async () => failure(code);
    await rejects(submissionApi.pollSubmissionStatus('backend-id'), new RegExp(code));
  }
  api.submissions.submitSolution = async () => { throw new Error('unexpected submit'); };
  await rejects(submissionApi.submitSolution('and-gate-demo', 'bad'), /unexpected submit/);
  api.submissions.getSubmission = async () => { throw new Error('unexpected poll'); };
  await rejects(submissionApi.pollSubmissionStatus('backend-id'), /unexpected poll/);
  check(evaluatorCalls === 0, 'Errors must never invoke local grading');
  api.submissions.submitSolution = async () => ok({ submission_id: 'real-backend-id', status: 'queued' });
  check((await submissionApi.submitSolution('and-gate-demo', 'code')).submissionId === 'real-backend-id', 'Backend ID retained');
  api.submissions.getSubmission = async () => ok({ status: 'accepted', challenge_id: 'db-id', xp_awarded: 73 });
  check((await submissionApi.pollSubmissionStatus('real-backend-id')).xpEarned === 73, 'Backend award preserved');
  for (const method of ['submitSolution', 'getSubmission']) {
    const d = deferred();
    api.submissions[method] = () => d.promise;
    const pending = method === 'submitSolution' ? submissionApi.submitSolution('challenge', 'code') : submissionApi.pollSubmissionStatus('id');
    boundary.changeSessionIdentity(null); boundary.changeSessionIdentity('B');
    d.resolve(ok({ submission_id: 'A-id', status: 'accepted', xp_awarded: 99 }));
    await rejects(pending, /SESSION_CHANGED/);
  }
  boundary.changeSessionIdentity(null);
  await rejects(submissionApi.submitSolution('and-gate-demo', 'code'), /UNAUTHORIZED/);
  const practice = await submissionApi.runPublicVectors('and-gate-demo', 'module and_gate(input a, input b, output y); assign y = a & b; endmodule');
  check(practice.status === 'ACCEPTED' && practice.xpEarned === 0, 'Real WASM practice accepted, zero XP');
  const matrix = await submissionApi.runTestMatrixCase('and-gate-demo', 'A');
  check(matrix.status === 'ACCEPTED' && matrix.xpEarned === 0, 'Real reference matrix zero XP');
  check(JSON.stringify(MOCK_USER) === baseline, 'Practice/matrix never mutate fixture profile');
  check(!('getCompletedChallenges' in (await server.ssrLoadModule('/src/api/submissionApi.ts'))), 'Scoring ledger removed');

  // Account A → logout → B, delayed A profile and delayed sign-out completion.
  globalThis.document = { documentElement: { setAttribute() {} } };
  globalThis.window = { scrollTo() {}, addEventListener() {}, removeEventListener() {} };
  let authCallback;
  supabase.auth.getSession = async () => ({ data: { session: null } });
  supabase.auth.onAuthStateChange = cb => { authCallback = cb; return { data: { subscription: { unsubscribe() {} } } }; };
  api.admin.listChallenges = async () => failure('FORBIDDEN');
  const aProfile = deferred();
  api.getProfile = () => aProfile.promise;
  const provider = harness(AppProvider); disposables.push(provider);
  provider.render(); provider.flush(); await settle();
  const session = id => ({ user: { id, email: `${id}@example.test`, user_metadata: { role: 'admin' } } });
  authCallback('SIGNED_IN', session('A'));
  let value = provider.render().props.value;
  check(value.user.id === 'A' && value.user.stats.currentXP === 0, 'A starts with zero, not fixture stats');
  const signOut = deferred(); supabase.auth.signOut = () => signOut.promise;
  const pendingLogout = value.logout();
  value = provider.render().props.value;
  check(!value.isAuthenticated && value.user.id === 'practice', 'Logout clears identity immediately');
  api.getProfile = async () => ok({ ...emptyProfile({ id: 'B' }), stats: { ...emptyProfile().stats, currentXP: 20 } });
  authCallback('SIGNED_IN', session('B')); await settle();
  aProfile.resolve(ok({ ...emptyProfile({ id: 'A' }), stats: { ...emptyProfile().stats, currentXP: 900 } }));
  signOut.resolve({ error: null }); await pendingLogout; await settle();
  value = provider.render().props.value;
  check(value.user.id === 'B' && value.user.stats.currentXP === 20 && value.isAuthenticated, 'Delayed A and logout cannot replace B');
  check(!value.isAdmin, 'Editable role metadata never grants admin');
  api.admin.listChallenges = async () => ok({ challenges: [] });
  authCallback('TOKEN_REFRESHED', session('B')); await settle();
  check(provider.render().props.value.isAdmin, 'Backend-authorized admin probe grants UI');
  const activity = JSON.stringify(harness(ActivityCard, { user: emptyProfile(), setCurrentRoute() {} }).render());
  check(activity.includes('Rank unavailable') && activity.includes('Server badges unavailable'), 'Unavailable server stats are not fixture rank/badges');
  const hero = JSON.stringify(harness(HeroQuestCard, { user: { ...emptyProfile(), stats: { ...emptyProfile().stats, totalSolved: 9 } }, openChallenge() {} }).render());
  check(!hero.includes('Verified') && hero.includes('Practice awards zero XP'), 'Aggregate solved count never establishes demo completion');
  const sidebar = harness(AppSidebar, { isAdmin: false, isAuthenticated: true });
  check(!JSON.stringify(sidebar.render()).includes('"Admin"'), 'Student sidebar hides admin');
  const shell = harness(App().props.children.type, { currentRoute: 'admin', isAdmin: false, isAuthenticated: true, sessionGeneration: 123 });
  const shellTree = shell.render();
  check(elements(shellTree).find(e => e.type === 'main').key === '123', 'Account generation remounts cached view subtree');
  check(JSON.stringify(shellTree).includes('Administrator authorization required'), 'Direct admin route is gated');

  // Production admin component callbacks; no real external mutations.
  boundary.changeSessionIdentity('admin');
  const toasts = [];
  const admin = harness(AdminView, { isAdmin: true, addToast: t => toasts.push(t) }); disposables.push(admin);
  admin.render(); admin.flush(); await settle();
  const fixture = { id: 'server-uuid', slug: 'fresh', title: 'Fresh', validation_status: 'draft', is_published: false };
  const operationNames = ['createChallenge', 'updateChallenge', 'validateChallenge', 'publishChallenge', 'unpublishChallenge'];
  for (const code of [...errors, 'EXCEPTION']) {
    for (const name of operationNames) {
      api.admin[name] = async () => { if (code === 'EXCEPTION') throw new Error('unexpected admin'); return failure(code); };
      admin.slots[1] = [{ ...fixture, validation_status: name === 'publishChallenge' ? 'validated' : 'draft', is_published: name === 'unpublishChallenge' }]; admin.slots[5] = name === 'updateChallenge' ? fixture.id : null;
      admin.slots[4] = true;
      const tree = admin.render();
      const before = JSON.stringify(admin.slots[1]); const toastStart = toasts.length;
      if (name === 'createChallenge' || name === 'updateChallenge') {
        await elements(tree).find(e => e.type === 'form').props.onSubmit({ preventDefault() {} });
      } else {
        const title = { validateChallenge: 'Validate official solution', publishChallenge: 'Publish challenge', unpublishChallenge: 'Unpublish challenge' }[name];
        // Locate by actual button title (checked below; fallback fails rather than silently skips).
        const buttons = elements(tree).filter(e => e.type === 'button');
        const match = buttons.find(e => e.props.title?.toLowerCase().includes(name === 'validateChallenge' ? 'validat' : name === 'unpublishChallenge' ? 'unpublish' : 'publish'));
        assert(match, `Missing ${title} control`);
        await match.props.onClick();
      }
      check(JSON.stringify(admin.slots[1]) === before, `${name} ${code} does not change lifecycle`);
      check(toasts.slice(toastStart).some(t => t.type === 'error') && !toasts.slice(toastStart).some(t => t.type === 'success'), `${name} ${code} reports error only`);
    }
  }
  admin.slots[5] = null; admin.slots[4] = true;
  api.admin.createChallenge = async () => ok({ challenge_id: 'real-created-uuid', status: 'draft' });
  await elements(admin.render()).find(e => e.type === 'form').props.onSubmit({ preventDefault() {} });
  check(admin.slots[1][0].id === 'real-created-uuid', 'Create retains server ID');
  let usedId;
  api.admin.getChallenge = async id => { usedId = id; return ok({ ...fixture, id }); };
  const edit = elements(admin.render()).find(e => e.type === 'button' && e.props.title?.toLowerCase().includes('edit'));
  assert(edit); await edit.props.onClick();
  check(usedId === 'real-created-uuid' && admin.slots[5] === usedId, 'Subsequent edit uses real ID');
  for (const name of ['updateChallenge', 'validateChallenge', 'publishChallenge', 'unpublishChallenge']) {
    api.admin[name] = async id => { usedId = id; return ok({ message: 'Backend confirmed', status: 'draft' }); };
    api.admin.listChallenges = async () => ok({ challenges: [{ ...fixture, id: 'real-created-uuid', validation_status: name === 'publishChallenge' ? 'validated' : 'draft', is_published: name === 'unpublishChallenge' }] });
    admin.slots[1] = (await api.admin.listChallenges()).data.challenges;
    admin.slots[4] = true; admin.slots[5] = 'real-created-uuid';
    const tree = admin.render();
    if (name === 'updateChallenge') await elements(tree).find(e => e.type === 'form').props.onSubmit({ preventDefault() {} });
    else await elements(tree).find(e => e.type === 'button' && e.props.title?.toLowerCase().includes(name === 'validateChallenge' ? 'validat' : name === 'unpublishChallenge' ? 'unpublish' : 'publish')).props.onClick();
    check(usedId === 'real-created-uuid', `${name} uses server-created ID`);
  }
  const denied = harness(AdminView, { isAdmin: false, addToast() {} });
  check(!elements(denied.render()).some(e => e.type === 'form' || e.type === 'button'), 'Student admin view has no privileged controls');

  // Production Workspace callbacks surface adapter errors, never refresh/award.
  const workspaceToasts = []; let refreshed = 0;
  const workspace = harness(WorkspaceView, { activeChallengeId: 'x', isAuthenticated: true, addToast: t => workspaceToasts.push(t), refreshProfile: async () => { refreshed++; }, setAuthOpen() {}, setCurrentRoute() {} });
  disposables.push(workspace);
  workspace.render(); workspace.slots[0] = { ...fixture, examples: [], starterCode: '' }; workspace.slots[1] = false;
  for (const code of [...errors, 'EXCEPTION']) {
    api.submissions.submitSolution = async () => { if (code === 'EXCEPTION') throw new Error('unexpected workspace'); return failure(code); };
    const editor = elements(workspace.render()).find(e => typeof e.props?.onSubmit === 'function');
    await editor.props.onSubmit();
    check(workspace.slots[3] === 'SYSTEM_ERROR', `Workspace ${code} error state`);
  }
  check(refreshed === 0 && !workspaceToasts.some(t => t.type === 'success' || t.description?.includes('Server progress updated')), 'No false progress toast or refresh on failures');
  api.submissions.submitSolution = async () => ok({ submission_id: 'server-success', status: 'queued' });
  api.submissions.getSubmission = async () => ok({ status: 'accepted', xp_awarded: 40 });
  await elements(workspace.render()).find(e => typeof e.props?.onSubmit === 'function').props.onSubmit();
  await new Promise(r => setTimeout(r, 650));
  check(refreshed === 1 && workspace.slots[4]?.xpEarned === 40, 'Successful backend completion refreshes server profile');
  const stalePoll = deferred();
  api.submissions.getSubmission = () => stalePoll.promise;
  await elements(workspace.render()).find(e => typeof e.props?.onSubmit === 'function').props.onSubmit();
  await new Promise(r => setTimeout(r, 550));
  const toastCount = workspaceToasts.length;
  boundary.changeSessionIdentity('new-account');
  stalePoll.resolve(ok({ status: 'accepted', xp_awarded: 900 })); await settle();
  check(refreshed === 1 && workspaceToasts.length === toastCount, 'Delayed old-session scoring cannot refresh or toast');

  // Real API fetch wrapper with simulated HTTP responses, including refresh retry.
  boundary.changeSessionIdentity('client-test');
  supabase.auth.getSession = async () => ({ data: { session: { user: { id: 'client-test' }, access_token: 'simulated-not-a-real-token' } } });
  supabase.auth.refreshSession = async () => ({ data: { session: { user: { id: 'client-test' }, access_token: 'simulated-refresh' } } });
  let request = 0;
  globalThis.fetch = async () => new Response(JSON.stringify({ error: { code: request++ === 0 ? 'UNAUTHORIZED' : 'FORBIDDEN', message: 'denied' } }), { status: request === 1 ? 401 : 403 });
  check((await productionSubmit('id', 'code')).error.code === 'FORBIDDEN', '401 retry retains real 403 failure');
  const delayedHttp = deferred(); globalThis.fetch = () => delayedHttp.promise;
  const pendingHttp = productionSubmit('id', 'code'); await settle();
  boundary.changeSessionIdentity('later-client');
  delayedHttp.resolve(new Response(JSON.stringify({ submission_id: 'old' }), { status: 201 }));
  check((await pendingHttp).error.code === 'SESSION_CHANGED', 'HTTP adapter discards old account response');
  let authorization;
  globalThis.fetch = async (_url, options) => { authorization = options.headers.Authorization; return new Response(JSON.stringify({ submission_id: 'mock' }), { status: 201 }); };
  await productionSubmit('id', 'code');
  check(!authorization, 'SDK token for another identity is never attached');
  boundary.changeSessionIdentity(null);
  await productionSubmit('id', 'code');
  check(!authorization, 'Logged-out requests never attach a retained SDK token');

  boundary.changeSessionIdentity('authenticated-catalog');
  api.challenges.getChallenges = async () => failure('NETWORK_ERROR');
  check((await challengeApi.getChallenges()).length === 0, 'Authenticated catalog errors cannot show fixture completions');
  boundary.changeSessionIdentity(null);
  check((await challengeApi.getChallenges()).every(c => !c.solved && c.attemptsCount === 0), 'Practice fixtures never indicate scored completion');
  console.log(`PASS: ${count} production adapter/component assertions; sessions and admin transports simulated; practice/matrix real HTTP WASM.`);
} finally {
  for (const h of disposables) h.dispose();
  globalThis.fetch = originalFetch;
  globalThis.window = originalWindow;
  globalThis.document = originalDocument;
  await server.close();
  console.log('Temporary Vite server closed.');
}
