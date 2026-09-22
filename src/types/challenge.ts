/* ==========================================================================
   VeriQuest Types — Public Challenge Contract (Student-Safe)
   ========================================================================== */

export type Difficulty = 'Easy' | 'Medium' | 'Hard';

export type ChallengeCategory = 
  | 'Fundamentals' 
  | 'Combinational Logic' 
  | 'Sequential Logic' 
  | 'Finite State Machines' 
  | 'Advanced HDL'
  | 'Development Demo';

export interface TestCaseExample {
  input: string;
  expectedOutput: string;
  explanation?: string;
}

export interface IOPin {
  name: string;
  direction: 'input' | 'output' | 'inout';
  width: string;
  description: string;
}

/**
 * PublicChallenge represents what the student client is authorized to see.
 * Strictly excludes: officialSolution, hiddenTestbench, executionProfile, internalGradingData.
 */
export interface PublicChallenge {
  id: string;
  title: string;
  slug: string;
  difficulty: Difficulty;
  category: ChallengeCategory;
  level: number;
  xp: number;
  estimatedMinutes: number;
  description: string;
  learningObjective: string;
  constraints: string[];
  ioPins: IOPin[];
  examples: TestCaseExample[];
  hints: string[];
  starterCode: string;
  solved: boolean;
  attemptsCount: number;
  acceptanceRate: number; // e.g. 74%
  prerequisiteId?: string;
}
