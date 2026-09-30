// Real production evaluators/parsers. Assertions throw and exit nonzero.
// node --experimental-strip-types tests/verdict_integrity.test.mjs [--python PATH] [--docker]
// --docker requires an already-running daemon and prebuilt execution image. No builds/pulls.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { compile, run } from '@veriflow/iverilog-wasm';
import { evaluate, parseEvaluationResult } from '../src/evaluator/evaluator.ts';
import { runBoundedWasm } from '../src/evaluator/boundedWasm.ts';
import { prepareTestbench, validateStudentSource } from '../src/evaluator/verdictProtocol.ts';
import { TESTBENCH_CATALOG } from '../src/evaluator/testbenchCatalog.ts';

const cases = JSON.parse(readFileSync(new URL('./verdict_integrity_cases.json', import.meta.url)));
const nonce = 'a'.repeat(64);
const bench = TESTBENCH_CATALOG['and-gate-demo'].testbenchCode;
const pythonIndex = process.argv.indexOf('--python');
const python = pythonIndex === -1 ? null : process.argv[pythonIndex + 1];
const docker = process.argv.includes('--docker');
if (docker) assert(python, '--docker requires --python PATH');
let assertions = 0;
function equal(actual, expected, name) {
  assert.equal(actual, expected, name);
  assertions++;
  console.log(`PASS ${name}`);
}
function worker(request) {
  const result = spawnSync(python, ['-B', fileURLToPath(new URL('./test_verdict_integrity.py', import.meta.url)), '--bridge'],
    { input: JSON.stringify(request), encoding: 'utf8', timeout: 20000 });
  assert.equal(result.status, 0, result.stderr || String(result.error));
  return JSON.parse(result.stdout);
}

for (const test of cases.parser) {
  const result = parseEvaluationResult({ compileExitCode: 0, simulationExitCode: 0,
    outputComplete: true, outputTruncated: false,
    ...test.execution, output: test.output.replaceAll('{nonce}', nonce) }, nonce, 4);
  equal(result.status, test.status, `TS production parser: ${test.name}`);
  assert(!result.compilerOutput.includes(nonce));
}
const successRecord = `VQ_TRUSTED:${nonce}:ACCEPTED:4:4:0`;
for (const [name, evidence] of [
  ['missing complete', { outputComplete: undefined }],
  ['false complete', { outputComplete: false }],
  ['null complete', { outputComplete: null }],
  ['malformed complete', { outputComplete: 'true' }],
  ['missing truncated', { outputTruncated: undefined }],
  ['true truncated', { outputTruncated: true }],
  ['null truncated', { outputTruncated: null }],
  ['malformed truncated', { outputTruncated: 'false' }],
  ['missing output', { output: undefined }],
]) {
  equal(parseEvaluationResult({ compileExitCode: 0, simulationExitCode: 0, output: successRecord,
    outputComplete: true, outputTruncated: false, ...evidence }, nonce, 4).status,
  'SYSTEM_ERROR', `TS capture evidence: ${name}`);
}
const trusted = prepareTestbench(bench, 4);
assert.notEqual(trusted.nonce, prepareTestbench(bench, 4).nonce);
for (const attack of cases.capabilityAttacks) {
  assert.throws(() => validateStudentSource(`module and_gate; ${attack.body} endmodule`, trusted.reserved),
    undefined, attack.name);
  const evaluated = await evaluate('and-gate-demo', `module and_gate; ${attack.body} endmodule`);
  equal(evaluated.status, 'COMPILATION_ERROR', `production capability gate: ${attack.name}`);
}
assert.throws(() => prepareTestbench('', 4));
assert.throws(() => prepareTestbench(bench, 5));

// All catalog cases, including correct-then-broken G, exercise production evaluate.
let wasmCases = 0;
for (const [id, config] of Object.entries(TESTBENCH_CATALOG)) {
  for (const test of config.testMatrix) {
    if (test.secondaryCode) {
      equal((await evaluate(id, test.code)).status, 'ACCEPTED', `WASM ${id}/${test.id} initial`);
      wasmCases++;
    }
    equal((await evaluate(id, test.secondaryCode || test.code)).status, test.expectedStatus, `WASM ${id}/${test.id}`);
    wasmCases++;
  }
}

