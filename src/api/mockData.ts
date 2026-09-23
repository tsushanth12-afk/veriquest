/* ==========================================================================
   VeriQuest Mock Data — Plausible Hardware Engineering Seed Catalog
   ========================================================================== */

import { PublicChallenge } from '../types/challenge';
import { UserProfile } from '../types/user';
import { Quest, Badge, LeaderboardEntry } from '../types/quest';
import { RecentSubmissionSummary } from '../types/submission';

export const MOCK_USER: UserProfile = {
  id: 'usr_sushanth_vlsi',
  username: 'Sushanth',
  fullName: 'Sushanth K.',
  bio: 'ECE Student & FPGA Enthusiast. Learning Verilog for ASIC physical design and digital synthesis.',
  joinedDate: 'February 2026',
  stats: {
    level: 1,
    levelTitle: 'RTL Novice',
    currentXP: 0,
    nextLevelXP: 500,
    totalSolved: 0,
    easySolved: 0,
    mediumSolved: 0,
    hardSolved: 0,
    totalAttempts: 0,
    acceptanceRate: 0,
    currentStreak: 0,
    longestStreak: 0,
    globalRank: 1,
    weeklyRank: 1,
    percentile: 0,
  },
  topicMasteries: [
    { topic: 'Development Demo', percentage: 0, completed: 0, total: 1 },
  ],
};


