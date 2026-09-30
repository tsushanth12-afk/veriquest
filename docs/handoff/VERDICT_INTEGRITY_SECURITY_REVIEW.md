# Verdict-integrity security and regression review

Review date: 2026-09-29 (Asia/Calcutta)  
Repository: C:\Users\tsush\Desktop\veriquest  
Comparison base and current HEAD: 4a49d625fdc43782ba2387fb9bcb9168dd4e0d60  
Branch: main  
Verdict: **NEEDS CHANGES**

## 1. Executive conclusion and evidence boundaries

The original stdout-marker acceptance attack is blocked in the exercised production paths. No student-controlled token disclosure or forged ACCEPTED bypass was reproduced. The implementation is substantially safer than the base commit, but it is not ready for an unqualified security/regression sign-off:

- A harmless trusted-testbench comment changes executable identifier rewriting and can break a correct submission.
- Valid, otherwise-correct HDL forms are newly rejected; some are accidental consequences of the scanner rather than necessary capabilities.
- The worker parser accepts missing output-completeness evidence.
- Real container execution remains unverified. Inherited output-capture and deployment issues remain important; they are not new verdict-forgery findings.

Only this review document was created. Implementation/test files were not modified, staged, committed, or pushed. No dependencies, services, migrations, builds, Docker containers, or deployments were started. WASM execution uses the library's in-memory filesystem. Python used -B. The filesystem-writing mocked Docker-adapter test was deliberately not rerun.

Evidence labels used below:

- **Executed:** observed in commands during this review.
- **Source:** traced in current source or the installed runtime, not necessarily exercised.
- **Recorded:** verified in earlier tool output in this conversation, not rerun here.
- **Blocked:** unavailable prerequisites or this review's no-write/no-service constraint.
- **Unresolved:** no sufficient proof; not a finding of exploitation.

All twelve pre-existing pending files were read, including both documents and all new helpers/fixtures. No repository AGENTS.md was found. The audit-context-building skill was consulted for trust tracing; its three referenced supporting documents are absent, so the review proceeded directly rather than claiming completion of that unavailable workflow.

## 2. Findings by severity

### Critical

**None confirmed.** This is not a proof that an ad hoc HDL scanner cannot be bypassed. Neither the existing attack suite nor the additional probes produced student-forged acceptance.

### High

#### H1 — Output capture remains unbounded before the apparent limit (inherited availability risk)

**Source + bounded execution; not a reproduced OOM.**

References:

- worker/execution/sandbox.py:144-157, DockerSandbox._execute_docker
- src/evaluator/evaluator.ts:76-81, evaluate
- src/evaluator/verdictProtocol.ts:83-84, redactVerdict
- node_modules/@veriflow/iverilog-wasm/dist/runtime.js, appendLine/createRuntime/executeStage

The Docker adapter fetches complete logs, decodes them, and only then slices them. MAX_OUTPUT_BYTES actually counts Python characters independently in each stream, not aggregate UTF-8 bytes. Container memory limits do not bound the host worker's allocations during log retrieval.

The WASM runtime accumulates stdout/stderr/combinedOutput arrays without an output budget. The new evaluator parses full output and only limits the returned diagnostic copy. It does not add a host-side memory/output cap. An allowed repeat/$display loop can amplify a small submission into much larger output.

An intentionally bounded 7,000-line probe (77,000 student-output bytes plus grader output) returned ACCEPTED and a 65,570-character compilerOutput (65,536-character body plus label). No truncation indicator was returned. This does **not** prove truncated evidence was used to accept: TypeScript had the full raw output and truncated the diagnostic copy afterward. It does demonstrate that its behavior differs from Python's over-limit rejection and that the returned-output limit is not a capture limit.

**Impact:** potential worker/server memory exhaustion, excessive Docker log storage, and inconsistent output-budget behavior. These weaknesses predate the patch; Docker capture is now more conservative about acceptance after truncation, not less.

**Required before production security approval:** enforce byte-based budgets while capturing output, terminate on budget exhaustion, preserve an explicit failure/completeness result, and align the two adapters. Do not run destructive OOM probes on the user's workstation. This inherited issue can be a separately scoped task rather than an unrelated packaging change in the verdict patch.

### Medium

#### M1 — Comments can alter trusted executable identifier rewriting

**New; reproduced.**

References:

- src/evaluator/verdictProtocol.ts:27-38, prepareTestbench
- worker/execution/verdict_protocol.py:24-34, prepare_testbench

