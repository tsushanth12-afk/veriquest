// ============================================================================
// VeriQuest — Status Contract Consistency Invariants Test Suite
//
// Pure static file-reading test (zero network, zero services, zero file writes).
// Validates end-to-end alignment across:
// 1. Frontend TypeScript definitions (src/types/submission.ts)
// 2. Backend Pydantic schema enum (backend/app/submissions/schemas.py)
// 3. Database CHECK constraints (supabase/migrations/003_status_contract.sql)
// 4. API Normalizer & error-handling branches (src/api/submissionApi.ts)
// 5. Exhaustive static scan for prohibited 'FAILED' / 'failed' status literals
// ============================================================================

import assert from 'node:assert';
import fs from 'node:fs';
import path from 'node:path';

console.log('========================================================================');
console.log('VERIQUEST — STATUS CONTRACT CONSISTENCY & INVARIANT SUITE');
console.log('========================================================================\n');

let passedTests = 0;
let totalTests = 0;

function runTest(id, name, fn) {
  totalTests++;
  try {
    fn();
    console.log(`  [PASS] ${id}: ${name}`);
    passedTests++;
  } catch (err) {
    console.error(`  [FAIL] ${id}: ${name} ->`, err.message);
  }
}

// ----------------------------------------------------------------------------
// 1. Read source files
// ----------------------------------------------------------------------------
const ROOT = path.resolve('.');
const tsTypesPath = path.join(ROOT, 'src/types/submission.ts');
const pySchemaPath = path.join(ROOT, 'backend/app/submissions/schemas.py');
const migrationPath = path.join(ROOT, 'supabase/migrations/003_status_contract.sql');
const submissionApiPath = path.join(ROOT, 'src/api/submissionApi.ts');

const tsTypesContent = fs.readFileSync(tsTypesPath, 'utf8');
const pySchemaContent = fs.readFileSync(pySchemaPath, 'utf8');
const migrationContent = fs.readFileSync(migrationPath, 'utf8');
const submissionApiContent = fs.readFileSync(submissionApiPath, 'utf8');

// ----------------------------------------------------------------------------
// 2. Parse status sets
// ----------------------------------------------------------------------------

// Extract SubmissionStatus union members from src/types/submission.ts
const tsStatusMatch = tsTypesContent.match(/export type SubmissionStatus\s*=\s*([^;]+);/);
assert(tsStatusMatch, 'Failed to locate SubmissionStatus type in src/types/submission.ts');
const tsStatuses = new Set(
  [...tsStatusMatch[1].matchAll(/'([A-Z_]+)'/g)].map((m) => m[1])
);

