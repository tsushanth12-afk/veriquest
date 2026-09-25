import { createServer } from 'vite';
import assert from 'node:assert';
import fs from 'node:fs';

const CHALLENGES = [
  'and-gate-demo',
  'mux-2to1',
  '4-bit-counter',
  'xor-gate',
];

const TEST_CASES = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I'];

const EXPECTED_STATUSES = {
  A: 'ACCEPTED',
  B: 'FAILED',
  C: 'FAILED',
  D: 'COMPILATION_ERROR',
  E: 'ACCEPTED',
  F: 'COMPILATION_ERROR',
  G: 'FAILED',
  H: 'FAILED',
  I: 'ACCEPTED',
};

async function runRegressionMatrix() {
  console.log('========================================================================');
  console.log('REGRESSION 1: FULL 9-CASE TEST MATRIX (A-I) ACROSS ALL 4 CHALLENGES');
  console.log('Total evaluations: 36 (Paced in 2 rate-limit-safe batches of 18)');
  console.log('========================================================================\n');

  const server = await createServer({
    server: { port: 5197 },
    configFile: './vite.config.ts',
  });
  await server.listen();
  console.log('Live test server running on http://localhost:5197');

  const results = [];

  try {
    // Split challenges into two batches of 2 challenges (18 requests each)
    const batch1 = CHALLENGES.slice(0, 2); // and-gate-demo, mux-2to1 (18 requests)
    const batch2 = CHALLENGES.slice(2, 4); // 4-bit-counter, xor-gate (18 requests)

    console.log('\n>>> Starting Batch 1 (Challenges: ' + batch1.join(', ') + ') — 18 requests <<<');
    for (const chId of batch1) {
      console.log(`\nEvaluating Challenge: ${chId}`);
      for (const testId of TEST_CASES) {
        const expected = EXPECTED_STATUSES[testId];
        const res = await fetch('http://localhost:5197/api/internal/evaluate-matrix', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ challengeId: chId, testId }),
        });

        if (res.status === 429) {
          console.error(`Unexpected rate limit 429 on ${chId} Case ${testId}`);
          process.exit(1);
        }

        const data = await res.json();
        const passed = data.status === expected;
        console.log(`  [${passed ? 'PASS' : 'FAIL'}] Case ${testId}: Actual=${data.status}, Expected=${expected} (${data.testsPassed}/${data.totalTests} tests)`);

        results.push({
          challenge: chId,
          testId,
          expected,
          actual: data.status,
          testsPassed: data.testsPassed,
          totalTests: data.totalTests,
          passed,
        });
      }
    }

    console.log('\n--- Batch 1 complete (18/18 requests executed without 429). ---');
    console.log('Pacing pause: waiting 61 seconds for the 60s sliding window to clear...');
    await new Promise((r) => setTimeout(r, 61000));
    console.log('Sliding window cleared. Proceeding to Batch 2.');

    console.log('\n>>> Starting Batch 2 (Challenges: ' + batch2.join(', ') + ') — 18 requests <<<');
    for (const chId of batch2) {
      console.log(`\nEvaluating Challenge: ${chId}`);
      for (const testId of TEST_CASES) {
        const expected = EXPECTED_STATUSES[testId];
        const res = await fetch('http://localhost:5197/api/internal/evaluate-matrix', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ challengeId: chId, testId }),
        });

        if (res.status === 429) {
          console.error(`Unexpected rate limit 429 on ${chId} Case ${testId}`);
          process.exit(1);
        }

        const data = await res.json();
        const passed = data.status === expected;
        console.log(`  [${passed ? 'PASS' : 'FAIL'}] Case ${testId}: Actual=${data.status}, Expected=${expected} (${data.testsPassed}/${data.totalTests} tests)`);

        results.push({
          challenge: chId,
          testId,
          expected,
          actual: data.status,
          testsPassed: data.testsPassed,
          totalTests: data.totalTests,
          passed,
        });
      }
    }

    fs.mkdirSync('./scratch', { recursive: true });
    fs.writeFileSync('./scratch/matrix_regression_results.json', JSON.stringify(results, null, 2));

    const totalPassed = results.filter((r) => r.passed).length;
    console.log('\n========================================================================');
    console.log(`REGRESSION 1 SUMMARY: ${totalPassed} / ${results.length} evaluations passed.`);
    if (totalPassed === 36) {
      console.log('REGRESSION 1 (ALL 36 MATRIX CASES): PASSED ZERO REGRESSIONS');
    } else {
      console.log('REGRESSION 1: FAILED');
    }
    console.log('========================================================================');
  } finally {
    await server.close();
  }
}

runRegressionMatrix().catch((err) => {
  console.error('Fatal matrix regression error:', err);
  process.exit(1);
});