export const MOCK_CHALLENGES: PublicChallenge[] = [
  {
    id: 'c0000000-0000-0000-0000-000000000001',
    title: 'Two-Input AND Gate (Development Demo)',
    slug: 'and-gate-demo',
    difficulty: 'Easy',
    category: 'Fundamentals',
    level: 1,
    xp: 40,
    estimatedMinutes: 10,
    description: 'Implement a basic 2-input AND gate in Verilog HDL. The output `y` must be high (`1`) if and only if both inputs `a` and `b` are high (`1`). When either input is low (`0`), the output must be low (`0`).',
    learningObjective: 'Learn fundamental continuous assignment and boolean operators in Verilog HDL.',
    constraints: [
      'Combinational logic only (no sequential clock/registers)',
      'Propagation delay: instantaneous (zero-delay simulation)',
    ],
    ioPins: [
      { name: 'a', direction: 'input', width: '[0:0]', description: 'First boolean operand' },
      { name: 'b', direction: 'input', width: '[0:0]', description: 'Second boolean operand' },
      { name: 'y', direction: 'output', width: '[0:0]', description: 'Boolean AND product' },
    ],
    examples: [
      { input: 'a = 0, b = 0', expectedOutput: 'y = 0', explanation: '0 & 0 = 0' },
      { input: 'a = 0, b = 1', expectedOutput: 'y = 0', explanation: '0 & 1 = 0' },
      { input: 'a = 1, b = 0', expectedOutput: 'y = 0', explanation: '1 & 0 = 0' },
      { input: 'a = 1, b = 1', expectedOutput: 'y = 1', explanation: '1 & 1 = 1' },
    ],
    hints: [
      'In Verilog, continuous assignments use the `assign` keyword: `assign y = a & b;`',
      'The `&` operator performs a bitwise boolean AND operation.',
    ],
    starterCode: `// Design a 2-input AND gate
// Output y should be 1 if and only if both a and b are 1.

module and_gate (
    input  wire a,
    input  wire b,
    output wire y
);

    // Enter your combinational logic here

endmodule
`,
    solved: false,
    attemptsCount: 0,
    acceptanceRate: 100,
  },
  {
    id: 'ch-fund-mux-2to1',
    title: '2-to-1 Multiplexer',
    slug: 'mux-2to1',
    difficulty: 'Easy',
    category: 'Combinational Logic',
    level: 1,
    xp: 50,
    estimatedMinutes: 10,
    description: 'Design a 2-to-1 multiplexer that selects between two single-bit inputs a and b using a select signal sel. When sel is 0, output y equals a. When sel is 1, output y equals b.',
    learningObjective: 'Master conditional data routing and multiplexer RTL implementation in Verilog HDL.',
    constraints: [
      'Pure combinational logic (instantaneous propagation)',
      'Inputs: a, b, sel. Output: y.',
    ],
    ioPins: [
      { name: 'a', direction: 'input', width: '[0:0]', description: 'Data input 0' },
      { name: 'b', direction: 'input', width: '[0:0]', description: 'Data input 1' },
      { name: 'sel', direction: 'input', width: '[0:0]', description: 'Channel select bit' },
      { name: 'y', direction: 'output', width: '[0:0]', description: 'Selected data output' },
    ],
    examples: [
      { input: 'sel = 0, a = 1, b = 0', expectedOutput: 'y = 1', explanation: 'sel=0 routes input a' },
      { input: 'sel = 1, a = 1, b = 0', expectedOutput: 'y = 0', explanation: 'sel=1 routes input b' },
    ],
    hints: [
      'You can use a continuous assignment with a conditional ternary operator: assign y = sel ? b : a;',
      'Alternatively, an always @(*) block with if-else or case(sel) can be used.',
    ],
    starterCode: `// Design a 2-to-1 Multiplexer
// When sel is 0, y = a. When sel is 1, y = b.

module mux_2to1 (
    input  wire a,
    input  wire b,
    input  wire sel,
    output wire y
);

    // Enter your combinational logic here

endmodule
`,
    solved: false,
    attemptsCount: 0,
    acceptanceRate: 100,
  },
  {
    id: 'ch-fund-xor-gate',
    title: 'Two-Input XOR Gate',
    slug: 'xor-gate',
    difficulty: 'Easy',
    category: 'Fundamentals',
    level: 1,
    xp: 45,
    estimatedMinutes: 10,
    description: 'Implement a basic 2-input XOR (exclusive OR) gate in Verilog HDL. The output y must be high (1) if and only if exactly one of the inputs a or b is high. When both inputs are low or both inputs are high, the output must be low (0).',
    learningObjective: 'Master exclusive disjunction and boolean operators in Verilog HDL.',
    constraints: [
      'Combinational logic only (no sequential clock/registers)',
      'Propagation delay: instantaneous (zero-delay simulation)',
    ],
    ioPins: [
      { name: 'a', direction: 'input', width: '[0:0]', description: 'First boolean operand' },
      { name: 'b', direction: 'input', width: '[0:0]', description: 'Second boolean operand' },
      { name: 'y', direction: 'output', width: '[0:0]', description: 'Boolean XOR product' },
    ],
    examples: [
      { input: 'a = 0, b = 1', expectedOutput: 'y = 1', explanation: 'Inputs differ -> output is 1' },
      { input: 'a = 1, b = 1', expectedOutput: 'y = 0', explanation: 'Inputs identical -> output is 0' },
    ],
    hints: [
      'You can use the bitwise XOR operator: assign y = a ^ b;',
      'Alternatively, you can instantiate the built-in primitive: xor g1(y, a, b);',
    ],
    starterCode: `// Design a Two-Input XOR Gate
// When exactly one input is 1, y = 1. Otherwise, y = 0.

module xor_gate (
    input  wire a,
    input  wire b,
    output wire y
);

    // Enter your combinational logic here

endmodule
`,
    solved: false,
    attemptsCount: 0,
    acceptanceRate: 100,
  },
  {
    id: 'ch-comb-priority-8to3',

    title: 'Priority Encoder 8-to-3',
    slug: 'priority-encoder-8to3',
    difficulty: 'Medium',
    category: 'Combinational Logic',
    level: 2,
    xp: 100,
    estimatedMinutes: 25,
    description: 'Design an 8-bit priority encoder that outputs the 3-bit binary index of the highest-order active bit (most significant bit). An additional active-high valid flag must indicate if any input bit is asserted.',
    learningObjective: 'Master priority resolution in HDL without causing synthesized latch inference or priority inversion glitches.',
    constraints: [
      'Input req is 8 bits [7:0]. req[7] has the highest priority, req[0] has lowest.',
      'Output grant is 3 bits [2:0] specifying index 0 to 7.',
      'Output valid is 1 bit: 1 if at least one bit of req is active, 0 if req == 8\'b00000000.',
      'Pure combinational logic; zero clock latency.',
    ],
    ioPins: [
      { name: 'req', direction: 'input', width: '[7:0]', description: '8-bit request bus' },
      { name: 'grant', direction: 'output', width: '[2:0]', description: 'Binary encoded index of highest active request' },
      { name: 'valid', direction: 'output', width: '[0:0]', description: 'Asserted when at least one request bit is high' },
    ],
    examples: [
      { input: 'req = 8\'b1000_0000', expectedOutput: 'grant = 3\'b111, valid = 1\'b1', explanation: 'Bit 7 is highest active' },
      { input: 'req = 8\'b0000_1010', expectedOutput: 'grant = 3\'b011, valid = 1\'b1', explanation: 'Bit 3 is highest active (overrides bit 1)' },
      { input: 'req = 8\'b0000_0000', expectedOutput: 'grant = 3\'b000, valid = 1\'b0', explanation: 'No requests active' },
    ],
    hints: [
      'You can use a cascade of if-else conditions or a casez statement with don\'t-care bits (?).',
      'Ensure all output signals are assigned in all branches to avoid unintentional latch generation.',
    ],
    starterCode: `module priority_enc_8to3 (
    input  wire [7:0] req,
    output reg  [2:0] grant,
    output reg        valid
);

    always @(*) begin
        // TODO: Implement 8-to-3 priority encoder logic
        grant = 3'b000;
        valid = 1'b0;
        
    end

endmodule
`,
    solved: false,
    attemptsCount: 2,
    acceptanceRate: 74,
  },
  {
    id: 'ch-comb-ripple-adder-4bit',
    title: '4-bit Ripple Carry Adder',
    slug: '4bit-ripple-carry-adder',
    difficulty: 'Medium',
    category: 'Combinational Logic',
    level: 2,
    xp: 100,
    estimatedMinutes: 20,
    description: 'Construct a 4-bit ripple carry adder from structural full adders, computing sum and carry-out from 4-bit operands A, B, and carry-in Cin.',
    learningObjective: 'Understand hierarchical module instantiation and carry propagation delay in arithmetic circuits.',
    constraints: [
      'Inputs: a[3:0], b[3:0], cin.',
      'Outputs: sum[3:0], cout.',
      'Synthesizable combinational RTL.',
    ],
    ioPins: [
      { name: 'a', direction: 'input', width: '[3:0]', description: 'Operand A' },
      { name: 'b', direction: 'input', width: '[3:0]', description: 'Operand B' },
      { name: 'cin', direction: 'input', width: '[0:0]', description: 'Carry input' },
      { name: 'sum', direction: 'output', width: '[3:0]', description: '4-bit sum output' },
      { name: 'cout', direction: 'output', width: '[0:0]', description: 'Carry output' },
    ],
    examples: [
      { input: 'a = 4\'b0101 (5), b = 4\'b0011 (3), cin = 0', expectedOutput: 'sum = 4\'b1000 (8), cout = 0' },
      { input: 'a = 4\'b1111 (15), b = 4\'b0001 (1), cin = 0', expectedOutput: 'sum = 4\'b0000 (0), cout = 1' },
    ],
    hints: [
      'Connect the carry-out of stage i to the carry-in of stage i+1 using internal wires.',
    ],
    starterCode: `module ripple_carry_adder_4bit (
    input  wire [3:0] a,
    input  wire [3:0] b,
    input  wire       cin,
    output wire [3:0] sum,
    output wire       cout
);

    // TODO: Instantiate 1-bit full adders or write carry logic
    assign {cout, sum} = a + b + cin;

endmodule
`,
    solved: true,
    attemptsCount: 3,
    acceptanceRate: 82,
  },
  {
    id: 'ch-fund-and-gate',
    title: 'Two-Input AND Gate',
    slug: 'and-gate',
    difficulty: 'Easy',
    category: 'Fundamentals',
    level: 1,
    xp: 40,
    estimatedMinutes: 5,
    description: 'Implement an elementary 2-input AND gate producing logic 1 if and only if both inputs A and B are 1.',
    learningObjective: 'Learn Verilog continuous assignment syntax (`assign`) and boolean operators.',
    constraints: ['Continuous assignment using the & operator.'],
    ioPins: [
      { name: 'a', direction: 'input', width: '[0:0]', description: 'Input A' },
      { name: 'b', direction: 'input', width: '[0:0]', description: 'Input B' },
      { name: 'out', direction: 'output', width: '[0:0]', description: 'Logical AND result' },
    ],
    examples: [
      { input: 'a=1, b=1', expectedOutput: 'out=1' },
      { input: 'a=1, b=0', expectedOutput: 'out=0' },
    ],
    hints: ['Use: assign out = a & b;'],
    starterCode: `module and_gate (
    input  wire a,
    input  wire b,
    output wire out
);

    assign out = a & b;

endmodule
`,
    solved: true,
    attemptsCount: 1,
    acceptanceRate: 98,
  },
  {
    id: 'ch-fund-mux-4to1',
    title: '4-to-1 Multiplexer',
    slug: '4-to-1-multiplexer',
    difficulty: 'Easy',
    category: 'Fundamentals',
    level: 1,
    xp: 50,
    estimatedMinutes: 15,
    description: 'Design a 4-to-1 multiplexer that routes one of four single-bit data inputs (d0, d1, d2, d3) to output Y based on a 2-bit select signal sel[1:0].',
    learningObjective: 'Understand conditional data routing and multiplexer synthesis.',
    constraints: ['sel is 2-bit [1:0].', 'No glitch transitions on unselected lines.'],
    ioPins: [
      { name: 'd', direction: 'input', width: '[3:0]', description: '4 data inputs d[3:0]' },
      { name: 'sel', direction: 'input', width: '[1:0]', description: '2-bit selection code' },
      { name: 'y', direction: 'output', width: '[0:0]', description: 'Routed output' },
    ],
    examples: [
      { input: 'd=4\'b1010, sel=2\'b01', expectedOutput: 'y=1', explanation: 'Selects bit d[1] = 1' },
    ],
    hints: ['Can use case(sel) or ternary operator conditional.'],
    starterCode: `module mux_4to1 (
    input  wire [3:0] d,
    input  wire [1:0] sel,
    output reg        y
);

    always @(*) begin
        case (sel)
            2'b00: y = d[0];
            2'b01: y = d[1];
            2'b10: y = d[2];
            2'b11: y = d[3];
            default: y = 1'b0;
        endcase
    end

endmodule
`,
    solved: true,
    attemptsCount: 1,
    acceptanceRate: 94,
  },
  {
    id: 'ch-seq-sync-counter-4bit',
    title: '4-bit Synchronous Counter',
    slug: '4-bit-counter',
    difficulty: 'Medium',
    category: 'Sequential Logic',
    level: 3,
    xp: 90,
    estimatedMinutes: 20,
    description: 'Implement a 4-bit synchronous up-counter with active-low asynchronous reset (rst_n) and active-high count enable (en). Rolls over from 15 to 0.',
    learningObjective: 'Master synchronous state registers and non-blocking assignments (`<=`).',
    constraints: ['Synchronous to positive clock edge posedge clk.', 'Asynchronous rst_n.'],
    ioPins: [
      { name: 'clk', direction: 'input', width: '[0:0]', description: 'Master clock input' },
      { name: 'rst_n', direction: 'input', width: '[0:0]', description: 'Active-low async reset' },
      { name: 'en', direction: 'input', width: '[0:0]', description: 'Count enable' },
      { name: 'count', direction: 'output', width: '[3:0]', description: 'Current count value' },
    ],
    examples: [
      { input: 'en=1 across 3 clock cycles', expectedOutput: 'count increments by 3' },
    ],
    hints: ['Use always @(posedge clk or negedge rst_n).'],
    starterCode: `module sync_counter_4bit (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       en,
    output reg  [3:0] count
);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            count <= 4'b0000;
        end else if (en) begin
            count <= count + 1'b1;
        end
    end

endmodule
`,
    solved: true,
    attemptsCount: 2,
    acceptanceRate: 85,
  },
  {
    id: 'ch-fsm-traffic-light',
    title: 'Traffic Light FSM',
    slug: 'traffic-light-fsm',
    difficulty: 'Hard',
    category: 'Finite State Machines',
    level: 4,
    xp: 140,
    estimatedMinutes: 40,
    description: 'Design a 4-state Moore Finite State Machine controlling main street and side street traffic lights with vehicle sensors.',
    learningObjective: 'Architect clean 3-process FSMs separating state register, next-state logic, and output decode.',
    constraints: ['Explicit state parameters or enum.', 'Zero race conditions between clock domains.'],
    ioPins: [
      { name: 'clk', direction: 'input', width: '[0:0]', description: 'Clock signal' },
      { name: 'rst_n', direction: 'input', width: '[0:0]', description: 'Active-low reset' },
      { name: 'car_present', direction: 'input', width: '[0:0]', description: 'Sensor flag' },
      { name: 'main_light', direction: 'output', width: '[1:0]', description: '2\'b00=Red, 01=Yellow, 10=Green' },
      { name: 'side_light', direction: 'output', width: '[1:0]', description: '2\'b00=Red, 01=Yellow, 10=Green' },
    ],
    examples: [
      { input: 'car_present = 1 when in Main Green', expectedOutput: 'Transitions through Yellow to Red after timer ticks' },
    ],
    hints: ['Split your FSM into current_state <= next_state and combinational next_state logic.'],
    starterCode: `module traffic_light_fsm (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       car_present,
    output reg  [1:0] main_light,
    output reg  [1:0] side_light
);

    // TODO: Define states and state transition logic

endmodule
`,
    solved: false,
    attemptsCount: 0,
    acceptanceRate: 61,
  },
  {
    id: 'ch-adv-sync-fifo',
    title: 'Parameterized Synchronous FIFO',
    slug: 'sync-fifo',
    difficulty: 'Hard',
    category: 'Advanced HDL',
    level: 5,
    xp: 180,
    estimatedMinutes: 50,
    description: 'Design a circular buffer FIFO queue with configurable DATA_WIDTH and DEPTH, supporting simultaneous read/write with overflow and underflow protection.',
    learningObjective: 'Implement dual pointer arithmetic, circular memory wrapping, and status flag generation in hardware.',
    constraints: ['Parameterized DATA_WIDTH=8, DEPTH=16.', 'Safe full/empty flag assertion.'],
    ioPins: [
      { name: 'clk', direction: 'input', width: '[0:0]', description: 'Clock' },
      { name: 'rst_n', direction: 'input', width: '[0:0]', description: 'Reset' },
      { name: 'wr_en', direction: 'input', width: '[0:0]', description: 'Write enable' },
      { name: 'rd_en', direction: 'input', width: '[0:0]', description: 'Read enable' },
      { name: 'din', direction: 'input', width: '[7:0]', description: 'Data input' },
      { name: 'dout', direction: 'output', width: '[7:0]', description: 'Data output' },
      { name: 'full', direction: 'output', width: '[0:0]', description: 'FIFO full flag' },
      { name: 'empty', direction: 'output', width: '[0:0]', description: 'FIFO empty flag' },
    ],
    examples: [
      { input: 'Write 16 items', expectedOutput: 'full asserts high' },
    ],
    hints: ['Use an extra bit in read and write pointers to distinguish between full and empty conditions.'],
    starterCode: `module sync_fifo #(
    parameter DATA_WIDTH = 8,
    parameter DEPTH = 16
)(
    input  wire                  clk,
    input  wire                  rst_n,
    input  wire                  wr_en,
    input  wire                  rd_en,
    input  wire [DATA_WIDTH-1:0] din,
    output reg  [DATA_WIDTH-1:0] dout,
    output wire                  full,
    output wire                  empty
);

    // TODO: FIFO RAM array and pointer management

endmodule
`,
    solved: false,
    attemptsCount: 1,
    acceptanceRate: 52,
  },
];