Preparation creates a comment/string-stripped skeleton for checking declarations, but collects reserved names from the original, unstripped testbench. A comment containing "module and_gate" adds and_gate to the rename set. The subsequent rewrite renames the actual DUT instantiation to __vq_grader_and_gate, although the correct student module is still named and_gate.

Reproduction: prepend the following to the unchanged AND testbench in memory:

    // module and_gate

Pass it to production prepareTestbench, then compile with the normal correct AND solution. Actual WASM output:

    success: false
    stage: compile
    error: Unknown module type: __vq_grader_and_gate

The Python production preparation also generated the incorrect __vq_grader_and_gate DUT instantiation. No repository testbench was edited.

**Impact:** harmless documentation in an otherwise-supported trusted template breaks correct submissions; the student is likely blamed with a compilation error. The current four frozen catalog fixtures do not contain this trigger, so their passing matrix does not cover it.

**Required fix:** discover and rewrite declarations from consistent lexical/structural tokens, excluding comments/strings and distinguishing grader declarations from DUT module/port identifiers. Add comment/string invariance regressions in both implementations, including identifiers used by the DUT. Do not merely special-case this comment.

#### M2 — The new source filter rejects valid beginner HDL beyond capability-bearing constructs

**New; reproduced. Some restrictions are intentional, but compatibility is not established by the catalog alone.**

References:

- src/evaluator/verdictProtocol.ts:42-66, validateStudentSource
- worker/execution/verdict_protocol.py:39-62, validate_student_source
- tests/verdict_integrity.test.mjs:55-80, catalog and endToEnd fixtures
- tests/VERDICT_INTEGRITY.md:46-62, stated compatibility limits

Each following correct design compiled, simulated, and emitted the original trusted grader's ACCEPTED using real Icarus WASM, but production evaluate returned COMPILATION_ERROR:

| Valid source variation | Filter reason |
| --- | --- |
| Literal timescale 1ns/1ps directive before the correct AND module | Every backtick is forbidden |
| Unused localparam real SCALE=1.0 in that module | Decimal point mistaken for hierarchy |
| Correct submodule wired using .a, .b, .y shorthand | Dot rule only allows .name(expression) |
| Harmless $isunknown(a) in diagnostic display, with correct AND logic | System function absent from allow-list |

The Python production filter also rejected the first three. The timescale and system-call restrictions are documented, but decimal numbers and shorthand connections are not identified as restrictions in the implementation summary. Neither a numeric literal nor shorthand port binding reads a token or manipulates grader state.

**Impact:** the requirement that correct solutions remain accepted is only demonstrated for a narrow fixture set, not ordinary alternate valid source. Valid-code capability rejections are classified as student compilation failures.

**Required fix/policy decision before commit:** distinguish numbers and legal port syntax from hierarchy with a reliable lexer/parser. Add positive compatibility tests. For genuinely capability-bearing features, keep fail-closed behavior and obtain an explicit supported-HDL policy decision; do not weaken file-access or grader-namespace restrictions merely to pass compatibility tests. A literal safe timescale directive can be considered separately from arbitrary preprocessing.

#### M3 — Missing completeness evidence defaults to permission to accept

**New protocol-boundary gap; reproduced with production parser fixtures, not a student-output exploit.**

Reference: worker/execution/evaluator.py:28-36, parse_evaluation_result.

The parser only rejects execution_result.get('output_truncated') when truthy. A valid authenticated record with zero compile/simulation/container exit codes is accepted when output_truncated is absent; None/False-like values have the same negative-check issue. This is not positive proof that output collection completed.

Executed production-parser results:

    valid record + successful exits + omitted output_truncated -> accepted
    same record + output_truncated=True                     -> system_error

The real current Docker success path always supplies the flag, including log-fetch exceptions. Its fallback also lacks successful stage evidence, so this is **not** a demonstrated present student route to false acceptance. It is a gap in the advertised independently fail-closed parser contract. Most shared parser fixtures and the WASM-to-Python bridge omit this flag, so the tests encode the permissive default.

**Required fix:** require an explicit, typed completeness/overflow contract for grading, reject absent or malformed evidence, and add missing/null/wrong-type cases. Make the bridge model that production contract instead of omitting it. TypeScript should likewise document that full capture is guaranteed by its adapter and distinguish diagnostic truncation from loss of grading evidence.

### Low

#### L1 — Token destruction/cleanup is best-effort, not guaranteed

