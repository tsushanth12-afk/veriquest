/* ==========================================================================
   VeriQuest — Client-Safe Test Matrix Metadata Catalog
   Contains strictly display metadata (IDs, titles, expected statuses, descriptions)
   for rendering verification test matrices in the browser UI.

   SECURITY INVARIANT:
   This file is bundled into the client browser application.
   It MUST NEVER contain:
     - Raw Verilog testbench strings
     - Correct or broken solution source code
     - Expected raw simulation vector bitstrings or outputs
     - Confidential evaluation scripts
   ========================================================================== */

export interface TestCaseMetadata {
  id: string; // 'A' | 'B' | 'C' | 'D' | 'E' | 'F' | 'G' | 'H' | 'I'
  title: string;
  expectedStatus: string; // 'ACCEPTED' | 'FAILED' | 'COMPILATION_ERROR'
  description?: string;
}

export interface ChallengeMatrixMetadata {
  challengeId: string;
  aliases: string[];
  testMatrix: TestCaseMetadata[];
}

export const TEST_MATRIX_METADATA: Record<string, ChallengeMatrixMetadata> = {
  'and-gate-demo': {
    challengeId: 'c0000000-0000-0000-0000-000000000001',
    aliases: ['c0000000-0000-0000-0000-000000000001', 'and-gate-demo', 'ch-fund-and-gate', 'and-gate'],
    testMatrix: [
      {
        id: 'A',
        title: 'Correct Solution',
        expectedStatus: 'ACCEPTED',
        description: 'Verifies canonical continuous assignment behavior against hidden testbench.',
      },
      {
        id: 'B',
        title: 'Required Logic Removed (Empty Body)',
        expectedStatus: 'FAILED',
        description: 'Tests floating output / undriven wire detection.',
      },
      {
        id: 'C',
        title: 'Logic Changed Incorrectly (OR gate)',
        expectedStatus: 'FAILED',
        description: 'Tests functional simulation vector mismatch on test cases 2 and 3.',
      },
      {
        id: 'D',
        title: 'Syntax Broken (Missing semicolon)',
        expectedStatus: 'COMPILATION_ERROR',
        description: 'Tests Icarus Verilog compiler syntax error capture.',
      },
      {
        id: 'E',
        title: 'Same Logic, Valid Gate Primitive Style',
        expectedStatus: 'ACCEPTED',
        description: 'Verifies structural primitive gate modeling equivalence.',
      },
      {
        id: 'F',
        title: 'Cross-Challenge Solution (MUX submitted to AND)',
        expectedStatus: 'COMPILATION_ERROR',
        description: 'Tests top-level module name and port signature mismatch detection.',
      },
      {
        id: 'G',
        title: 'Submit Correct then Broken (Cache Invalidation)',
        expectedStatus: 'FAILED',
        description: 'Verifies sequential cache invalidation and fresh compile execution.',
      },
      {
        id: 'H',
        title: 'Comment-Only Trick (Old Regex Bug Check)',
        expectedStatus: 'FAILED',
        description: 'Ensures commented-out code cannot trick AST or evaluation pipeline.',
      },
      {
        id: 'I',
        title: 'Resubmit Already-ACCEPTED (XP Idempotency)',
        expectedStatus: 'ACCEPTED',
        description: 'Verifies submission acceptance with zero duplicate XP awarded.',
      },
    ],
  },
  'mux-2to1': {
    challengeId: 'ch-fund-mux-2to1',
    aliases: ['ch-fund-mux-2to1', 'mux-2to1', '2-to-1-multiplexer'],
    testMatrix: [
      {
        id: 'A',
        title: 'Correct Solution (Ternary assign)',
        expectedStatus: 'ACCEPTED',
        description: 'Verifies ternary conditional multiplexer routing.',
      },
      {
        id: 'B',
        title: 'Required Logic Removed (Empty Body)',
        expectedStatus: 'FAILED',
        description: 'Tests detection of missing routing logic.',
      },
      {
        id: 'C',
        title: 'Logic Changed Incorrectly (Inverted select)',
        expectedStatus: 'FAILED',
        description: 'Tests inverted select channel routing failure.',
      },
      {
        id: 'D',
        title: 'Syntax Broken (Missing semicolon)',
        expectedStatus: 'COMPILATION_ERROR',
        description: 'Tests syntax compilation diagnostics.',
      },
      {
        id: 'E',
        title: 'Different Valid Style (Procedural always block)',
        expectedStatus: 'ACCEPTED',
        description: 'Tests procedural combinational always @(*) sensitivity block.',
      },
      {
        id: 'F',
        title: 'Cross-Challenge Solution (Counter submitted to MUX)',
        expectedStatus: 'COMPILATION_ERROR',
        description: 'Tests module signature incompatibility.',
      },
      {
        id: 'G',
        title: 'Submit Correct then Broken (Cache Invalidation)',
        expectedStatus: 'FAILED',
        description: 'Tests cache invalidation on modified multiplexer submissions.',
      },
      {
        id: 'H',
        title: 'Comment-Only Trick (Old Regex Bug Check)',
        expectedStatus: 'FAILED',
        description: 'Prevents bypasses using comments containing ternary expressions.',
      },
      {
        id: 'I',
        title: 'Resubmit Already-ACCEPTED (XP Idempotency)',
        expectedStatus: 'ACCEPTED',
        description: 'Verifies idempotency on repeated multiplexer submissions.',
      },
    ],
  },
  'sync-counter-4bit': {
    challengeId: 'ch-seq-sync-counter-4bit',
    aliases: ['ch-seq-sync-counter-4bit', 'sync-counter-4bit', '4-bit-counter'],
    testMatrix: [
      {
        id: 'A',
        title: 'Correct Solution (Async reset + enable)',
        expectedStatus: 'ACCEPTED',
        description: 'Verifies active-low asynchronous reset and clock-edge increment logic.',
      },
      {
        id: 'B',
        title: 'Required Logic Removed (Empty Body)',
        expectedStatus: 'FAILED',
        description: 'Tests floating register output detection.',
      },
      {
        id: 'C',
        title: 'Logic Changed Incorrectly (Synchronous reset only)',
        expectedStatus: 'FAILED',
        description: 'Tests sensitivity list async reset trigger requirement.',
      },
      {
        id: 'D',
        title: 'Syntax Broken (Missing semicolon)',
        expectedStatus: 'COMPILATION_ERROR',
        description: 'Tests sequential block syntax compilation diagnostics.',
      },
      {
        id: 'E',
        title: 'Different Valid Style (Explicit decimal constants)',
        expectedStatus: 'ACCEPTED',
        description: 'Tests alternative constant formatting in sequential models.',
      },
      {
        id: 'F',
        title: 'Cross-Challenge Solution (AND gate submitted to Counter)',
        expectedStatus: 'COMPILATION_ERROR',
        description: 'Tests clock/reset port mismatch.',
      },
      {
        id: 'G',
        title: 'Submit Correct then Broken (Cache Invalidation)',
        expectedStatus: 'FAILED',
        description: 'Tests state reset and cache invalidation.',
      },
      {
        id: 'H',
        title: 'Comment-Only Trick (Old Regex Bug Check)',
        expectedStatus: 'FAILED',
        description: 'Tests sequential comment bypass rejection.',
      },
      {
        id: 'I',
        title: 'Resubmit Already-ACCEPTED (XP Idempotency)',
        expectedStatus: 'ACCEPTED',
        description: 'Verifies XP idempotency on counter re-evaluations.',
      },
    ],
  },
  'xor-gate': {
    challengeId: 'ch-fund-xor-gate',
    aliases: ['ch-fund-xor-gate', 'xor-gate', 'two-input-xor-gate'],
    testMatrix: [
      {
        id: 'A',
        title: 'Correct Solution (XOR operator ^)',
        expectedStatus: 'ACCEPTED',
        description: 'Verifies bitwise XOR boolean evaluation.',
      },
      {
        id: 'B',
        title: 'Required Logic Removed (Empty Body)',
        expectedStatus: 'FAILED',
        description: 'Tests missing logic detection.',
      },
      {
        id: 'C',
        title: 'Logic Changed Incorrectly (AND gate instead of XOR)',
        expectedStatus: 'FAILED',
        description: 'Tests wrong truth table output vectors.',
      },
      {
        id: 'D',
        title: 'Syntax Broken (Missing semicolon)',
        expectedStatus: 'COMPILATION_ERROR',
        description: 'Tests compiler error capture.',
      },
      {
        id: 'E',
        title: 'Different Valid Style (Gate Primitive xor)',
        expectedStatus: 'ACCEPTED',
        description: 'Tests gate primitive modeling.',
      },
      {
        id: 'F',
        title: 'Cross-Challenge Solution (AND gate submitted to XOR)',
        expectedStatus: 'COMPILATION_ERROR',
        description: 'Tests module identifier collision.',
      },
      {
        id: 'G',
        title: 'Submit Correct then Broken (OR gate replacement)',
        expectedStatus: 'FAILED',
        description: 'Tests cache invalidation on gate re-evaluation.',
      },
      {
        id: 'H',
        title: 'Comment-Only Trick (Commented XOR, actual 0)',
        expectedStatus: 'FAILED',
        description: 'Tests comment bypass prevention.',
      },
      {
        id: 'I',
        title: 'Resubmit Already-ACCEPTED (XP Idempotency)',
        expectedStatus: 'ACCEPTED',
        description: 'Verifies idempotency on XOR gate resubmission.',
      },
    ],
  },
};

/**
 * Pure dictionary lookup for challenge test matrix metadata.
 * Safe for client-side bundle; contains no testbench or solution source.
 */
export function getTestMatrixMetadata(challengeIdOrSlug: string): ChallengeMatrixMetadata | null {
  if (!challengeIdOrSlug) return null;
  const key = challengeIdOrSlug.trim();

  // Direct match
  if (TEST_MATRIX_METADATA[key]) {
    return TEST_MATRIX_METADATA[key];
  }

  // Alias lookup
  for (const entry of Object.values(TEST_MATRIX_METADATA)) {
    if (entry.challengeId === key || entry.aliases.includes(key)) {
      return entry;
    }
  }

  return null;
}