export const MOCK_QUESTS: Quest[] = [
  {
    id: 'quest-comb-logic',
    title: 'Master Combinational Logic',
    category: 'Combinational Logic',
    description: 'Synthesize standard arithmetic and multiplexing circuits with zero glitch hazards. Complete the full suite of ALU primitives and priority arbiters.',
    progressPercent: 75,
    completedChallenges: 6,
    totalChallenges: 8,
    xpReward: 300,
    currentChallengeId: 'ch-comb-priority-8to3',
    currentChallengeTitle: 'Priority Encoder 8-to-3',
    status: 'IN_PROGRESS',
  },
  {
    id: 'quest-seq-logic',
    title: 'Master Sequential Logic',
    category: 'Sequential Logic',
    description: 'Design robust clocked systems with zero setup or hold violations. Build shift registers, Johnson counters, and frequency dividers.',
    progressPercent: 20,
    completedChallenges: 2,
    totalChallenges: 10,
    xpReward: 400,
    currentChallengeId: 'ch-seq-sync-counter-4bit',
    currentChallengeTitle: '4-bit Synchronous Counter',
    status: 'IN_PROGRESS',
  },
  {
    id: 'quest-fsm-arch',
    title: 'FSM Architect',
    category: 'Finite State Machines',
    description: 'Master Mealy and Moore state machine synthesis. Design protocol controllers and sequence detectors with one-hot and binary encoding.',
    progressPercent: 0,
    completedChallenges: 0,
    totalChallenges: 8,
    xpReward: 500,
    currentChallengeId: 'ch-fsm-traffic-light',
    currentChallengeTitle: 'Traffic Light FSM',
    status: 'LOCKED',
  },
];