**Source; cleanup fault injection and real Docker cleanup are unexecuted. Mostly inherited cleanup behavior, now carrying tokens.**

References: worker/execution/sandbox.py:184-197; node_modules/@veriflow/iverilog-wasm/dist/client.js, requestWorker/settle.

Container removal and workspace deletion exceptions are silently swallowed, even after a successful result has been constructed. Leftover testbench.v, compiled VVP, and Docker logs can contain the token and hidden testbench material. Worker termination failure in the WASM dependency is also ignored when settling an otherwise-successful result. Strings are not explicitly zeroized in either host runtime.

Freshness prevents ordinary reuse of a leftover old token against a new run; no replay bypass was reproduced. Host/admin access to residual data is a different issue from student HDL access.

**Follow-up:** observable cleanup failures, retry/reaper policy, verified ownership/permissions, and truthful retention documentation. Do not claim guaranteed destruction or erase-on-return.

#### L2 — Parser exceptions and timeout classification are not fully normalized at the parser boundary

**Source + production-parser fixture execution.**

Reference: worker/execution/evaluator.py:6-9, 22-34.

stdout=None raises TypeError rather than returning a neutral parser result. The real adapter normally supplies strings; the outer submission task catches exceptions and attempts to save system_error (worker/tasks/hdl_task.py:192 onward), while admin validation catches and reports failure. Thus no acceptance was reproduced. If the database update itself fails, terminal state persistence is not guaranteed.

A simulation exit of 124 without timed_out=True becomes system_error, whereas a wait exception with timed_out=True becomes timeout. The fixed shell uses timeout 5, while container.wait uses configurable timeout_s. Any wait exception is called a timeout even if caused by another transport error. These differences are largely inherited, but the new exit evidence makes normalization testable.

**Follow-up:** typed adapter result validation, explicit timeout/signal/transport-error distinctions, and exception tests. Preserve neutral failures and avoid using stderr text to infer process status.

## 3. Execution-token lifecycle

| Phase | TypeScript | Python worker |
| --- | --- | --- |
| Generation | prepareTestbench:15, crypto.getRandomValues over 32 bytes, hex encoded | prepare_testbench:17, secrets.token_hex(32) |
| Timing | Each configured, nonempty evaluation prepares a new token before source validation and compilation | Each valid-template execute call prepares a new token before source validation and Docker selection |
| No execution | Unknown/empty input can return without a token; this is not token reuse | Missing/unsupported template can return without a token |
| Insertion | Replaces the two trusted terminal display statements; only one branch should run | Same two in-memory replacements |
| Retention | Local trusted object, nonce variable, generated source, compiled program, WASM virtual files/worker memory, captured output | Local trusted dict, generated testbench.v, sim.vvp, raw logs, returned execution_result |
| Parser channel | nonce and expected total passed as separate host arguments to parseEvaluationResult | verdict_nonce and expected_total returned by host adapter, passed directly to parse_evaluation_result |
| Student channel | HDL source is a separate solution.v string and has no token parameter | HDL source is a separate submission.v; no token argument is supplied to it |
| Return to caller | Only EvaluatorResult; full-token occurrences redacted from diagnostics and caught errors | Parser returns normalized fields and redacted compiler_output, not raw execution_result metadata |
| Lifetime end | Local values become GC candidates; run worker termination is attempted; no explicit zeroization | remove(force=True) and rmtree attempted in finally; local objects eventually released; cleanup failures ignored |

**Freshness:** cryptographically secure generation is source-verified. Tests execute two preparations and assert different tokens; this sanity check is not a statistical proof of randomness. There is no reuse cache or persisted expected-token lookup. Retries call preparation again.

**Independent channel:** yes, relative to stdout. The expected value is never extracted from student output. This is a bearer-capability design, not a MAC/signature: security depends on preventing the student program from reading or invoking the trusted emitter. Shared-process HDL capability restrictions and reserved grader names are therefore part of the trusted computing base.

**Exposure inventory:**

