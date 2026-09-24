/* ==========================================================================
   VeriQuest — Authoritative Testbench Catalog (SERVER-ONLY)
   Stores hidden testbenches, module definitions, and verification test matrices
   keyed strictly by challengeId.
   Zero branching in evaluator logic — challengeId only performs catalog lookup.

   CRITICAL SECURITY INVARIANT:
   This module contains confidential testbenches and official solutions.
   It must NEVER be imported, directly or transitively, by any client-rendered component.
   Only server-side runtimes (vite.config.ts middleware or backend services) may import this.
   ========================================================================== */

export interface TestCaseDef {
  id: string; // 'A' | 'B' | 'C' | 'D' | 'E' | 'F' | 'G' | 'H' | 'I'
  title: string;
  expectedStatus: string;
  code: string;
  secondaryCode?: string; // For Test G
}

export interface ChallengeTestbenchConfig {
  challengeId: string;
  moduleName: string;
  aliases: string[];
  totalVectors: number;
  testbenchCode: string;
  testMatrix: TestCaseDef[];
}

const AND_GATE_TESTBENCH = `\`timescale 1ns/1ps

module tb_and_gate;
    reg a;
    reg b;
    wire y;
    integer passed = 0;
    integer failed = 0;

    // Instantiate Unit Under Test
    and_gate uut (
        .a(a),
        .b(b),
        .y(y)
    );

    task check_case;
        input exp_y;
        begin
            #1;
            if (y === exp_y) begin
                $display("TEST CASE PASS: a=%b b=%b -> y=%b (expected %b)", a, b, y, exp_y);
                passed = passed + 1;
            end else begin
                $display("TEST CASE FAIL: a=%b b=%b -> y=%b (expected %b)", a, b, y, exp_y);
                failed = failed + 1;
            end
        end
    endtask

    initial begin
        a = 0; b = 0; check_case(1'b0);
        a = 0; b = 1; check_case(1'b0);
        a = 1; b = 0; check_case(1'b0);
        a = 1; b = 1; check_case(1'b1);

        $display("--- SUMMARY ---");
        $display("TOTAL: 4");
        $display("PASSED: %0d", passed);
        $display("FAILED: %0d", failed);

        if (failed == 0) begin
            $display("VERIQUEST_STATUS: ACCEPTED");
            $finish(0);
        end else begin
            $display("VERIQUEST_STATUS: WRONG_ANSWER");
            $finish(1);
        end
    end
endmodule
`;

const MUX_2TO1_TESTBENCH = `\`timescale 1ns/1ps

module tb_mux_2to1;
    reg a;
    reg b;
    reg sel;
    wire y;
    integer passed = 0;
    integer failed = 0;

    // Instantiate Unit Under Test
    mux_2to1 uut (
        .a(a),
        .b(b),
        .sel(sel),
        .y(y)
    );

    task check_case;
        input exp_y;
        begin
            #1;
            if (y === exp_y) begin
                $display("TEST CASE PASS: sel=%b a=%b b=%b -> y=%b (expected %b)", sel, a, b, y, exp_y);
                passed = passed + 1;
            end else begin
                $display("TEST CASE FAIL: sel=%b a=%b b=%b -> y=%b (expected %b)", sel, a, b, y, exp_y);
                failed = failed + 1;
            end
        end
    endtask

    initial begin
        // sel = 0: routes a
        sel = 0; a = 0; b = 0; check_case(1'b0);
        sel = 0; a = 0; b = 1; check_case(1'b0);
        sel = 0; a = 1; b = 0; check_case(1'b1);
        sel = 0; a = 1; b = 1; check_case(1'b1);

        // sel = 1: routes b
        sel = 1; a = 0; b = 0; check_case(1'b0);
        sel = 1; a = 0; b = 1; check_case(1'b1);
        sel = 1; a = 1; b = 0; check_case(1'b0);
        sel = 1; a = 1; b = 1; check_case(1'b1);

        $display("--- SUMMARY ---");
        $display("TOTAL: 8");
        $display("PASSED: %0d", passed);
        $display("FAILED: %0d", failed);

        if (failed == 0) begin
            $display("VERIQUEST_STATUS: ACCEPTED");
            $finish(0);
        end else begin
            $display("VERIQUEST_STATUS: WRONG_ANSWER");
            $finish(1);
        end
    end
endmodule
`;

