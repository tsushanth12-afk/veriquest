// ============================================================================
// VeriQuest Security & Contract Invariants Test Suite (Group E)
// Validates:
// 1. Cross-user isolation & protected field immutability
// 2. Secret leakage defense (official_solution & hidden_testbench omission)
// 3. Command injection & path traversal sanitization
// 4. Payload bounds (64 KB cap)
// 5. Rate limiting sliding window mathematical enforcement
// 6. Section 7 Evaluator error boundary rules
// 7. Client-side polling timeout cap (60s)
// ============================================================================

import assert from 'node:assert';

console.log('====================================================');
console.log('VERIQUEST — GROUP E SECURITY & INVARIANT TEST SUITE');
console.log('====================================================\n');

let passedTests = 0;
let totalTests = 0;

function test(name, fn) {
  totalTests++;
  try {
    fn();
    console.log(`  [PASS] ${name}`);
    passedTests++;
  } catch (err) {
    console.error(`  [FAIL] ${name}:`, err.message);
  }
}

// ----------------------------------------------------------------------------
// TEST SUITE 1: Confidential Schema Isolation (Master Prompt Section 8)
// ----------------------------------------------------------------------------
console.log('\n--- 1. Confidential Schema Isolation (Section 8) ---');

const PUBLIC_CHALLENGE_KEYS = new Set([
  'id', 'slug', 'title', 'description', 'category', 'difficulty',
  'level', 'xp', 'estimated_minutes', 'starter_code', 'input_description',
  'output_description', 'constraints', 'io_pins', 'examples', 'hints',
  'learning_objective', 'solved', 'attempts_count', 'acceptance_rate',
]);

const FORBIDDEN_SECRET_KEYS = [
  'official_solution',
  'hidden_testbench',
  'evaluator_type',
  'execution_profile',
  'private_notes',
];

test('Public challenge schema strictly forbids secret fields by design', () => {
  FORBIDDEN_SECRET_KEYS.forEach((secret) => {
    assert.strictEqual(
      PUBLIC_CHALLENGE_KEYS.has(secret),
      false,
      `PublicChallenge schema leaked forbidden key: ${secret}`
    );
  });
});

test('Simulated public API challenge payload contains zero secret keys', () => {
  const publicPayload = {
    id: 'demo-001',
    slug: 'and-gate-demo',
    title: 'Two-Input AND Gate (Development Demo)',
    description: 'Implement a two-input AND gate.',
    category: 'Fundamentals',
    difficulty: 'Easy',
    level: 1,
    xp: 50,
    starter_code: 'module and_gate(input a, input b, output y);\n  // Your code\nendmodule',
    constraints: ['Use basic Verilog gates or assign operator.'],
    io_pins: [{ name: 'a', direction: 'input', width: '1', description: 'Input A' }],
    examples: [{ input: 'a=1, b=1', expectedOutput: 'y=1' }],
  };

  const payloadKeys = Object.keys(publicPayload);
  FORBIDDEN_SECRET_KEYS.forEach((secret) => {
    assert.strictEqual(
      payloadKeys.includes(secret),
      false,
      `Public payload contained forbidden secret field: ${secret}`
    );
  });
});

// ----------------------------------------------------------------------------
// TEST SUITE 2: Protected Field Immutability (Master Prompt Section 1)
// ----------------------------------------------------------------------------
console.log('\n--- 2. Protected Field Immutability (Section 1) ---');

const ALLOWED_PROFILE_FIELDS = new Set(['display_name', 'bio', 'avatar_url']);
const PROTECTED_PROFILE_FIELDS = [
  'id', 'xp', 'level', 'role', 'is_admin', 'is_published', 'completed',
  'current_streak', 'longest_streak', 'total_solved', 'easy_solved',
  'medium_solved', 'hard_solved', 'total_attempts', 'created_at', 'updated_at',
  'official_solution', 'hidden_testbench', 'execution_profile', 'leaderboard_rank'
];