- Generated trusted source and compiled bytecode contain the full token. They are not returned as student source. The WASM run receives only the program, not original source files; the program still contains the token.
- Native execution mounts the generated testbench, script, bytecode, and exit files in the same writable workspace. OS permissions do not separate them from HDL inside that process; the source capability gate is essential.
- Command arguments are fixed paths; the token is not embedded in shell commands or environment variables.
- Raw simulator stdout and Docker logging contain the full token by design. Host/admin log access is not token-free.
- Compiler diagnostics can potentially reference generated code. TypeScript redacts full-token occurrences on compile failure and execution exceptions. Python redacts before sanitizing/truncating returned diagnostics.
- Normal API flows serialize only the normalized evaluator/parser result: vite.config.ts:129-132, worker/tasks/hdl_task.py:113-135, backend/app/admin/router.py:338-344. No current flow was found that serializes the raw worker execution_result to students.
- Returned console output substitutes [grader-token] for the full token. Tests assert full-token absence in parser diagnostics. Partial-token fragments cut during capture are not guaranteed to be redacted; those jobs should fail on capture truncation and the token is single-use.
- Custom trusted templates could expose internal data through diagnostics; trusted authors/compiler/runtime remain trusted. This review does not prove arbitrary simulator memory safety.

## 4. Trusted-result protocol and process evidence

### Protocol

Both implementations require exactly one **line containing the expected full token**. They then validate the entire line against:

    VQ_TRUSTED:<expected-token>:<ACCEPTED|WRONG_ANSWER>:<total>:<passed>:<failed>

The three numbers are canonical nonnegative decimal representations with at most seven digits. The trusted expected total must be an integer in 1..1,000,000. Total must match it, passed+failed must equal total, and ACCEPTED is equivalent to failed==0.

Thus all four grading fields are in the token-bearing record. Timing and diagnostics are not authenticated grading fields; Python now returns zero timing fields and TypeScript measures host elapsed time while returning zero simulationNanoseconds. Neither trusts printed timing fields.

- Zero matching lines: neutral error.
- Two identical or conflicting matching lines: neutral error.
- Full-token line with incomplete fields, extra text, bad numeric syntax, incorrect total, or inconsistent status/counts: neutral error.
- Full token embedded elsewhere in output: also causes rejection/cardinality failure, not acceptance.
- Legacy VERIQUEST_STATUS/VQ_RESULT, totals, counters, vectors, and wrong-token records: ignored for grading.
- A bogus-token record plus a valid authenticated record does not count as two trusted records. That is intentional: attacker diagnostics are not allowed to choose a verdict.
- Marker order is not consulted; no first/last-marker selection remains.
- Additional probes with CR/U+2028/U+2029 suffixes did not produce acceptance in the TypeScript parser.

### Process trace

TypeScript evaluate:69-81 calls production compile, checks success, stage=='compile', exitCode==0, and program presence; then calls run. A failed run or unexpected run stage supplies -1 to parseEvaluationResult. Acceptance requires successful stage evidence and the valid record. Runtime callMain returns the real Emscripten exit code, executeStage derives success from exitCode==0, and requestWorker enforces timeouts/worker protocol identity. Exceptions become SYSTEM_ERROR in evaluate.

Python's fixed script records the iverilog exit into compile.exit, skips VVP after a nonzero compiler result, executes timeout 5 vvp, records simulation.exit, and exits with that result. The adapter separately reads the container wait StatusCode and stage files. The parser requires integer zero in all three exit fields. It rejects timeout/truncation flags and validates the trusted record. Those files are not parsed from stdout, but are only trustworthy under the enforced no-file-access HDL profile.

| Condition | Current behavior and evidence |
| --- | --- |
| Syntax failure | Correct classification exercised in production WASM; Python classification exercised with real WASM exit data, not native Docker |
| Ordinary wrong HDL | Genuine wrong count yields WRONG_ANSWER/wrong_answer; Icarus finish(1) is not assumed to be an OS error |
| Missing record or early finish | Neutral error, even with zero run exit; exercised |
| Duplicate/conflicting/malformed record | Neutral error in both production parsers; fixtures exercised |
| Nonzero run or signal-style 137 | No acceptance; executed parser fixtures and real WASM fatal case |
| Timeout | WASM request exception -> SYSTEM_ERROR; native wait exception -> timed_out flag; timeout executable exit 124 -> system_error unless flag set |
| Output truncation/log retrieval failure | Python adapter marks truncated/incomplete and parser rejects; adapter mechanism source-verified and previously recorded mocked test passes |
| Missing completeness flag | Accepted if other evidence succeeds: M3 |
| Missing stage file/bad exit text | None -> neutral error; source and recorded mock coverage |
| Adapter exception | Native fallback lacks successful stage evidence; cannot synthetically accept |
| Cleanup failure | May still return accepted; cleanup is not a grading prerequisite: L1 |
| Parser exception | TypeScript outer catch neutralizes; Python callers handle failures, but parser itself can raise: L2 |
| Diagnostic truncation after full capture | TypeScript can still accept; not the same as accepting incomplete grading evidence |
| Missing/whitespace template | Python execute preflight rejects before containers.run; Docker client construction/ping may already have occurred |