const SYNC_COUNTER_4BIT_TESTBENCH = `\`timescale 1ns/1ps

module tb_sync_counter_4bit;
    reg clk;
    reg rst_n;
    reg en;
    wire [3:0] count;
    integer passed = 0;
    integer failed = 0;
    integer i;

    // Instantiate Unit Under Test
    sync_counter_4bit uut (
        .clk(clk),
        .rst_n(rst_n),
        .en(en),
        .count(count)
    );

    // Clock generator: 10ns period
    always #5 clk = ~clk;

    task check_count;
        input [3:0] exp_count;
        input [255:0] description;
        begin
            #1;
            if (count === exp_count) begin
                $display("TEST CASE PASS: %0s -> count=%b (expected %b)", description, count, exp_count);
                passed = passed + 1;
            end else begin
                $display("TEST CASE FAIL: %0s -> count=%b (expected %b)", description, count, exp_count);
                failed = failed + 1;
            end
        end
    endtask

    initial begin
        clk = 0;
        rst_n = 0;
        en = 0;

        // Vector 1: Asynchronous reset immediately drives count to 0
        #2;
        check_count(4'b0000, "async reset");

        // Vector 2: Deassert reset with en=0: count holds at 0 across clock edge
        @(negedge clk);
        rst_n = 1;
        en = 0;
        @(posedge clk);
        check_count(4'b0000, "en=0 holds count");

        // Vectors 3-17: Enable counter, count increments from 1 to 15
        @(negedge clk);
        en = 1;
        for (i = 1; i <= 15; i = i + 1) begin
            @(posedge clk);
            check_count(i[3:0], "incrementing");
        end

        // Vector 18: Rollover from 15 back to 0
        @(posedge clk);
        check_count(4'b0000, "rollover to 0");

        // Vector 19: Disable enable (en=0): count holds
        @(negedge clk);
        en = 0;
        @(posedge clk);
        check_count(4'b0000, "disabled holds count");

        // Vector 20: Enable again, clock 2 ticks, then assert async reset mid-cycle
        @(negedge clk);
        en = 1;
        @(posedge clk);
        @(posedge clk);
        #1;
        rst_n = 0;
        #1;
        check_count(4'b0000, "async reset recovery");

        $display("--- SUMMARY ---");
        $display("TOTAL: 20");
        $display("PASSED: %0d", passed);
        $display("FAILED: %0d", failed);

        if (failed == 0) begin
            $display("VERIQUEST_STATUS: ACCEPTED");
            $finish(0);
        end else begin
            $display("VERIQUEST_STATUS: WRONG_ANSWER");
            $finish(1);
        end
    end
endmodule
`;

const XOR_GATE_TESTBENCH = `\`timescale 1ns/1ps

module tb_xor_gate;
    reg a;
    reg b;
    wire y;
    integer passed = 0;
    integer failed = 0;

    // Instantiate Unit Under Test
    xor_gate uut (
        .a(a),
        .b(b),
        .y(y)
    );

    task check_case;
        input exp_y;
        begin
            #1;
            if (y === exp_y) begin
                $display("TEST CASE PASS: a=%b b=%b -> y=%b (expected %b)", a, b, y, exp_y);
                passed = passed + 1;
            end else begin
                $display("TEST CASE FAIL: a=%b b=%b -> y=%b (expected %b)", a, b, y, exp_y);
                failed = failed + 1;
            end
        end
    endtask

    initial begin
        a = 0; b = 0; check_case(1'b0);
        a = 0; b = 1; check_case(1'b1);
        a = 1; b = 0; check_case(1'b1);
        a = 1; b = 1; check_case(1'b0);

        $display("--- SUMMARY ---");
        $display("TOTAL: 4");
        $display("PASSED: %0d", passed);
        $display("FAILED: %0d", failed);

        if (failed == 0) begin
            $display("VERIQUEST_STATUS: ACCEPTED");
            $finish(0);
        end else begin
            $display("VERIQUEST_STATUS: WRONG_ANSWER");
            $finish(1);
        end
    end
endmodule
`;