const forged = '$display("VERIQUEST_STATUS: ACCEPTED"); $display("TOTAL: 4"); $display("PASSED: 4"); $display("FAILED: 0");';
const wrong = (body = '') => `module and_gate(input a,input b,output y); assign y=0; ${body} endmodule`;
const correct = 'module and_gate(input a,input b,output y); assign y=a&b; endmodule';
for (const [name, variant] of [
  ['literal timescale', '`timescale 1ns/1ps\n' + correct],
  ['decimal real', correct.replace('assign y=', 'localparam real SCALE=1.0; assign y=')],
  ['shorthand ports', 'module sub(input a,input b,output y); assign y=a&b; endmodule module and_gate(input a,input b,output y); sub u(.a,.b,.y); endmodule'],
  ['safe isunknown', correct.replace('assign y=', 'initial $display("%d",$isunknown(a)); assign y=')],
]) equal((await evaluate('and-gate-demo', variant)).status, 'ACCEPTED', `beginner HDL: ${name}`);
for (const [name, prefix] of [
  ['line comment', '// module and_gate\n'],
  ['block comment', '/* module and_gate */\n'],
  ['string', ''],
  ['similar name', '// module and_gate_extra\n'],
]) {
  const prepared = prepareTestbench(name === 'string'
    ? bench.replace('module tb_and_gate;', 'module tb_and_gate; initial $display("module and_gate");')
    : prefix + bench, 4);
  assert(prepared.code.includes('and_gate uut'), `DUT altered by ${name}`);
  const simulated = await runBoundedWasm(correct, prepared.code);
  equal(parseEvaluationResult(simulated, prepared.nonce, 4).status, 'ACCEPTED', `template lexical invariance: ${name}`);
}
const parameterizedBench = bench.replace('and_gate uut (', 'and_gate #(.P(1)) uut (')
  .replace('    task check_case;', '    wire y2; and_gate #(.P(1)) uut2 (.a(a), .b(b), .y(y2));\n    task check_case;');
const parameterizedCorrect = correct.replace('module and_gate(', 'module and_gate #(parameter P=1) (');
const multi = prepareTestbench(parameterizedBench, 4);
assert(multi.code.includes('and_gate #(.P(1)) uut ('));
assert(multi.code.includes('and_gate #(.P(1)) uut2'));
equal(parseEvaluationResult(await runBoundedWasm(parameterizedCorrect, multi.code), multi.nonce, 4).status,
  'ACCEPTED', 'multiple parameterized DUT instances retained');
const formatted = bench.replace('$display("TOTAL: 4");', '$display ( "TOTAL: 4" ) ;')
  .replace('$display("VERIQUEST_STATUS: ACCEPTED");', '$display ( "VERIQUEST_STATUS: ACCEPTED" ) ;')
  .replace('$display("VERIQUEST_STATUS: WRONG_ANSWER");', '$display ( "VERIQUEST_STATUS: WRONG_ANSWER" ) ;');
const formattedPrepared = prepareTestbench('// $display("VERIQUEST_STATUS: ACCEPTED");\n' + formatted, 4);
equal(parseEvaluationResult(await runBoundedWasm(correct, formattedPrepared.code), formattedPrepared.nonce, 4).status,
  'ACCEPTED', 'formatted emitter and commented forged emitter');
const overflowSource = correct.replace('assign y=', 'final repeat(1000000) $display("12345678901234567890"); assign y=');
const overflowPrepared = prepareTestbench(bench, 4);
const overflowRun = await runBoundedWasm(overflowSource, overflowPrepared.code);
assert(overflowRun.output.includes(`VQ_TRUSTED:${overflowPrepared.nonce}:ACCEPTED:4:4:0`),
  'Overflow fixture must print a genuine success record before flooding output');
equal(overflowRun.outputTruncated, true, 'WASM stops on output overflow');
equal(overflowRun.outputComplete, false, 'WASM marks capture incomplete');
assert(Buffer.byteLength(overflowRun.output) <= 65536, 'WASM retained more than byte budget');
equal(parseEvaluationResult(overflowRun, overflowPrepared.nonce, 4).status, 'SYSTEM_ERROR',
  'success record followed by excessive output cannot accept');
