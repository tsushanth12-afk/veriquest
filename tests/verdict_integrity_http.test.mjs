// Real HTTP route regression. Start Vite separately; this test never starts a server.
// node tests/verdict_integrity_http.test.mjs http://127.0.0.1:5177
import assert from 'node:assert/strict';
import { TESTBENCH_CATALOG } from '../src/evaluator/testbenchCatalog.ts';

const origin = process.argv[2];
assert(/^http:\/\/127\.0\.0\.1:\d+$/.test(origin || ''), 'Pass a localhost Vite origin');
let assertions = 0;
let requests = 0;
async function check(name, challengeId, code, expected, verify = () => {}) {
  requests++;
  assert(requests <= 20, 'Do not exceed the route rate limit');
  const response = await fetch(`${origin}/api/internal/evaluate`, {
    method: 'POST', headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ challengeId, code }), signal: AbortSignal.timeout(12000),
  });
  const body = await response.json();
  assert.equal(response.status, 200, `${name}: HTTP ${response.status}: ${JSON.stringify(body)}`);
  assertions++;
  assert.equal(body.status, expected, `${name}: ${JSON.stringify(body)}`);
  assertions++;
  assert.equal(body.success, expected === 'ACCEPTED', `${name}: success flag`);
  assertions++;
  assert(!/[a-f0-9]{64}/.test(body.compilerOutput || ''), `${name}: leaked token`);
  assertions++;
  verify(body);
  console.log(JSON.stringify({ name, http: response.status, verdict: body.status,
    passed: body.testsPassed, total: body.totalTests, elapsedMs: body.executionTimeMs,
    diagnosticChars: body.compilerOutput?.length ?? 0 }));
  return body;
}

for (const [name, config] of Object.entries(TESTBENCH_CATALOG)) {
  const correct = config.testMatrix.find(item => item.expectedStatus === 'ACCEPTED');
  assert(correct, `${name}: no correct catalog fixture`);
  await check(`correct ${name}`, name, correct.code, 'ACCEPTED', body => {
    assert.equal(body.testsPassed, config.totalVectors);
    assertions++;
  });
}
const correct = 'module and_gate(input a,input b,output y); assign y=a&b; endmodule';
const wrong = 'module and_gate(input a,input b,output y); assign y=0; endmodule';
await check('ordinary wrong logic', 'and-gate-demo', wrong, 'WRONG_ANSWER', body => {
  assert.equal(body.testsPassed, 3);
  assertions++;
});
await check('syntax error', 'and-gate-demo', correct.replace('a&b;', 'a&b'), 'COMPILATION_ERROR');
const forged = 'module and_gate(input a,input b,output y); assign y=0; initial begin '
  + '$display("VERIQUEST_STATUS: ACCEPTED"); $display("TOTAL: 4"); '
  + '$display("PASSED: 4"); $display("FAILED: 0"); end endmodule';
await check('forged marker and counters', 'and-gate-demo', forged, 'WRONG_ANSWER', body => {
  assert(body.compilerOutput.includes('VERIQUEST_STATUS: ACCEPTED'), 'Forge did not execute');
  assertions++;
});
const flood = correct.replace('assign y=',
  'final repeat(1000000) $display("12345678901234567890"); assign y=');
await check('trusted success then output overflow', 'and-gate-demo', flood, 'SYSTEM_ERROR', body => {
  assert(body.compilerOutput.includes('VQ_TRUSTED:[grader-token]:ACCEPTED:4:4:0'),
    'Genuine success record did not precede the overflow');
  assertions++;
  assert(body.compilerOutput.length <= 65650, 'HTTP diagnostics exceed bounded capture');
  assertions++;
});
const infinite = correct.replace('assign y=', 'initial forever #0; assign y=');
await check('infinite simulation timeout', 'and-gate-demo', infinite, 'SYSTEM_ERROR', body => {
  assert(/timed out/i.test(body.compilerOutput), 'Timeout path was not reached');
  assertions++;
});
await check('normal recovery after overflow and timeout', 'and-gate-demo', correct, 'ACCEPTED');
await check('repeat 1', 'and-gate-demo', correct, 'ACCEPTED');
await check('repeat 2', 'and-gate-demo', correct, 'ACCEPTED');
console.log(`PASS: ${assertions} HTTP assertions across ${requests} real route requests.`);