function filterProfileUpdate(patchBody) {
  const updates = {};
  for (const [key, value] of Object.entries(patchBody)) {
    if (ALLOWED_PROFILE_FIELDS.has(key)) {
      updates[key] = value;
    }
  }
  return updates;
}

test('Malicious PATCH attempting to modify XP or Admin role is stripped', () => {
  const maliciousPatch = {
    display_name: 'Ethical Hacker',
    xp: 999999,
    level: 99,
    role: 'superadmin',
    is_admin: true,
    total_solved: 500,
    official_solution: 'malicious-overwrite',
  };

  const filtered = filterProfileUpdate(maliciousPatch);
  assert.strictEqual(filtered.display_name, 'Ethical Hacker');
  assert.strictEqual(filtered.xp, undefined);
  assert.strictEqual(filtered.level, undefined);
  assert.strictEqual(filtered.role, undefined);
  assert.strictEqual(filtered.is_admin, undefined);
  assert.strictEqual(filtered.total_solved, undefined);
  assert.strictEqual(filtered.official_solution, undefined);
  assert.strictEqual(Object.keys(filtered).length, 1);
});

// ----------------------------------------------------------------------------
// TEST SUITE 3: Command Injection & Path Traversal Defense (Section 1 & 2)
// ----------------------------------------------------------------------------
console.log('\n--- 3. Command Injection & Path Traversal Defense ---');

const DANGEROUS_PATTERNS = [
  '; rm -rf /',
  '| cat /etc/passwd',
  '& netstat -an',
  '`whoami`',
  '$(id)',
  '../../etc/shadow',
  '..\\..\\windows\\system32',
];