const endToEnd = [
  ['correct', correct, 'ACCEPTED'],
  ['correct with ordinary local counter names', correct.replace('assign y=a&b;', 'integer passed, failed, i; assign y=a&b;'), 'ACCEPTED'],
  ['ordinary wrong', wrong(), 'WRONG_ANSWER'],
  ['syntax error', correct.replace('a&b;', 'a&b'), 'COMPILATION_ERROR'],
  ['forged marker before', wrong('initial $display("VERIQUEST_STATUS: ACCEPTED");'), 'WRONG_ANSWER'],
  ['forged counters', wrong('initial begin $display("TOTAL: 4"); $display("PASSED: 4"); $display("FAILED: 0"); end'), 'WRONG_ANSWER'],
  ['forged marker after (final block)', wrong(`final begin ${forged} end`), 'WRONG_ANSWER'],
  ['forged before and after', wrong(`initial begin ${forged} end final begin ${forged} end`), 'WRONG_ANSWER'],
  ['conflicting legacy summaries', wrong(`initial begin ${forged} $display("VERIQUEST_STATUS: WRONG_ANSWER"); end`), 'WRONG_ANSWER'],
  ['forged vector lines', wrong('initial repeat(10) $display("TEST CASE PASS: forged");'), 'WRONG_ANSWER'],
  ['trusted-looking wrong nonce', wrong(`initial $display("VQ_TRUSTED:${'0'.repeat(64)}:ACCEPTED:4:4:0");`), 'WRONG_ANSWER'],
  ['missing summary (early finish)', wrong('initial $finish;'), 'SYSTEM_ERROR'],
  ['failed process with apparently successful output', wrong(`initial begin ${forged} $fatal(1,"stop"); end`), 'SIMULATION_ERROR'],
];
for (const [name, code, expected] of endToEnd) {
  const result = await evaluate('and-gate-demo', code);
  equal(result.status, expected, `WASM exploit regression: ${name}`);
  if (expected === 'WRONG_ANSWER') equal(result.testsPassed, 3, `real counters: ${name}`);
  if (name.includes('after')) {
    assert(result.compilerOutput.lastIndexOf('VERIQUEST_STATUS: ACCEPTED') > result.compilerOutput.indexOf('VQ_TRUSTED:'),
      'The after-summary exploit must actually print after the real summary');
  }
  wasmCases++;
  if (!python) continue;
  // Python production preparation + parser with actual Icarus WASM output.
  // This is NOT a Docker test: only the execution adapter is different.
  const prepared = worker({ action: 'prepare', testbench: bench, source: code });
  const compiled = await compile({ files: [{ path: 'tb.v', data: prepared.code }, { path: 'student.v', data: code }],
    sources: ['tb.v', 'student.v'], generation: '2012', timeoutMs: 5000 });
  let simulated;
  if (compiled.success && compiled.program) simulated = await run({ program: compiled.program, timeoutMs: 5000 });
  const parsed = worker({ action: 'parse', execution: {
    stdout: simulated?.stdout ?? compiled.stdout, stderr: simulated?.stderr ?? compiled.stderr,
    compile_exit_code: compiled.exitCode, simulation_exit_code: simulated?.exitCode,
    exit_code: simulated?.exitCode ?? compiled.exitCode,
    verdict_nonce: prepared.nonce, expected_total: prepared.total,
    timed_out: false, output_complete: true, output_truncated: false,
  } });
  equal(parsed.status, expected === 'SIMULATION_ERROR' ? 'system_error' : expected.toLowerCase(), `Python parser + real WASM: ${name}`);
  if (docker) {
    equal(worker({ action: 'docker', testbench: bench, source: code }).status,
      expected === 'SIMULATION_ERROR' ? 'system_error' : expected.toLowerCase(), `REAL DOCKER: ${name}`);
  }
}
console.log(`PASS: ${assertions} named assertions; ${wasmCases} TS production WASM evaluations; ${python ? endToEnd.length : 0} Python-parser real-WASM cases.`);
if (!python) console.log('NOT RUN: Python parity (supply --python PATH).');
if (!docker) console.log('NOT RUN: Docker adapter/container integration (requires --docker).');