export const MOCK_BADGES: Badge[] = [
  {
    id: 'b-first-sub',
    name: 'First Simulation',
    description: 'Successfully pass all testbench vectors on your first Verilog module.',
    category: 'Logic',
    icon: 'Terminal',
    unlocked: true,
    unlockedAt: 'Feb 12, 2026',
    requirement: 'Pass 1 challenge testbench',
  },
  {
    id: 'b-logic-builder',
    name: 'Logic Builder',
    description: 'Complete all fundamental combinational logic modules with zero warnings.',
    category: 'Logic',
    icon: 'Cpu',
    unlocked: true,
    unlockedAt: 'Feb 18, 2026',
    requirement: 'Solve 10 Combinational challenges',
  },
  {
    id: 'b-sequential-master',
    name: 'Sequential Master',
    description: 'Demonstrate synchronous timing closure across 5 sequential modules.',
    category: 'Timing',
    icon: 'Clock',
    unlocked: true,
    unlockedAt: 'Mar 02, 2026',
    requirement: 'Solve 5 Sequential challenges',
  },
  {
    id: 'b-glitch-hunter',
    name: 'Glitch Hunter',
    description: 'Eliminate hazard paths in multiplexers and decoders.',
    category: 'Synthesis',
    icon: 'ShieldAlert',
    unlocked: true,
    unlockedAt: 'Mar 10, 2026',
    requirement: 'Solve 3 advanced multiplexer challenges',
  },
  {
    id: 'b-fsm-architect',
    name: 'FSM Architect',
    description: 'Design 8 race-free finite state machines with optimal state encoding.',
    category: 'Logic',
    icon: 'Workflow',
    unlocked: false,
    requirement: 'Solve 8 FSM challenges',
  },
  {
    id: 'b-timing-met',
    name: 'Zero Slack Violation',
    description: 'Achieve positive setup and hold slack on 5 clocked designs @ 100MHz+.',
    category: 'Timing',
    icon: 'Zap',
    unlocked: false,
    requirement: 'Synthesize 5 designs meeting 100MHz timing closure',
  },
  {
    id: 'b-silicon-craftsman',
    name: 'Silicon Craftsman',
    description: 'Reach Level 10 and accumulate over 3,000 Hardware XP.',
    category: 'Consistency',
    icon: 'Award',
    unlocked: false,
    requirement: 'Reach Level 10 (Current: Level 7)',
  },
];

