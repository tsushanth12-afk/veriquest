import { evaluate } from '../src/evaluator/evaluator.ts';
import fs from 'node:fs';
import assert from 'node:assert/strict';

const challenges = [
  { id: 'and-gate-demo', module: 'and_gate', ports: 'input wire a, input wire b, output wire y' },
  { id: 'mux-2to1', module: 'mux_2to1', ports: 'input wire a, input wire b, input wire sel, output wire y' },
  { id: '4-bit-counter', module: 'sync_counter_4bit', ports: 'input wire clk, input wire reset_n, input wire enable, output reg [3:0] count' },
  { id: 'xor-gate', module: 'xor_gate', ports: 'input wire a, input wire b, output wire y' },
];

async function runTests() {
  const results = [];

  for (const ch of challenges) {
    const cases = [
      {
        category: 'A: Syntax/Token Corruption (Stray Brace)',
        code: `module ${ch.module} (\n    ${ch.ports}\n);\n    assign y = a } b;\nendmodule\n`,
        expected: 'COMPILATION_ERROR',
      },
      {
        category: 'B: Undeclared/Invalid Reference (Undefined Module/Function)',
        code: `module ${ch.module} (\n    ${ch.ports}\n);\n    undefined_submodule_xyz inst (.in1(a), .out1(y));\nendmodule\n`,
        expected: 'COMPILATION_ERROR',
      },
      {
        category: 'C: Missing Semicolon / Unterminated Statement',
        code: `module ${ch.module} (\n    ${ch.ports}\n);\n    wire temp = 1'b0\n    assign y = temp;\nendmodule\n`,
        expected: 'COMPILATION_ERROR',
      },
      {
        category: 'D: Pure Random Garbage / Non-Verilog',
        code: `TOTAL_GARBAGE_RANDOM_TEXT_NOT_VERILOG { [ ( 1234567890 !@#$%^&* ) ] }`,
        expected: 'COMPILATION_ERROR',
      },
      {
        category: 'E: Empty / Whitespace-Only Submission',
        code: `   \n\t   \r\n   `,
        expected: 'COMPILATION_ERROR',
      },
    ];

    for (const c of cases) {
      const res = await evaluate(ch.id, c.code);
      const isExpected = res.status === c.expected;
      const notAccepted = res.status !== 'ACCEPTED';
      const notSystemError = (c.category.startsWith('A') || c.category.startsWith('B') || c.category.startsWith('C'))
        ? res.status !== 'SYSTEM_ERROR'
        : true;
      const passed = isExpected && notAccepted && notSystemError;

      results.push({
        challenge: ch.id,
        inputType: c.category,
        expectedStatus: c.expected,
        actualStatus: res.status,
        compilerEvidence: res.compilerOutput,
        passed,
      });
    }
  }

  if (process.argv.includes('--write-report')) {
    fs.mkdirSync('./scratch', { recursive: true });
    fs.writeFileSync('./scratch/fix1_results.json', JSON.stringify(results, null, 2));
  }
  const failures = results.filter(result => !result.passed);
  assert.equal(failures.length, 0, JSON.stringify(failures, null, 2));
  console.log(`PASS: ${results.length} production evaluator error-classification cases.`);
}

runTests().catch(err => {
  console.error('Fatal error:', err);
  process.exit(1);
});
