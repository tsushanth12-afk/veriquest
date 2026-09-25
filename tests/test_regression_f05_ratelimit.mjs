import { createServer } from 'vite';
import assert from 'node:assert';

async function testRateLimiterRegression() {
  console.log('========================================================================');
  console.log('REGRESSION 3: F-05 SLIDING WINDOW RATE LIMITER VERIFICATION');
  console.log('Threshold: 20 requests / 60 seconds per IP');
  console.log('========================================================================\n');

  const server = await createServer({
    server: { port: 5196 },
    configFile: './vite.config.ts',
  });
  await server.listen();
  console.log('Test server running on http://localhost:5196');

  try {
    const testIp = '198.51.100.42'; // Isolated IP for rate limit test
    const challenges = ['and-gate-demo', 'mux-2to1', '4-bit-counter', 'xor-gate'];
    const codes = {
      'and-gate-demo': 'module and_gate(input a, input b, output y); assign y = a & b; endmodule',
      'mux-2to1': 'module mux_2to1(input a, input b, input sel, output y); assign y = sel ? b : a; endmodule',
      '4-bit-counter': 'module sync_counter_4bit(input wire clk, input wire rst_n, input wire en, output reg [3:0] count); always @(posedge clk or negedge rst_n) begin if (!rst_n) count <= 4\'b0000; else if (en) count <= count + 1\'b1; end endmodule',
      'xor-gate': 'module xor_gate(input a, input b, output y); assign y = a ^ b; endmodule',
    };

    // ------------------------------------------------------------------------
    // Part A: Send 20 requests within window (Threshold = 20)
    // ------------------------------------------------------------------------
    console.log('--- Part A: Sending 20 requests within allowed threshold (All must succeed) ---');
    for (let i = 1; i <= 20; i++) {
      const ch = challenges[(i - 1) % challenges.length];
      const res = await fetch('http://localhost:5196/api/internal/evaluate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Forwarded-For': testIp,
        },
        body: JSON.stringify({ challengeId: ch, code: codes[ch] }),
      });

      assert.strictEqual(res.status, 200, `Request #${i} must return HTTP 200, got ${res.status}`);
      process.stdout.write(`.`);
    }
    console.log('\n  [PASS] 20 / 20 requests succeeded with HTTP 200.');

    // ------------------------------------------------------------------------
    // Part B & D: Burst beyond threshold (21st-23rd requests) across different challenges
    // ------------------------------------------------------------------------
    console.log('\n--- Part B & D: Sending requests beyond threshold across different challenges ---');
    for (let i = 21; i <= 23; i++) {
      const ch = challenges[(i - 1) % challenges.length];
      const res = await fetch('http://localhost:5196/api/internal/evaluate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Forwarded-For': testIp,
        },
        body: JSON.stringify({ challengeId: ch, code: codes[ch] }),
      });

      console.log(`  Request #${i} (${ch}) -> HTTP ${res.status}`);
      assert.strictEqual(res.status, 429, `Request #${i} must return HTTP 429`);

      const retryAfter = res.headers.get('retry-after');
      assert(retryAfter !== null, 'Response must include Retry-After header');
      const body = await res.json();
      assert.strictEqual(body.status, 'RATE_LIMITED');
      console.log(`    Status: ${body.status}, Retry-After: ${retryAfter}s, Message: ${body.message}`);
    }
    console.log('  [PASS] Rate limit strictly triggered 429 across different challenges with Retry-After.');

    // ------------------------------------------------------------------------
    // Part C: Verify normal service resumes when window resets
    // ------------------------------------------------------------------------
    console.log('\n--- Part C: Verifying normal service resumes after window reset ---');
    console.log('Waiting 61 seconds for the sliding rate-limit window to expire...');
    await new Promise((r) => setTimeout(r, 61000));

    const resResume = await fetch('http://localhost:5196/api/internal/evaluate', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Forwarded-For': testIp,
      },
      body: JSON.stringify({ challengeId: 'and-gate-demo', code: codes['and-gate-demo'] }),
    });

    console.log(`Post-window request status: HTTP ${resResume.status}`);
    assert.strictEqual(resResume.status, 200, 'Service must resume with HTTP 200 after window reset');
    const resumeBody = await resResume.json();
    assert.strictEqual(resumeBody.status, 'ACCEPTED');
    console.log('  [PASS] Normal service successfully resumed with HTTP 200 (ACCEPTED).');

    console.log('\n========================================================================');
    console.log('REGRESSION 3 (F-05 RATE LIMITER): ALL CHECKS PASSED');
    console.log('========================================================================');
  } finally {
    await server.close();
  }
}

testRateLimiterRegression().catch((err) => {
  console.error('Fatal rate limiter regression error:', err);
  process.exit(1);
});