export const MOCK_SUBMISSIONS: RecentSubmissionSummary[] = [
  {
    id: 'sub-01',
    challengeId: 'ch-comb-ripple-adder-4bit',
    challengeTitle: '4-bit Ripple Carry Adder',
    status: 'ACCEPTED',
    testsPassed: 20,
    totalTests: 20,
    xp: 100,
    timeAgo: '14m ago',
    timestamp: '2026-09-21T14:45:00Z',
  },
  {
    id: 'sub-02',
    challengeId: 'ch-seq-sync-counter-4bit',
    challengeTitle: '4-bit Synchronous Counter',
    status: 'ACCEPTED',
    testsPassed: 16,
    totalTests: 16,
    xp: 90,
    timeAgo: '2h ago',
    timestamp: '2026-09-21T12:55:00Z',
  },
  {
    id: 'sub-03',
    challengeId: 'ch-comb-priority-8to3',
    challengeTitle: 'Priority Encoder 8-to-3',
    status: 'FAILED',
    testsPassed: 15,
    totalTests: 20,
    xp: 0,
    timeAgo: '5h ago',
    timestamp: '2026-09-21T09:30:00Z',
  },
  {
    id: 'sub-04',
    challengeId: 'ch-fund-mux-4to1',
    challengeTitle: '4-to-1 Multiplexer',
    status: 'ACCEPTED',
    testsPassed: 10,
    totalTests: 10,
    xp: 50,
    timeAgo: '1d ago',
    timestamp: '2026-09-20T16:00:00Z',
  },
];

export const MOCK_LEADERBOARD: LeaderboardEntry[] = [
  { rank: 1, username: 'elena_fpga', avatarText: 'EF', level: 14, levelTitle: 'RTL Architect', xp: 4820, solvedCount: 142 },
  { rank: 2, username: 'chen_vlsi', avatarText: 'CV', level: 13, levelTitle: 'Silicon Lead', xp: 4350, solvedCount: 128 },
  { rank: 3, username: 'marcus_hdl', avatarText: 'MH', level: 12, levelTitle: 'Verification Eng', xp: 3910, solvedCount: 115 },
  { rank: 4, username: 'priya_asic', avatarText: 'PA', level: 11, levelTitle: 'Logic Designer', xp: 3420, solvedCount: 98 },
  { rank: 18, username: 'Sushanth', avatarText: 'SK', level: 7, levelTitle: 'HDL Explorer', xp: 1240, solvedCount: 68, isCurrentUser: true },
  { rank: 19, username: 'david_vhdl', avatarText: 'DV', level: 7, levelTitle: 'HDL Explorer', xp: 1210, solvedCount: 65 },
  { rank: 20, username: 'sara_digital', avatarText: 'SD', level: 6, levelTitle: 'Logic Student', xp: 1080, solvedCount: 58 },
];