## 5. HDL restrictions and bypass analysis

Enforcement is **regex/text token scanning, not a structural Verilog parser**. Grader declaration rewriting is likewise textual. The real compiler remains responsible for syntax after this preflight.

| Newly prohibited construct | Rationale/limitation |
| --- | --- |
| Every backtick outside comments/strings | Blocks macros/includes and preprocessing that could evade scanning or read source; also rejects safe timescale/default_nettype/constant macros |
| Every backslash outside strings/comments | Blocks escaped identifiers that could name forbidden tasks or grader identifiers; also rejects legitimate escaped local names |
| Non-ASCII non-whitespace code tokens and malformed quote tokens | Conservative lexical profile; not a full language grammar |
| Every system call except display, write, strobe, monitor, time, realtime, signed, unsigned, clog2, bits, finish, fatal | Excludes file I/O, readmem, fwrite, system/host access, dump/VPI-style inspection, plusargs, etc.; also harmless math/introspection calls |
| bind, defparam, force, release | Prevents attaching to or overriding grading state; some legitimate design/testbench styles are lost |
| import, export, program, interface, package, config | Excludes foreign-function/scope/elaboration features; broad policy restriction, not evidence each keyword alone compromises a token |
| Identifiers starting __vq_grader_ | Protects renamed grader module/task/integer names and unqualified upward references |
| Dots except immediately after '(' or ',' followed by identifier and '(' | Tries to permit .port(expr) but exclude hierarchy; accidentally rejects decimals, .port shorthand, .*, field/member access |
| Double-colon scope resolution | Excludes scoped access; packages/interfaces are already rejected |

Comments and strings are removed/replaced for validation, so diagnostic strings containing forbidden names do not themselves grant capabilities. CR is normalized to LF for scanning to avoid hiding statements in line comments.

Executed probes beyond the supplied suite:

- Valid generate loop: accepted.
- Forbidden task/namespace text in harmless comments and diagnostic strings: accepted.
- Protected identifier inside generate block: rejected by gate.
- __vq_/**/grader_passed: gate allowed, actual compiler rejected; no concatenation bypass.
- Old upward passed/check_case names: gate allowed, actual compiler could no longer resolve them after grader renaming.
- Whitespace/split system-call forms ($ fopen and $f/**/open): gate rejected.
- Existing 17 capability fixtures cover direct file read/write, readmem, shell, hierarchy, escaped names, macros/includes, force, bind, DPI, lone CR, plusargs and dumpvars.

No bypass was demonstrated. These finite probes do not establish equivalence between the regex lexer and all Icarus lexical/elaboration behavior. Any expansion of the profile needs cross-language positive and adversarial tests. Merely making the token longer cannot compensate for a file-read or grader-call bypass.

## 6. Sandbox and packaging comparison

Every sandbox.py hunk was reviewed against the base commit.

Unchanged controls: network_disabled=True; cap_drop ALL; no-new-privileges; read_only root; fixed non-root numeric UID/GID 1000:1000; memory/CPU/PID settings; fixed command paths; detached execution; wait/kill/remove attempts; tmpfs /tmp with noexec/nosuid/size=64m; writable bind-mounted /workspace. There is no new network, privilege, mount, or resource-limit relaxation.

The removed set -e is replaced with an explicit compile exit check and final simulation exit propagation. A failed stage-file write does not immediately stop the script, but missing evidence causes parser rejection. Fresh workspaces avoid stale success files. The code does not fsync or independently attest the stage files; the same capability restrictions must prevent student writes.

Pre-existing deployment concerns are still **source findings requiring real Docker validation**:

- tempfile.mkdtemp normally creates a POSIX 0700 directory owned by the worker process. worker/Dockerfile has no USER instruction, while execution is forced to UID 1000. No chown/chmod is present. Correct access cannot be assumed.
- Compose mounts the Docker socket, not a shared temporary-workspace volume. A path created inside the worker container is not automatically available at that path to the host daemon.
- Path.write_text uses platform newline behavior; running this adapter directly on Windows requires verifying the generated shell script works in Linux.
- Output capture is not bounded at acquisition (H1). Root read_only does not make /workspace read-only, and /workspace is not tmpfs despite the header description.
- Cleanup is best-effort (L1); worker.wait transport failure is indistinguishable from timeout at this layer.