export const TESTBENCH_CATALOG: Record<string, ChallengeTestbenchConfig> = {
  'and-gate-demo': {
    challengeId: 'c0000000-0000-0000-0000-000000000001',
    moduleName: 'and_gate',
    aliases: ['c0000000-0000-0000-0000-000000000001', 'and-gate-demo', 'ch-fund-and-gate', 'and-gate'],
    totalVectors: 4,
    testbenchCode: AND_GATE_TESTBENCH,
    testMatrix: [
      {
        id: 'A',
        title: 'Correct Solution',
        expectedStatus: 'ACCEPTED',
        code: `module and_gate (\n    input  wire a,\n    input  wire b,\n    output wire y\n);\n    assign y = a & b;\nendmodule\n`,
      },
      {
        id: 'B',
        title: 'Required Logic Removed (Empty Body)',
        expectedStatus: 'FAILED',
        code: `module and_gate (\n    input  wire a,\n    input  wire b,\n    output wire y\n);\nendmodule\n`,
      },
      {
        id: 'C',
        title: 'Logic Changed Incorrectly (OR gate)',
        expectedStatus: 'FAILED',
        code: `module and_gate (\n    input  wire a,\n    input  wire b,\n    output wire y\n);\n    assign y = a | b;\nendmodule\n`,
      },
      {
        id: 'D',
        title: 'Syntax Broken (Missing semicolon)',
        expectedStatus: 'COMPILATION_ERROR',
        code: `module and_gate (\n    input  wire a,\n    input  wire b,\n    output wire y\n);\n    assign y = a & b\nendmodule\n`,
      },
      {
        id: 'E',
        title: 'Same Logic, Valid Gate Primitive Style',
        expectedStatus: 'ACCEPTED',
        code: `module and_gate (\n    input  wire a,\n    input  wire b,\n    output wire y\n);\n    and g1(y, a, b);\nendmodule\n`,
      },
      {
        id: 'F',
        title: 'Cross-Challenge Solution (MUX submitted to AND)',
        expectedStatus: 'COMPILATION_ERROR',
        code: `module mux_2to1 (\n    input  wire a,\n    input  wire b,\n    input  wire sel,\n    output wire y\n);\n    assign y = sel ? b : a;\nendmodule\n`,
      },
      {
        id: 'G',
        title: 'Submit Correct then Broken (Cache Invalidation)',
        expectedStatus: 'FAILED',
        code: `module and_gate (\n    input  wire a,\n    input  wire b,\n    output wire y\n);\n    assign y = a & b;\nendmodule\n`,
        secondaryCode: `module and_gate (\n    input  wire a,\n    input  wire b,\n    output wire y\n);\n    assign y = a | b;\nendmodule\n`,
      },
      {
        id: 'H',
        title: 'Comment-Only Trick (Old Regex Bug Check)',
        expectedStatus: 'FAILED',
        code: `module and_gate (\n    input  wire a,\n    input  wire b,\n    output wire y\n);\n    /* assign y = a & b; */\n    assign y = 1'b0;\nendmodule\n`,
      },
      {
        id: 'I',
        title: 'Resubmit Already-ACCEPTED (XP Idempotency)',
        expectedStatus: 'ACCEPTED',
        code: `module and_gate (\n    input  wire a,\n    input  wire b,\n    output wire y\n);\n    assign y = a & b;\nendmodule\n`,
      },
    ],
  },
  'mux-2to1': {
    challengeId: 'ch-fund-mux-2to1',
    moduleName: 'mux_2to1',
    aliases: ['ch-fund-mux-2to1', 'mux-2to1', '2-to-1-multiplexer'],
    totalVectors: 8,
    testbenchCode: MUX_2TO1_TESTBENCH,
    testMatrix: [
      {
        id: 'A',
        title: 'Correct Solution (Ternary assign)',
        expectedStatus: 'ACCEPTED',
        code: `module mux_2to1 (\n    input  wire a,\n    input  wire b,\n    input  wire sel,\n    output wire y\n);\n    assign y = sel ? b : a;\nendmodule\n`,
      },
      {
        id: 'B',
        title: 'Required Logic Removed (Empty Body)',
        expectedStatus: 'FAILED',
        code: `module mux_2to1 (\n    input  wire a,\n    input  wire b,\n    input  wire sel,\n    output wire y\n);\nendmodule\n`,
      },
      {
        id: 'C',
        title: 'Logic Changed Incorrectly (Inverted select)',
        expectedStatus: 'FAILED',
        code: `module mux_2to1 (\n    input  wire a,\n    input  wire b,\n    input  wire sel,\n    output wire y\n);\n    assign y = sel ? a : b;\nendmodule\n`,
      },
      {
        id: 'D',
        title: 'Syntax Broken (Missing semicolon)',
        expectedStatus: 'COMPILATION_ERROR',
        code: `module mux_2to1 (\n    input  wire a,\n    input  wire b,\n    input  wire sel,\n    output wire y\n);\n    assign y = sel ? b : a\nendmodule\n`,
      },
      {
        id: 'E',
        title: 'Different Valid Style (Procedural always block)',
        expectedStatus: 'ACCEPTED',
        code: `module mux_2to1 (\n    input  wire a,\n    input  wire b,\n    input  wire sel,\n    output reg  y\n);\n    always @(*) begin\n        if (sel) y = b;\n        else y = a;\n    end\nendmodule\n`,
      },
      {
        id: 'F',
        title: 'Cross-Challenge Solution (Counter submitted to MUX)',
        expectedStatus: 'COMPILATION_ERROR',
        code: `module sync_counter_4bit (\n    input  wire clk,\n    input  wire rst_n,\n    input  wire en,\n    output reg [3:0] count\n);\n    always @(posedge clk) count <= 0;\nendmodule\n`,
      },
      {
        id: 'G',
        title: 'Submit Correct then Broken (Cache Invalidation)',
        expectedStatus: 'FAILED',
        code: `module mux_2to1 (\n    input  wire a,\n    input  wire b,\n    input  wire sel,\n    output wire y\n);\n    assign y = sel ? b : a;\nendmodule\n`,
        secondaryCode: `module mux_2to1 (\n    input  wire a,\n    input  wire b,\n    input  wire sel,\n    output wire y\n);\n    assign y = sel ? a : b;\nendmodule\n`,
      },
      {
        id: 'H',
        title: 'Comment-Only Trick (Old Regex Bug Check)',
        expectedStatus: 'FAILED',
        code: `module mux_2to1 (\n    input  wire a,\n    input  wire b,\n    input  wire sel,\n    output wire y\n);\n    /* assign y = sel ? b : a; */\n    assign y = 1'b0;\nendmodule\n`,
      },
      {
        id: 'I',
        title: 'Resubmit Already-ACCEPTED (XP Idempotency)',
        expectedStatus: 'ACCEPTED',
        code: `module mux_2to1 (\n    input  wire a,\n    input  wire b,\n    input  wire sel,\n    output wire y\n);\n    assign y = sel ? b : a;\nendmodule\n`,
      },
    ],
  },
  'sync-counter-4bit': {
    challengeId: 'ch-seq-sync-counter-4bit',
    moduleName: 'sync_counter_4bit',
    aliases: ['ch-seq-sync-counter-4bit', 'sync-counter-4bit', '4-bit-counter'],
    totalVectors: 20,
    testbenchCode: SYNC_COUNTER_4BIT_TESTBENCH,
    testMatrix: [
      {
        id: 'A',
        title: 'Correct Solution (Async reset + enable)',
        expectedStatus: 'ACCEPTED',
        code: `module sync_counter_4bit (\n    input  wire       clk,\n    input  wire       rst_n,\n    input  wire       en,\n    output reg  [3:0] count\n);\n    always @(posedge clk or negedge rst_n) begin\n        if (!rst_n) count <= 4'b0000;\n        else if (en) count <= count + 1'b1;\n    end\nendmodule\n`,
      },
      {
        id: 'B',
        title: 'Required Logic Removed (Empty Body)',
        expectedStatus: 'FAILED',
        code: `module sync_counter_4bit (\n    input  wire       clk,\n    input  wire       rst_n,\n    input  wire       en,\n    output reg  [3:0] count\n);\nendmodule\n`,
      },
      {
        id: 'C',
        title: 'Logic Changed Incorrectly (Synchronous reset only)',
        expectedStatus: 'FAILED',
        code: `module sync_counter_4bit (\n    input  wire       clk,\n    input  wire       rst_n,\n    input  wire       en,\n    output reg  [3:0] count\n);\n    always @(posedge clk) begin\n        if (!rst_n) count <= 4'b0000;\n        else count <= count + 1'b1;\n    end\nendmodule\n`,
      },
      {
        id: 'D',
        title: 'Syntax Broken (Missing semicolon)',
        expectedStatus: 'COMPILATION_ERROR',
        code: `module sync_counter_4bit (\n    input  wire       clk,\n    input  wire       rst_n,\n    input  wire       en,\n    output reg  [3:0] count\n);\n    always @(posedge clk) count <= 0\nendmodule\n`,
      },
      {
        id: 'E',
        title: 'Different Valid Style (Explicit decimal constants)',
        expectedStatus: 'ACCEPTED',
        code: `module sync_counter_4bit (\n    input  wire       clk,\n    input  wire       rst_n,\n    input  wire       en,\n    output reg  [3:0] count\n);\n    always @(posedge clk or negedge rst_n) begin\n        if (rst_n == 1'b0) count <= 4'd0;\n        else if (en == 1'b1) count <= count + 4'd1;\n        else count <= count;\n    end\nendmodule\n`,
      },
      {
        id: 'F',
        title: 'Cross-Challenge Solution (AND gate submitted to Counter)',
        expectedStatus: 'COMPILATION_ERROR',
        code: `module and_gate (\n    input  wire a,\n    input  wire b,\n    output wire y\n);\n    assign y = a & b;\nendmodule\n`,
      },
      {
        id: 'G',
        title: 'Submit Correct then Broken (Cache Invalidation)',
        expectedStatus: 'FAILED',
        code: `module sync_counter_4bit (\n    input  wire       clk,\n    input  wire       rst_n,\n    input  wire       en,\n    output reg  [3:0] count\n);\n    always @(posedge clk or negedge rst_n) begin\n        if (!rst_n) count <= 4'b0000;\n        else if (en) count <= count + 1'b1;\n    end\nendmodule\n`,
        secondaryCode: `module sync_counter_4bit (\n    input  wire       clk,\n    input  wire       rst_n,\n    input  wire       en,\n    output reg  [3:0] count\n);\n    always @(posedge clk) begin\n        if (!rst_n) count <= 4'b0000;\n        else count <= count + 1'b1;\n    end\nendmodule\n`,
      },
      {
        id: 'H',
        title: 'Comment-Only Trick (Old Regex Bug Check)',
        expectedStatus: 'FAILED',
        code: `module sync_counter_4bit (\n    input  wire       clk,\n    input  wire       rst_n,\n    input  wire       en,\n    output reg  [3:0] count\n);\n    /* count <= count + 1; */\n    always @(posedge clk) count <= 4'b0000;\nendmodule\n`,
      },
      {
        id: 'I',
        title: 'Resubmit Already-ACCEPTED (XP Idempotency)',
        expectedStatus: 'ACCEPTED',
        code: `module sync_counter_4bit (\n    input  wire       clk,\n    input  wire       rst_n,\n    input  wire       en,\n    output reg  [3:0] count\n);\n    always @(posedge clk or negedge rst_n) begin\n        if (!rst_n) count <= 4'b0000;\n        else if (en) count <= count + 1'b1;\n    end\nendmodule\n`,
      },
    ],
  },
  'xor-gate': {
    challengeId: 'ch-fund-xor-gate',
    moduleName: 'xor_gate',
    aliases: ['ch-fund-xor-gate', 'xor-gate', 'two-input-xor-gate'],
    totalVectors: 4,
    testbenchCode: XOR_GATE_TESTBENCH,
    testMatrix: [
      {
        id: 'A',
        title: 'Correct Solution (XOR operator ^)',
        expectedStatus: 'ACCEPTED',
        code: `module xor_gate (\n    input  wire a,\n    input  wire b,\n    output wire y\n);\n    assign y = a ^ b;\nendmodule\n`,
      },
      {
        id: 'B',
        title: 'Required Logic Removed (Empty Body)',
        expectedStatus: 'FAILED',
        code: `module xor_gate (\n    input  wire a,\n    input  wire b,\n    output wire y\n);\nendmodule\n`,
      },
      {
        id: 'C',
        title: 'Logic Changed Incorrectly (AND gate instead of XOR)',
        expectedStatus: 'FAILED',
        code: `module xor_gate (\n    input  wire a,\n    input  wire b,\n    output wire y\n);\n    assign y = a & b;\nendmodule\n`,
      },
      {
        id: 'D',
        title: 'Syntax Broken (Missing semicolon)',
        expectedStatus: 'COMPILATION_ERROR',
        code: `module xor_gate (\n    input  wire a,\n    input  wire b,\n    output wire y\n);\n    assign y = a ^ b\nendmodule\n`,
      },
      {
        id: 'E',
        title: 'Different Valid Style (Gate Primitive xor)',
        expectedStatus: 'ACCEPTED',
        code: `module xor_gate (\n    input  wire a,\n    input  wire b,\n    output wire y\n);\n    xor g1 (y, a, b);\nendmodule\n`,
      },
      {
        id: 'F',
        title: 'Cross-Challenge Solution (AND gate submitted to XOR)',
        expectedStatus: 'COMPILATION_ERROR',
        code: `module and_gate (\n    input  wire a,\n    input  wire b,\n    output wire y\n);\n    assign y = a & b;\nendmodule\n`,
      },
      {
        id: 'G',
        title: 'Submit Correct then Broken (OR gate replacement)',
        expectedStatus: 'FAILED',
        code: `module xor_gate (\n    input  wire a,\n    input  wire b,\n    output wire y\n);\n    assign y = a ^ b;\nendmodule\n`,
        secondaryCode: `module xor_gate (\n    input  wire a,\n    input  wire b,\n    output wire y\n);\n    assign y = a | b;\nendmodule\n`,
      },
      {
        id: 'H',
        title: 'Comment-Only Trick (Commented XOR, actual 0)',
        expectedStatus: 'FAILED',
        code: `module xor_gate (\n    input  wire a,\n    input  wire b,\n    output wire y\n);\n    /* assign y = a ^ b; */\n    assign y = 1'b0;\nendmodule\n`,
      },
      {
        id: 'I',
        title: 'Resubmit Already-ACCEPTED (XP Idempotency)',
        expectedStatus: 'ACCEPTED',
        code: `module xor_gate (\n    input  wire a,\n    input  wire b,\n    output wire y\n);\n    assign y = a ^ b;\nendmodule\n`,
      },
    ],
  },
};

/**
 * Pure dictionary lookup for challenge testbench configuration.
 * Never executes logic or regex on challengeId or code content.
 */
export function getTestbenchConfig(challengeIdOrSlug: string): ChallengeTestbenchConfig | null {
  if (!challengeIdOrSlug) return null;
  const key = challengeIdOrSlug.trim();
  
  // Direct match
  if (TESTBENCH_CATALOG[key]) {
    return TESTBENCH_CATALOG[key];
  }

  // Alias lookup
  for (const entry of Object.values(TESTBENCH_CATALOG)) {
    if (entry.challengeId === key || entry.aliases.includes(key)) {
      return entry;
    }
  }

  return null;
}

/**
 * Server-only helper to look up a specific test case definition for execution.
 */
export function getTestMatrixExecutable(challengeIdOrSlug: string, testId: string): TestCaseDef | null {
  const config = getTestbenchConfig(challengeIdOrSlug);
  if (!config) return null;
  return config.testMatrix.find((t) => t.id === testId) || null;
}
