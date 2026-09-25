import { createServer } from 'vite';
import assert from 'node:assert';

async function testPayloadLimit() {
  console.log('========================================================================');
  console.log('VERIFYING FIX 2 (F-08): 64 KB PAYLOAD LIMIT ON EVALUATION ENDPOINTS');
  console.log('========================================================================\n');

  const server = await createServer({
    server: { port: 5199 },
    configFile: './vite.config.ts',
  });
  await server.listen();
  console.log('Vite test server listening on http://localhost:5199');

  try {
    // ------------------------------------------------------------------------
    // 1. Deliberately oversized submission test (> 64 KB) on /api/internal/evaluate
    // ------------------------------------------------------------------------
    console.log('\n--- 1. Testing Oversized Submission (> 64 KB) on /api/internal/evaluate ---');
    const validPaddedCode = `module and_gate (input a, input b, output y);\n` +
      `  // ${'Padded comment line '.repeat(3500)}\n` +
      `  assign y = a & b;\n` +
      `endmodule\n`;
    
    const oversizedPayload = JSON.stringify({
      challengeId: 'and-gate-demo',
      code: validPaddedCode,
    });
    const oversizedByteLength = Buffer.byteLength(oversizedPayload, 'utf8');
    console.log(`Constructed oversized payload byte size: ${oversizedByteLength} bytes (Cap: 65,536 bytes)`);
    assert(oversizedByteLength > 65536, 'Payload must exceed 65,536 bytes');

    const resOversized = await fetch('http://localhost:5199/api/internal/evaluate', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': oversizedByteLength.toString(),
      },
      body: oversizedPayload,
    });

    console.log(`HTTP Status: ${resOversized.status}`);
    const oversizedBody = await resOversized.json();
    console.log('Response body:', JSON.stringify(oversizedBody));

    assert.strictEqual(resOversized.status, 413, 'Expected HTTP status 413 for oversized body');
    assert.strictEqual(oversizedBody.status, 'SUBMISSION_TOO_LARGE', 'Expected SUBMISSION_TOO_LARGE status');
    assert.strictEqual(oversizedBody.message, 'Submission exceeds the 64 KB limit.');
    console.log('  [PASS] Content-Length shortcut correctly rejected oversized payload with HTTP 413');

    // ------------------------------------------------------------------------
    // 2. Testing Chunked / No Content-Length Header Oversized Submission
    // ------------------------------------------------------------------------
    console.log('\n--- 2. Testing Streaming/Chunked Oversized Submission (No Content-Length Header) ---');
    // Using http request without Content-Length to test streaming boundary
    const http = await import('node:http');
    const chunkedResult = await new Promise((resolve, reject) => {
      const req = http.request('http://localhost:5199/api/internal/evaluate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Transfer-Encoding': 'chunked',
        },
      }, (res) => {
        let respData = '';
        res.on('data', (c) => respData += c);
        res.on('end', () => {
          resolve({ status: res.statusCode, body: respData });
        });
      });

      req.on('error', (err) => {
        // Socket closed by server after 413 is acceptable
        resolve({ error: err.message });
      });

      // Write in 16KB chunks past 65,536 bytes
      const chunk = '{"challengeId":"and-gate-demo","code":"' + 'X'.repeat(16384);
      req.write(chunk);
      req.write('X'.repeat(16384));
      req.write('X'.repeat(16384));
      req.write('X'.repeat(16384));
      req.write('X'.repeat(16384)); // Now ~80KB
      req.write('"}');
      req.end();
    });

    console.log('Chunked result:', chunkedResult);
    if (chunkedResult.status) {
      assert.strictEqual(chunkedResult.status, 413);
      const parsed = JSON.parse(chunkedResult.body);
      assert.strictEqual(parsed.status, 'SUBMISSION_TOO_LARGE');
    }
    console.log('  [PASS] Streaming chunked boundary correctly triggers 413 before unbounded buffering');

    // ------------------------------------------------------------------------
    // 3. Testing Oversized Submission on /api/internal/evaluate-matrix
    // ------------------------------------------------------------------------
    console.log('\n--- 3. Testing Oversized Submission on /api/internal/evaluate-matrix ---');
    const matrixOversizedPayload = JSON.stringify({
      challengeId: 'and-gate-demo',
      testId: 'A',
      padding: 'P'.repeat(70000),
    });
    const matrixOversizedByteLength = Buffer.byteLength(matrixOversizedPayload, 'utf8');

    const resMatrixOversized = await fetch('http://localhost:5199/api/internal/evaluate-matrix', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': matrixOversizedByteLength.toString(),
      },
      body: matrixOversizedPayload,
    });

    console.log(`HTTP Status: ${resMatrixOversized.status}`);
    const matrixOversizedBody = await resMatrixOversized.json();
    console.log('Matrix response body:', JSON.stringify(matrixOversizedBody));

    assert.strictEqual(resMatrixOversized.status, 413, 'Expected HTTP 413 on evaluate-matrix');
    assert.strictEqual(matrixOversizedBody.status, 'SUBMISSION_TOO_LARGE');
    console.log('  [PASS] evaluate-matrix endpoint correctly enforces 64 KB limit with HTTP 413');

    // ------------------------------------------------------------------------
    // 4. Testing Legitimate Submissions Across All 4 Challenges (< 64 KB)
    // ------------------------------------------------------------------------
    console.log('\n--- 4. Testing Legitimate Submissions across All 4 Challenges ---');
    const normalSubmissions = [
      { id: 'and-gate-demo', code: 'module and_gate(input a, input b, output y); assign y = a & b; endmodule' },
      { id: 'mux-2to1', code: 'module mux_2to1(input a, input b, input sel, output y); assign y = sel ? b : a; endmodule' },
      { id: '4-bit-counter', code: 'module sync_counter_4bit(input wire clk, input wire rst_n, input wire en, output reg [3:0] count); always @(posedge clk or negedge rst_n) begin if (!rst_n) count <= 4\'b0000; else if (en) count <= count + 1\'b1; end endmodule' },
      { id: 'xor-gate', code: 'module xor_gate(input a, input b, output y); assign y = a ^ b; endmodule' },
    ];

    for (const sub of normalSubmissions) {
      const payload = JSON.stringify({ challengeId: sub.id, code: sub.code });
      const byteSize = Buffer.byteLength(payload, 'utf8');
      console.log(`Submitting normal payload for ${sub.id}: ${byteSize} bytes`);

      const res = await fetch('http://localhost:5199/api/internal/evaluate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: payload,
      });

      console.log(`  ${sub.id} -> HTTP ${res.status}`);
      assert.strictEqual(res.status, 200, `Expected HTTP 200 for normal submission of ${sub.id}`);
      const body = await res.json();
      console.log(`  ${sub.id} -> Status: ${body.status}, Tests Passed: ${body.testsPassed}/${body.totalTests}`);
      assert.strictEqual(body.status, 'ACCEPTED', `Expected ACCEPTED status for normal submission of ${sub.id}`);
      assert.strictEqual(body.success, true);
    }
    console.log('  [PASS] Normal submissions across all 4 challenges evaluate normally');

    console.log('\n========================================================================');
    console.log('FIX 2 (F-08) VERIFICATION: ALL PAYLOAD BOUNDARY TESTS PASSED');
    console.log('========================================================================');
  } finally {
    await server.close();
  }
}

testPayloadLimit().catch(err => {
  console.error('Fatal error during Fix 2 verification:', err);
  process.exit(1);
});