The trust rules are intentionally similar but not identical operational contracts: same token grammar/counter checks and source profile; different simulation-error statuses; Python rejects capture over its limit whereas TypeScript limits only returned diagnostics; Python preparation errors map to evaluator_not_configured while TypeScript configuration exceptions map to SYSTEM_ERROR; different exception/timeout normalization. Neither path can infer successful execution from status text.

Docker CLI absent from PATH and standard installation path; bundled Python reports Docker SDK absent; wsl --status reports WSL not installed. No real container, mount/permission, native VVP, daemon-log, or cleanup validation was performed. Mocked adapter tests cannot settle any of those questions.

## 7. Regression-test quality and all ten categories

Production imports/calls are real: evaluate, parseEvaluationResult, prepareTestbench, validateStudentSource, Python parse_evaluation_result/prepare_testbench/validate_student_source and DockerSandbox.execute. Node assertion failures propagate to a nonzero process exit; the Python unittest runner also exits nonzero. The modified error-classification script now asserts failures and only writes its report with --write-report, which was not used.

| Requested category | Actual asserted coverage |
| --- | --- |
| 1. Correct solution | All catalog A/E/I and G-initial cases; direct correct AND; Python preparation/parser with real WASM output |
| 2. Ordinary wrong | Catalog B/C/H/G-secondary and constant-zero AND; status and real 3/4 count assertions |
| 3. Syntax error | Catalog D/F and explicit syntax example; separate 20-case production classification test |
| 4. Wrong + forged ACCEPTED | Real production evaluate and Python/WASM bridge |
| 5. Wrong + forged counters | Real production evaluate/bridge; real count remains 3 |
| 6. Marker before grader | Student initial block and parser fixtures |
| 7. Marker after grader | Student final block; assertion explicitly checks returned marker ordering |
| 8. Duplicate/conflicting summaries | Same-token duplicates/conflicts tested at both production parsers with synthetic fixtures; conflicting legacy student summaries also simulated |
| 9. Missing summary | Fixture and real early finish |
| 10. Unsuccessful process + successful-looking output | Nonzero compile/run parser fixtures, actual WASM fatal with forged legacy success text; not a native Docker process test |

Important qualifications:

- Tests use a known synthetic token for parser unit cases. That is appropriate for malformed/duplicate authenticated-record handling; it does **not** prove students cannot learn a real token.
- End-to-end student payloads do not receive the fresh execution token. The Python bridge passes a real token to the trusted test harness to connect preparation and parsing, not to student source. It bypasses Docker and cannot verify native capability behavior, exit files, permissions, or capture completeness.
- The mocked Docker transport reads the generated token and writes synthetic stage files/output. It proves adapter branches, not compilation or operating-system isolation. In particular it bypasses the UID/mount problems.
- Wrong-token test uses all zeros rather than capturing and replaying an actual previous execution token. Freshness has a two-generation inequality assertion; no concurrency/retry lifecycle stress test exists.
- There is no comprehensive lexer differential/fuzz suite or positive syntax compatibility corpus; M1/M2 are absent.
- Parser fixtures mostly omit output_truncated, concealing M3.
- 124 is the number of calls to the suite's named equal helper, not 124 independent end-to-end simulations. Additional assert calls are not counted.
- 53 is 40 catalog evaluate calls plus 13 exploit/compatibility evaluate calls. Syntax/missing-module cases compile and fail without simulating; it does not mean 53 successful compiler-plus-simulator runs. Seventeen additional capability-gate evaluate calls never reach the compiler.
- The 20-case classification test's counter port names remain reset_n/enable rather than rst_n/en. Those invalid cases can fail for interface errors as well as their intended error; the separate catalog matrix provides correct counter-interface coverage.
- Removing failedVector construction means the existing UI's structured failed-vector panel is no longer populated from this evaluator. Raw vector diagnostics remain available. The old synthetic simulation duration is now zero. This is documented behavior, not evidence of measured zero simulation time.

## 8. Exact executed evidence

Commands ran from the repository root. No --docker, --write-report, build, install, or service command was used.

Python executable used below:

    C:/Users/tsush/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe

| ID | Command/evidence | Observed result |
| --- | --- | --- |
| E1 | node --experimental-strip-types tests/verdict_integrity.test.mjs --python <above executable> | Exit 0; "PASS: 124 named assertions; 53 TS production WASM evaluations; 13 Python-parser real-WASM cases." Explicit Docker NOT RUN message |
| E2 | & <python> -B tests/test_verdict_integrity.py VerdictIntegrityTests.test_shared_parser_cases VerdictIntegrityTests.test_worker_process_evidence VerdictIntegrityTests.test_capability_attacks VerdictIntegrityTests.test_fresh_token_and_template_fail_closed VerdictIntegrityTests.test_seeded_testbench_profile VerdictIntegrityTests.test_preflight_before_docker_and_fallback | Exit 0; Ran 6 tests, OK |
| E3 | node --experimental-strip-types tests/test_fix1_error_classification.mjs | Exit 0; PASS: 20 production evaluator error-classification cases |
| E4 | node node_modules/typescript/bin/tsc -p tsconfig.app.json --noEmit | Exit 0, no diagnostics |
| E5 | node node_modules/typescript/bin/tsc -p tsconfig.node.json --noEmit | Exit 0, no diagnostics |
| E6 | node tests/status_contract_consistency.test.mjs | Exit 0; 6/6 static checks |
| E7 | node tests/security_and_contracts.test.js | Exit 0; 23/23 mocked/reimplemented security checks, not production auth evidence |
| E8 | node tests/backend_multiuser_security.test.mjs | Exit 0; 23/23 mocked/static auth/security checks, not live multi-user evidence |
| E9 | node node_modules/oxlint/bin/oxlint src/evaluator/evaluator.ts src/evaluator/verdictProtocol.ts tests/verdict_integrity.test.mjs tests/test_fix1_error_classification.mjs tests/status_contract_consistency.test.mjs --deny-warnings | Exit 0, no diagnostic output |
| E10 | git diff --check <base> | No whitespace errors; only Git LF-to-CRLF warnings |
| E11 | In-memory Node production-evaluator/WASM probes described in M1/M2/H1 and section 5 | Exit 0; confirmed four correct-source rejections, harmless-comment rewrite failure, bounded output behavior, and six unsuccessful bypass attempts |
| E12 | In-memory Python production-helper/parser probes | Exit 0; confirmed comment-driven rewrite, three capability rejections, omitted-completeness acceptance, explicit-truncation/signal rejection, 124-vs-timeout classification, and malformed-stdout TypeError |
| E13 | Git state, SHA256, versions, PATH, Docker SDK lookup, wsl --status | main/base HEAD unchanged; report hash matches; Node v25.9.0, Python 3.12.14; Docker/WSL unavailable |

**Recorded-only confirmation:** the preceding implementation turn contains a seven-method Python run with exit 0, including the mocked adapter method. Its source was inspected here. That method creates temporary source/script/exit files and was not rerun under this request's only-one-document write authorization. Therefore this review independently reran six Python methods, not seven.

The independent E11/E12 probes were inline commands, not new test files. Minimal reproduction inputs:

    correct = module and_gate(input a,input b,output y); assign y=a&b; endmodule

    M1: prepareTestbench("// module and_gate\n" + catalogAND.testbenchCode, 4)
        then actual WASM compilation against correct above.

    M2: prepend a literal timescale directive;
        insert localparam real SCALE=1.0;
        use module sub with sub u(.a,.b,.y);
        or insert initial $display("%d",$isunknown(a)).
        Compare production evaluate with actual simulate against the original catalog bench.

    H1 bounded probe: insert initial repeat(7000) $display("1234567890");
        into the correct module. Observe ACCEPTED and returnedChars=65570.

    M3: parse_evaluation_result({
        "stdout": "VQ_TRUSTED:" + "a"*64 + ":ACCEPTED:4:4:0",
        "stderr": "", "verdict_nonce": "a"*64, "expected_total": 4,
        "compile_exit_code": 0, "simulation_exit_code": 0, "exit_code": 0
    })
        returns accepted; adding output_truncated=True returns system_error.

These parser-fixture tokens are synthetic constants, not leaked live execution secrets. No OOM, host-file exploit, real Docker, or live database test was attempted.

## 9. Repository state and complete changed-file inventory

**Staged:** none. All tracked modifications below are unstaged; all additions below are untracked. Branch main and HEAD still equal the requested base. The existing takeover review is absent from the base commit, so "unchanged" means byte-identical to the pre-implementation/pre-review copy, not equal to a tracked base file.