function sanitizeFilename(name) {
  // Disallow directory traversal or shell metacharacters in file/module names
  if (/[\/\\;&|`$]/.test(name) || name.includes('..')) {
    throw new Error('Invalid filename or module identifier');
  }
  return name.replace(/[^a-zA-Z0-9_-]/g, '');
}

test('Sanitizer blocks directory traversal and command injection tokens', () => {
  DANGEROUS_PATTERNS.forEach((pattern) => {
    assert.throws(
      () => sanitizeFilename(pattern),
      /Invalid filename/,
      `Failed to reject malicious pattern: ${pattern}`
    );
  });
});

test('Sanitizer preserves valid alphanumeric Verilog module identifiers', () => {
  assert.strictEqual(sanitizeFilename('and_gate'), 'and_gate');
  assert.strictEqual(sanitizeFilename('alu_32bit'), 'alu_32bit');
  assert.strictEqual(sanitizeFilename('shift-reg'), 'shift-reg');
});

// Compiler output sanitizer: strips internal sandbox paths from compiler error logs
function sanitizeCompilerOutput(output) {
  return output
    .replace(/\/workspace\/testbench\.v:?/g, '[internal_testbench]:')
    .replace(/\/workspace\/solution\.v:?/g, 'solution.v:')
    .replace(/\/tmp\/[a-zA-Z0-9_-]+/g, '[sandbox_temp]')
    .replace(/public\.[a-zA-Z0-9_]+/g, '[db_table]')
    .replace(/private\.[a-zA-Z0-9_]+/g, '[db_secret]');
}

test('Compiler output sanitizer strips testbench.v and private schemas', () => {
  const rawLog = '/workspace/testbench.v:45: syntax error in private.challenge_secrets near solution.v';
  const cleanLog = sanitizeCompilerOutput(rawLog);
  assert.strictEqual(cleanLog.includes('/workspace/testbench.v'), false);
  assert.strictEqual(cleanLog.includes('private.challenge_secrets'), false);
  assert.strictEqual(cleanLog.includes('[internal_testbench]:45'), true);
});

// ----------------------------------------------------------------------------
// TEST SUITE 4: Payload Bounds (Section 2 - 64 KB Max)
// ----------------------------------------------------------------------------
console.log('\n--- 4. Payload Bounds (Section 2) ---');

const MAX_PAYLOAD_BYTES = 65536;

function validatePayloadSize(code) {
  const bytes = Buffer.byteLength(code, 'utf8');
  if (bytes > MAX_PAYLOAD_BYTES) {
    throw new Error(`Payload exceeds maximum allowed size of ${MAX_PAYLOAD_BYTES} bytes (received ${bytes} bytes)`);
  }
  return true;
}

test('Payload of 64 KB (65,536 bytes) is permitted', () => {
  const code = 'a'.repeat(65536);
  assert.strictEqual(validatePayloadSize(code), true);
});

test('Payload of 64 KB + 1 byte (65,537 bytes) is rejected', () => {
  const oversizedCode = 'a'.repeat(65537);
  assert.throws(() => validatePayloadSize(oversizedCode), /Payload exceeds maximum allowed size/);
});

// ----------------------------------------------------------------------------
// TEST SUITE 5: Rate Limiting Enforcement (Section 6)
// ----------------------------------------------------------------------------
console.log('\n--- 5. Rate Limiting Sliding Window (Section 6) ---');

class SlidingWindowRateLimiter {
  constructor() {
    this.buckets = new Map();
  }

  check(key, maxRequests, windowSeconds, nowSeconds = Date.now() / 1000) {
    const cutoff = nowSeconds - windowSeconds;
    let timestamps = this.buckets.get(key) || [];
    timestamps = timestamps.filter((t) => t > cutoff);

    if (timestamps.length >= maxRequests) {
      this.buckets.set(key, timestamps);
      return false; // rate limited
    }

    timestamps.push(nowSeconds);
    this.buckets.set(key, timestamps);
    return true; // allowed
  }
}

test('Login rate limit: strictly enforces 5 attempts / 5 min / IP', () => {
  const limiter = new SlidingWindowRateLimiter();
  const ip = '192.168.1.50';
  const now = 10000;

  for (let i = 1; i <= 5; i++) {
    assert.strictEqual(
      limiter.check(`login:${ip}`, 5, 300, now + i),
      true,
      `Attempt ${i} should be allowed`
    );
  }

  // 6th attempt within window fails
  assert.strictEqual(
    limiter.check(`login:${ip}`, 5, 300, now + 6),
    false,
    '6th attempt within 5 minutes must be rate limited'
  );

  // After 301 seconds, attempts recover
  assert.strictEqual(
    limiter.check(`login:${ip}`, 5, 300, now + 307),
    true,
    'Attempt after 300s window expiry should be allowed'
  );
});

test('Signup rate limit: strictly enforces 3 / hour / IP', () => {
  const limiter = new SlidingWindowRateLimiter();
  const ip = '192.168.1.51';
  const now = 20000;

  for (let i = 1; i <= 3; i++) {
    assert.strictEqual(limiter.check(`signup:${ip}`, 3, 3600, now + i), true);
  }
  assert.strictEqual(limiter.check(`signup:${ip}`, 3, 3600, now + 4), false);
});

test('Submission rate limit: strictly enforces 10 / min / user', () => {
  const limiter = new SlidingWindowRateLimiter();
  const userId = 'usr-abc-123';
  const now = 30000;

  for (let i = 1; i <= 10; i++) {
    assert.strictEqual(limiter.check(`sub:${userId}`, 10, 60, now + i), true);
  }
  assert.strictEqual(limiter.check(`sub:${userId}`, 10, 60, now + 11), false);
});

test('Admin action rate limit: strictly enforces 20 / min / admin user', () => {
  const limiter = new SlidingWindowRateLimiter();
  const adminId = 'adm-xyz-789';
  const now = 40000;

  for (let i = 1; i <= 20; i++) {
    assert.strictEqual(limiter.check(`adm:${adminId}`, 20, 60, now + i), true);
  }
  assert.strictEqual(limiter.check(`adm:${adminId}`, 20, 60, now + 21), false);
});

// ----------------------------------------------------------------------------
// TEST SUITE 6: Section 7 Evaluator Error Boundary Rules
// ----------------------------------------------------------------------------
console.log('\n--- 6. Section 7 Evaluator Error Boundary Rules ---');

function evaluateSimulationOutput(rawOutput, returnCode, timeout = false) {
  if (timeout) {
    return { status: 'TIMEOUT', countsAsAttempt: true, penalty: 1 };
  }
  if (returnCode !== 0) {
    return { status: 'COMPILATION_ERROR', countsAsAttempt: true, penalty: 1 };
  }

  // Parse structured marker
  const resultMatch = rawOutput.match(/VERIQUEST_STATUS:\s*(ACCEPTED|WRONG_ANSWER)/);
  if (!resultMatch) {
    // Malformed or missing evaluator output -> SYSTEM_ERROR, 0 attempt penalty
    return { status: 'SYSTEM_ERROR', countsAsAttempt: false, penalty: 0 };
  }

  const status = resultMatch[1];
  return { status, countsAsAttempt: true, penalty: 1 };
}

test('Malformed simulator output produces SYSTEM_ERROR with 0 penalty', () => {
  const malformed = 'VCD info: dumpfile dump.vcd opened for output.\nSimulation started... Segment fault';
  const result = evaluateSimulationOutput(malformed, 0, false);
  assert.strictEqual(result.status, 'SYSTEM_ERROR');
  assert.strictEqual(result.countsAsAttempt, false);
  assert.strictEqual(result.penalty, 0);
});

test('Accepted output counts as attempt and rewards success', () => {
  const accepted = 'VERIQUEST_STATUS: ACCEPTED\nVQ_PASSED: 4\nVQ_FAILED: 0';
  const result = evaluateSimulationOutput(accepted, 0, false);
  assert.strictEqual(result.status, 'ACCEPTED');
  assert.strictEqual(result.countsAsAttempt, true);
});

test('Wrong answer counts as normal attempt', () => {
  const failed = 'VERIQUEST_STATUS: WRONG_ANSWER\nVQ_PASSED: 3\nVQ_FAILED: 1';
  const result = evaluateSimulationOutput(failed, 0, false);
  assert.strictEqual(result.status, 'WRONG_ANSWER');
  assert.strictEqual(result.countsAsAttempt, true);
});

// ----------------------------------------------------------------------------
// TEST SUITE 7: Client Polling Timeout Cap (Section 6)
// ----------------------------------------------------------------------------
console.log('\n--- 7. Polling Timeout Cap ---');

test('Client polling enforces 60-second maximum cap', () => {
  const MAX_POLL_DURATION_MS = 60000;
  const startTime = 100000;

  function shouldStopPolling(currentTime) {
    return currentTime - startTime >= MAX_POLL_DURATION_MS;
  }

  assert.strictEqual(shouldStopPolling(100000 + 30000), false);
  assert.strictEqual(shouldStopPolling(100000 + 59000), false);
  assert.strictEqual(shouldStopPolling(100000 + 60000), true);
  assert.strictEqual(shouldStopPolling(100000 + 90000), true);
});

// ----------------------------------------------------------------------------
// TEST SUITE 8: Verilog Syntax & Semicolon Termination Validation
// ----------------------------------------------------------------------------
console.log('\n--- 8. Verilog Syntax & Semicolon Termination Validation ---');

function validateVerilogSyntax(code) {
  const cleanWithLines = code.replace(/\/\*[\s\S]*?\*\//g, (match) => {
    return '\n'.repeat((match.match(/\n/g) || []).length);
  });
  const rawLines = cleanWithLines.split('\n');
  const lines = rawLines.map((line) => line.replace(/\/\/.*/, ''));
  const fullClean = lines.join(' ').replace(/\s+/g, ' ').trim();

  if (!fullClean.includes('module') || !fullClean.includes('endmodule')) {
    return { isValid: false, error: 'missing module or endmodule' };
  }

  let paren = 0, bracket = 0, brace = 0;
  for (let i = 0; i < fullClean.length; i++) {
    const ch = fullClean[i];
    if (ch === '(') paren++;
    else if (ch === ')') paren--;
    else if (ch === '[') bracket++;
    else if (ch === ']') bracket--;
    else if (ch === '{') brace++;
    else if (ch === '}') brace--;
    if (paren < 0 || bracket < 0 || brace < 0) return { isValid: false, error: 'unexpected delimiter' };
  }
  if (paren !== 0 || bracket !== 0 || brace !== 0) return { isValid: false, error: 'unmatched delimiters' };

  // Check module header termination
  const modKeywordIdx = fullClean.indexOf('module');
  const afterModule = fullClean.slice(modKeywordIdx + 6).trim();
  const idMatch = afterModule.match(/^([A-Za-z_][A-Za-z0-9_]*)/);
  if (!idMatch) return { isValid: false, error: 'missing module identifier' };

  function skipParens(str) {
    if (!str.startsWith('(')) return 0;
    let depth = 0;
    for (let k = 0; k < str.length; k++) {
      if (str[k] === '(') depth++;
      else if (str[k] === ')') {
        depth--;
        if (depth === 0) return k + 1;
      }
    }
    return 0;
  }

  let cursor = afterModule.slice(idMatch[0].length).trim();
  if (cursor.startsWith('#')) {
    cursor = cursor.slice(1).trim();
    const plen = skipParens(cursor);
    if (plen > 0) cursor = cursor.slice(plen).trim();
  }
  if (cursor.startsWith('(')) {
    const portLen = skipParens(cursor);
    if (portLen > 0) cursor = cursor.slice(portLen).trim();
  }

  if (!cursor.startsWith(';')) {
    return { isValid: false, error: "missing ';' after module header" };
  }

  // Check statement semicolon termination
  let inStatement = false;
  let stmtKeyword = '';
  const statementStarters = ['assign', 'wire', 'reg', 'input', 'output', 'inout', 'and', 'or', 'nand', 'nor', 'xor', 'xnor', 'not'];
  let inModuleHeader = true;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim();
    if (!line) continue;
    const tokens = line.split(/(\s+|[;(),=+\-*&|^~!<>[\]{}])/).filter((t) => t && t.trim());

    for (let j = 0; j < tokens.length; j++) {
      const tok = tokens[j];
      if (inModuleHeader) {
        if (tok === ';') inModuleHeader = false;
        continue;
      }
      if (tok === 'endmodule') {
        if (inStatement) return { isValid: false, error: "missing ';' before 'endmodule'" };
        continue;
      }
      if (!inStatement) {
        if (statementStarters.includes(tok)) {
          inStatement = true;
          stmtKeyword = tok;
        }
      } else {
        if (tok === ';') {
          inStatement = false;
          stmtKeyword = '';
        } else if (statementStarters.includes(tok)) {
          return { isValid: false, error: `missing ';' before '${tok}'` };
        }
      }
    }
  }

  if (inStatement) return { isValid: false, error: `missing ';' at end of ${stmtKeyword}` };
  return { isValid: true };
}

test('Verilog code with missing semicolon is strictly rejected', () => {
  const codeWithoutSemicolon = `
module and_gate (
    input  wire a,
    input  wire b,
    output wire y
);
    assign y = a & b
endmodule
  `;
  const res = validateVerilogSyntax(codeWithoutSemicolon);
  assert.strictEqual(res.isValid, false);
  assert.match(res.error, /missing ';'/);
});

test('Verilog code with correct semicolon is accepted', () => {
  const validCode = `
module and_gate (
    input  wire a,
    input  wire b,
    output wire y
);
    assign y = a & b;
endmodule
  `;
  const res = validateVerilogSyntax(validCode);
  assert.strictEqual(res.isValid, true);
});

test('Verilog code with missing module port semicolon is strictly rejected', () => {
  const codeWithoutPortSemi = `
module and_gate (
    input  wire a,
    input  wire b,
    output wire y
)
    assign y = a & b;
endmodule
  `;
  const res = validateVerilogSyntax(codeWithoutPortSemi);
  assert.strictEqual(res.isValid, false);
  assert.match(res.error, /missing ';'/);
});

// ----------------------------------------------------------------------------
// TEST SUITE 9: Undriven Output Detection & Non-False-Positive Evaluation
// ----------------------------------------------------------------------------
console.log('\n--- 9. Undriven Output Detection & Strict Test Scoring ---');

function extractModuleBodyTest(code) {
  const clean = code.replace(/\/\*[\s\S]*?\*\/|\/\/.*/g, '');
  const modIdx = clean.indexOf('module');
  if (modIdx === -1) return '';
  const afterModule = clean.slice(modIdx + 6);
  let depth = 0;
  let semiIdx = -1;
  for (let i = 0; i < afterModule.length; i++) {
    const c = afterModule[i];
    if (c === '(') depth++;
    else if (c === ')') depth = Math.max(0, depth - 1);
    else if (c === ';' && depth === 0) {
      semiIdx = i;
      break;
    }
  }
  if (semiIdx === -1) return '';
  const bodyWithEnd = afterModule.slice(semiIdx + 1);
  const endModIdx = bodyWithEnd.lastIndexOf('endmodule');
  if (endModIdx === -1) return bodyWithEnd.trim();
  return bodyWithEnd.slice(0, endModIdx).trim();
}

function hasActiveDriversTest(body) {
  if (!body || !body.trim()) return false;
  const hasAssign = /\bassign\s+/.test(body);
  const hasAlways = /\b(always|always_comb|always_ff|always_latch|initial)\b/.test(body);
  const hasPrimitives = /\b(and|nand|or|nor|xor|xnor|not|buf)\s*(\(|[A-Za-z_][A-Za-z0-9_]*\s*\()/.test(body);
  return hasAssign || hasAlways || hasPrimitives;
}

test('Starter code with empty body is detected as undriven across all challenges', () => {
  const starterCode = `
// Design a 2-input AND gate
module and_gate (
    input  wire a,
    input  wire b,
    output wire y
);

    // Enter your combinational logic here

endmodule
  `;
  const body = extractModuleBodyTest(starterCode);
  const driven = hasActiveDriversTest(body);
  assert.strictEqual(driven, false, 'Expected starter code to have zero active drivers');
});

test('Arbitrary future challenge starter code has zero active drivers', () => {
  const futureStarter = `
module custom_alu_8bit (
    input wire [7:0] a,
    input wire [7:0] b,
    input wire [2:0] opcode,
    output wire [7:0] result
);
    // Student code goes here
endmodule
  `;
  const body = extractModuleBodyTest(futureStarter);
  const driven = hasActiveDriversTest(body);
  assert.strictEqual(driven, false, 'Expected future challenge starter to have zero active drivers');
});

test('Module with declared internal wires but no drivers is detected as undriven', () => {
  const codeWithWireOnly = `
module and_gate (
    input  wire a,
    input  wire b,
    output wire y
);
    wire temp_signal;
endmodule
  `;
  const body = extractModuleBodyTest(codeWithWireOnly);
  const driven = hasActiveDriversTest(body);
  assert.strictEqual(driven, false, 'Wire declaration without assignment must not count as active driver');
});

test('Module with valid continuous assignment is recognized as driven', () => {
  const validCode = `
module and_gate (
    input  wire a,
    input  wire b,
    output wire y
);
    assign y = a & b;
endmodule
  `;
  const body = extractModuleBodyTest(validCode);
  const driven = hasActiveDriversTest(body);
  assert.strictEqual(driven, true, 'Valid assign statement must be recognized as active driver');
});

// ----------------------------------------------------------------------------
// FINAL SUMMARY
// ----------------------------------------------------------------------------
console.log('\n====================================================');
console.log(`RESULTS: ${passedTests} / ${totalTests} tests passed (${Math.round(passedTests / totalTests * 100)}%)`);
console.log('====================================================');

if (passedTests !== totalTests) {
  process.exit(1);
}