// Extract enum values from backend/app/submissions/schemas.py
const enumBlockMatch = pySchemaContent.match(/class SubmissionStatus\s*\(str,\s*Enum\):([\s\S]*?)TERMINAL_STATUSES/);
assert(enumBlockMatch, 'Failed to locate SubmissionStatus enum in backend/app/submissions/schemas.py');
const backendEnumValues = new Set(
  [...enumBlockMatch[1].matchAll(/=\s*["']([a-z_]+)["']/g)].map((m) => m[1])
);

// Extract allowed values from supabase/migrations/003_status_contract.sql
const dbConstraintMatch = migrationContent.match(/CHECK\s*\(\s*status\s+IN\s*\(([\s\S]*?)\)\s*\)/i);
assert(dbConstraintMatch, 'Failed to locate valid_submission_status CHECK constraint in migration 003');
const dbAllowedValues = new Set(
  [...dbConstraintMatch[1].matchAll(/'([a-z_]+)'/g)].map((m) => m[1])
);

// Parse normalizeBackendStatus function body from src/api/submissionApi.ts
const normalizerMatch = submissionApiContent.match(/export function normalizeBackendStatus[\s\S]*?switch\s*\([^{]+\)\s*\{([\s\S]*?)\n\}/);
assert(normalizerMatch, 'Failed to locate normalizeBackendStatus function in src/api/submissionApi.ts');
const normalizerBody = normalizerMatch[1];

// ----------------------------------------------------------------------------
// 3. Assertions
// ----------------------------------------------------------------------------

runTest('CONTRACT-01', 'Every backend enum value is allowed by latest DB CHECK constraint (migration 003)', () => {
  for (const enumVal of backendEnumValues) {
    assert(
      dbAllowedValues.has(enumVal),
      `Backend enum value '${enumVal}' is NOT allowed by DB CHECK constraint in migration 003`
    );
  }
  assert.strictEqual(backendEnumValues.size, dbAllowedValues.size);
});

runTest('CONTRACT-02', 'EVALUATOR_NOT_CONFIGURED exists consistently across TS, Python Enum, and DB', () => {
  assert(tsStatuses.has('EVALUATOR_NOT_CONFIGURED'), 'EVALUATOR_NOT_CONFIGURED missing from src/types/submission.ts');
  assert(backendEnumValues.has('evaluator_not_configured'), 'evaluator_not_configured missing from SubmissionStatus enum in backend');
  assert(dbAllowedValues.has('evaluator_not_configured'), 'evaluator_not_configured missing from DB migration 003 CHECK constraint');
});

runTest('CONTRACT-03', 'Retired status FAILED / failed is absent from TS SubmissionStatus, Python Enum, and DB CHECK constraint', () => {
  assert(!tsStatuses.has('FAILED'), "Prohibited 'FAILED' found in TS SubmissionStatus");
  assert(!backendEnumValues.has('failed'), "Prohibited 'failed' found in backend SubmissionStatus enum");
  assert(!dbAllowedValues.has('failed'), "Prohibited 'failed' found in DB CHECK constraint");
});

runTest('CONTRACT-04', 'normalizeBackendStatus correctly maps evaluator_not_configured to EVALUATOR_NOT_CONFIGURED', () => {
  assert(
    normalizerBody.includes("case 'evaluator_not_configured':"),
    "normalizeBackendStatus must contain case 'evaluator_not_configured'"
  );
  assert(
    /case\s+'evaluator_not_configured':\s*return\s+'EVALUATOR_NOT_CONFIGURED';/.test(normalizerBody),
    "evaluator_not_configured must return 'EVALUATOR_NOT_CONFIGURED'"
  );
});

runTest('CONTRACT-05', 'normalizeBackendStatus removes legacy failed alias and enforces fail-closed default -> SYSTEM_ERROR', () => {
  assert(
    !normalizerBody.includes("case 'failed':"),
    "Legacy alias `case 'failed':` must not exist in normalizeBackendStatus"
  );
  const defaultMatch = normalizerBody.match(/default:([\s\S]*)/);
  assert(defaultMatch, 'normalizeBackendStatus must have a default branch');
  assert(
    defaultMatch[1].includes("return 'SYSTEM_ERROR';"),
    "default branch must return 'SYSTEM_ERROR' per fail-closed security rule"
  );
  assert(
    !defaultMatch[1].includes("return 'ACCEPTED';"),
    "default branch must never return 'ACCEPTED'"
  );
  assert(
    !defaultMatch[1].includes("return 'WRONG_ANSWER';"),
    "default branch must never return 'WRONG_ANSWER'"
  );
});

runTest('CONTRACT-06', 'Exhaustive scan: No status-position FAILED / failed in src/ (outside explicit allow-list)', () => {
  // Allow-list for legitimate non-status text and documented audit-only findings:
  // 1. Verilog $display counter summary lines in testbenchCatalog.ts ($display("FAILED: %0d", failed))
  // 2. Dev testbench fixture expectedStatus in frozen src/evaluator/testbenchCatalog.ts (frozen per Section 0)
  // 3. Regex parsing of Verilog simulator counter line in evaluator.ts (output.match(/FAILED:\s*(\d+)/))
  // 4. UI card sub-heading label in SubmissionPanel.tsx ("FAILED TESTCASE #...")
  // 5. Frozen mockData.ts (line 627) preserved per explicit user audit instruction
  const ALLOW_LIST = [
    { file: 'src/evaluator/testbenchCatalog.ts', pattern: /\$display\("FAILED:\s*%0d"/ },
    { file: 'src/evaluator/testbenchCatalog.ts', pattern: /expectedStatus:\s*'FAILED'/ },
    { file: 'src/evaluator/evaluator.ts', pattern: /output\.match\(\/FAILED:\\s\*\(\\d\+\)\/\)/ },
    { file: 'src/components/workspace/SubmissionPanel.tsx', pattern: /FAILED TESTCASE #/ },
    { file: 'src/api/mockData.ts', pattern: /status:\s*'FAILED'/ },
  ];

  function scanDir(dir) {
    const entries = fs.readdirSync(dir, { withFileTypes: true });
    for (const entry of entries) {
      const fullPath = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        scanDir(fullPath);
      } else if (entry.isFile() && (entry.name.endsWith('.ts') || entry.name.endsWith('.tsx') || entry.name.endsWith('.js'))) {
        const content = fs.readFileSync(fullPath, 'utf8');
        const relPath = path.relative(ROOT, fullPath).replace(/\\/g, '/');

        const lines = content.split('\n');
        for (let i = 0; i < lines.length; i++) {
          const line = lines[i];
          if (/['"]FAILED['"]|['"]failed['"]/.test(line)) {
            const isAllowed = ALLOW_LIST.some((rule) => {
              return relPath === rule.file && rule.pattern.test(line);
            });
            assert(
              isAllowed,
              `Disallowed status literal 'FAILED' / 'failed' found in ${relPath}:${i + 1}: ${line.trim()}`
            );
          }
        }
      }
    }
  }

  scanDir(path.join(ROOT, 'src'));
});

// ----------------------------------------------------------------------------
// 4. Summary
// ----------------------------------------------------------------------------
console.log('\n========================================================================');
console.log(`TEST RESULTS: ${passedTests} / ${totalTests} tests passed (${Math.round(passedTests / totalTests * 100)}%)`);
console.log('========================================================================');

if (passedTests !== totalTests) {
  process.exit(1);
}