| Path | State | Diff/size | Review disposition |
| --- | --- | --- | --- |
| src/evaluator/evaluator.ts | Unstaged modified | +56 / -179 | Stage-separated WASM execution and production result parser; reviewed |
| worker/execution/evaluator.py | Unstaged modified | +44 / -188 | Removes stdout status trust; normalizes trusted execution result; reviewed |
| worker/execution/sandbox.py | Unstaged modified | +42 / -20 | Preparation, capability gate, stage files, capture flags; every hunk reviewed |
| tests/status_contract_consistency.test.mjs | Unstaged modified | +2 / -0 | Narrow reserved-counter allow-list; reviewed, not a blanket status exemption |
| tests/test_fix1_error_classification.mjs | Unstaged modified | +8 / -3 | Adds nonzero failure and opt-in report writing; reviewed |
| src/evaluator/verdictProtocol.ts | Untracked new | 85 lines | New preparation/scanner/protocol; reviewed |
| worker/execution/verdict_protocol.py | Untracked new | 80 lines | Python counterpart; reviewed |
| tests/verdict_integrity.test.mjs | Untracked new | 112 lines | Real evaluator/parser/WASM bridge tests; reviewed |
| tests/test_verdict_integrity.py | Untracked new | 153 lines | Production parser/gate and mocked adapter tests; reviewed |
| tests/verdict_integrity_cases.json | Untracked new | 280 lines | 33 parser cases and 17 capability attacks; every fixture reviewed |
| tests/VERDICT_INTEGRITY.md | Untracked new | 100 lines | Design/test claims reviewed with qualifications above |
| docs/handoff/CODEX_TAKEOVER_REVIEW.md | Pre-existing untracked | 186 lines | Reviewed historical report, preserved; not part of the implementation change |
| docs/handoff/VERDICT_INTEGRITY_SECURITY_REVIEW.md | New review artifact | This document | Only authorized write during this review |

Tracked diff summary against the specified commit: **5 files, 152 insertions, 390 deletions**. Git's default diff stat excludes untracked files. Six new implementation/test/documentation files contribute 810 lines, so the verdict milestone itself is **11 files, 962 added lines and 390 removed lines** using the tracked diff plus full new-file contents. The historical takeover report adds another 186 lines if comparing every pre-review pending file against the base. This review artifact is additional and excluded from those counts.

Takeover review SHA256 before and after verification:

    5964DA4DA8B358266B4F888FB742141E49A229B70CAA5531122DBC405DC85D21

No new generated artifacts appeared in the pending-file inventory. Do not accidentally fold the historical takeover document into the implementation commit without an explicit documentation decision. No XP, database, migration, UI source, Dockerfile, compose, lockfile, or dependency changes were found. UI diagnostic behavior changes through the evaluator return shape were identified above rather than hidden as a source-file scope claim.

Final preservation verification compared SHA256 values for all twelve pre-existing pending files with the opening inventory: **12 checked, 0 changed during this review**. The final Git status adds only this review document; the index remains empty.

## 10. Required next actions and acceptance criteria

Before committing the verdict patch:

1. Fix M1's comment/string-sensitive declaration discovery and rewriting. Both language implementations must preserve compilation/verdicts when harmless comments or strings mention DUT identifiers.
2. Resolve M2's supported-language policy and accidental lexer exclusions. Add positive correct-solution tests for decimals and both explicit/shorthand named ports; decide literal safe directives and harmless system functions explicitly. Keep token/file/grader protections intact.
3. Require explicit complete-output evidence at the Python parser boundary (M3); test missing/null/wrong-type metadata and update the real-WASM bridge to carry the same contract.
4. Add these reproductions to production-calling regressions and rerun all existing focused suites. Continue distinguishing parser fixtures, real WASM, mocks, and containers.

Before claiming production readiness:

- Address or explicitly schedule/accept H1's inherited output-capture risk.
- In a provisioned environment, run --docker parity with the prebuilt image. Confirm normal correct/wrong/syntax results, no forged acceptance, successful stage-file recording, fail-closed incomplete capture, UID/mount access, timeouts/signals, and observable cleanup.
- Do not reinterpret the current WASM/mocked results as evidence that native Docker or deployment works.

**Final verdict: NEEDS CHANGES.** Core stdout-forgery regression coverage passes, but independently reproduced new correctness issues and the completeness-contract gap require resolution. Docker-dependent security/operational conclusions remain blocked; this review neither approves deployment nor claims a new reproduced critical verdict bypass.

