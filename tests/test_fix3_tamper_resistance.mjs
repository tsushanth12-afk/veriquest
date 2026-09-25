import { createServer } from 'vite';
import assert from 'node:assert';

class StorageMock {
  constructor() {
    this.store = new Map();
  }
  getItem(key) {
    return this.store.has(key) ? this.store.get(key) : null;
  }
  setItem(key, val) {
    this.store.set(key, String(val));
  }
  removeItem(key) {
    this.store.delete(key);
  }
  clear() {
    this.store.clear();
  }
}

const mockLocalStorage = new StorageMock();
const mockSessionStorage = new StorageMock();

globalThis.window = {
  localStorage: mockLocalStorage,
  sessionStorage: mockSessionStorage,
};

async function testFix3() {
  console.log('========================================================================');
  console.log('VERIFYING FIX 3 (F-04): CLIENT-SIDE XP TAMPER RESISTANCE STOPGAP');
  console.log('========================================================================\n');

  const server = await createServer({
    server: { port: 5198 },
    configFile: './vite.config.ts',
  });

  try {
    const submissionApiModule = await server.ssrLoadModule('./src/api/submissionApi.ts');
    const { getCompletedChallenges, recordChallengeCompleted } = submissionApiModule;

    const CHALLENGES = [
      { id: 'and-gate-demo', xp: 50 },
      { id: 'mux-2to1', xp: 40 },
      { id: '4-bit-counter', xp: 60 },
      { id: 'xor-gate', xp: 30 },
    ];

    // ----------------------------------------------------------------------------
    // 1. Demonstrate OLD vs NEW Behavior on Storage Deletion (localStorage.clear())
    // ----------------------------------------------------------------------------
    console.log('--- 1. Comparison: OLD Behavior vs NEW Tamper-Resistant Stopgap ---');

    console.log('\n[OLD BEHAVIOR EXPLANATION]');
    console.log('Under the old single-storage implementation:');
    console.log('  1. Student solves "and-gate-demo" -> receives 50 XP.');
    console.log('  2. Student executes localStorage.clear() in DevTools.');
    console.log('  3. getCompletedChallenges() reads empty localStorage -> returns empty set.');
    console.log('  4. Student resubmits "and-gate-demo" -> alreadyCompleted is FALSE -> receives 50 XP AGAIN.');
    console.log('  -> Exploit succeeded: unlimited repeat XP via single-click localStorage.clear().');

    console.log('\n[NEW BEHAVIOR TEST ON LIVE CODE]');
    // Reset storage for clean test
    mockLocalStorage.clear();
    mockSessionStorage.clear();

    // First submission
    const chId = 'and-gate-demo';
    console.log(`Step 1: First solve of ${chId}...`);
    assert.strictEqual(getCompletedChallenges().has(chId), false, 'Initially not completed');
    recordChallengeCompleted(chId);
    assert.strictEqual(getCompletedChallenges().has(chId), true, 'Marked completed');
    console.log(`  -> Initial completion recorded: ${chId} is marked completed.`);

    // Idempotent resubmission
    console.log('Step 2: Resubmitting while storage is intact...');
    const alreadyCompletedNormal = getCompletedChallenges().has(chId);
    const xpAwardedNormal = alreadyCompletedNormal ? 0 : 50;
    console.log(`  -> alreadyCompleted: ${alreadyCompletedNormal}, XP Awarded: ${xpAwardedNormal}`);
    assert.strictEqual(xpAwardedNormal, 0, 'Normal resubmission must award 0 XP');
    console.log('  [PASS] Existing idempotency verified: 0 XP on resubmit.');

    // TAMPERING CLASS A: Clear localStorage
    console.log('\nStep 3: Tampering Class A — Simulating localStorage.clear() in active session...');
    mockLocalStorage.clear();
    assert.strictEqual(mockLocalStorage.getItem('veriquest_completed_challenge_ids'), null);
    console.log('  -> localStorage has been completely cleared!');

    console.log('Step 4: Attempting repeat submission after localStorage wipe...');
    const completedAfterWipe = getCompletedChallenges();
    const isStillMarkedCompleted = completedAfterWipe.has(chId);
    const xpAfterWipe = isStillMarkedCompleted ? 0 : 50;
    console.log(`  -> Tamper detection result: Challenge still completed = ${isStillMarkedCompleted}`);
    console.log(`  -> XP Awarded on resubmission: ${xpAfterWipe} XP`);
    assert.strictEqual(isStillMarkedCompleted, true, 'Dual-tier session store must restore completed state');
    assert.strictEqual(xpAfterWipe, 0, 'Must award 0 XP after localStorage wipe');
    assert.notStrictEqual(mockLocalStorage.getItem('veriquest_completed_challenge_ids'), null, 'localStorage must be auto-restored');
    console.log('  [PASS] Tampering Class A DETECTED & RESTORED: 0 XP awarded, exploit defeated.');

    // ----------------------------------------------------------------------------
    // 2. Tampering Class B: Modify Stored State Without Clearing (JSON edit / deletion)
    // ----------------------------------------------------------------------------
    console.log('\n--- 2. Tampering Class B — Modification of Stored State Without Clearing ---');
    console.log('Step 1: Student manually modifies localStorage to remove "and-gate-demo" but keeps corrupted state...');
    mockLocalStorage.setItem('veriquest_completed_challenge_ids', JSON.stringify([])); // cleared the array
    // Notice the checksum in localStorage still belongs to previous state or is invalid!

    console.log('Step 2: Calling getCompletedChallenges() with tampered localStorage payload...');
    const completedAfterMod = getCompletedChallenges();
    const isProtectedFromMod = completedAfterMod.has(chId);
    const xpAfterMod = isProtectedFromMod ? 0 : 50;
    console.log(`  -> Checksum mismatch detected! Protected: ${isProtectedFromMod}, XP Awarded: ${xpAfterMod}`);
    assert.strictEqual(isProtectedFromMod, true, 'Must detect modification and restore from session ledger');
    assert.strictEqual(xpAfterMod, 0, 'Must award 0 XP on modified state resubmission');
    console.log('  [PASS] Tampering Class B DETECTED & RESTORED: 0 XP awarded.');

    // ----------------------------------------------------------------------------
    // 3. Test Across All 4 Challenges
    // ----------------------------------------------------------------------------
    console.log('\n--- 3. Testing Tamper-Resistance Stopgap Across All 4 Challenges ---');

    for (const ch of CHALLENGES) {
      mockLocalStorage.clear();
      mockSessionStorage.clear();

      // 1. Initial complete
      recordChallengeCompleted(ch.id);
      assert.strictEqual(getCompletedChallenges().has(ch.id), true);

      // 2. Clear localStorage
      mockLocalStorage.clear();

      // 3. Verify restored
      const resSet = getCompletedChallenges();
      assert.strictEqual(resSet.has(ch.id), true, `Challenge ${ch.id} must be restored after wipe`);
      console.log(`  [PASS] ${ch.id}: Deletion tampering prevented, completion restored, 0 duplicate XP.`);
    }

    console.log('\n========================================================================');
    console.log('FIX 3 (F-04) VERIFICATION: ALL TAMPER RESISTANCE TESTS PASSED');
    console.log('========================================================================');
  } finally {
    await server.close();
  }
}

testFix3().catch(err => {
  console.error('Fatal error during Fix 3 verification:', err);
  process.exit(1);
});
