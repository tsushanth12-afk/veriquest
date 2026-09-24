import react from '@vitejs/plugin-react'
import { defineConfig, type Plugin } from 'vite'
import { evaluate } from './src/evaluator/evaluator.ts'
import { getTestMatrixExecutable } from './src/evaluator/testbenchCatalog.ts'

function iverilogEvaluatorPlugin(): Plugin {
  const handler = (req: any, res: any, next: any) => {
    if (req.url === '/api/internal/evaluate' && req.method === 'POST') {
      let body = '';
      req.on('data', (chunk: any) => {
        body += chunk.toString();
      });
      req.on('end', async () => {
        try {
          const { challengeId, code } = JSON.parse(body || '{}');
          const result = await evaluate(challengeId, code);
          res.setHeader('Content-Type', 'application/json');
          res.statusCode = 200;
          res.end(JSON.stringify(result));
        } catch (err: any) {
          res.setHeader('Content-Type', 'application/json');
          res.statusCode = 500;
          res.end(JSON.stringify({
            status: 'SYSTEM_ERROR',
            success: false,
            testsPassed: 0,
            totalTests: 0,
            compilerOutput: `Internal Evaluator Error: ${err?.message || String(err)}`,
            executionTimeMs: 0,
            simulationNanoseconds: 0,
          }));
        }
      });
    } else if (req.url === '/api/internal/evaluate-matrix' && req.method === 'POST') {
      let body = '';
      req.on('data', (chunk: any) => {
        body += chunk.toString();
      });
      req.on('end', async () => {
        try {
          const { challengeId, testId } = JSON.parse(body || '{}');
          const testCase = getTestMatrixExecutable(challengeId, testId);
          if (!testCase) {
            res.setHeader('Content-Type', 'application/json');
            res.statusCode = 404;
            res.end(JSON.stringify({
              status: 'SYSTEM_ERROR',
              success: false,
              testsPassed: 0,
              totalTests: 0,
              compilerOutput: `Test case '${testId}' not found for challenge '${challengeId}'.`,
              executionTimeMs: 0,
              simulationNanoseconds: 0,
            }));
            return;
          }

          let result;
          if (testId === 'G' && testCase.secondaryCode) {
            // Test G: Submit first code, then submit second code to test cache invalidation
            await evaluate(challengeId, testCase.code);
            result = await evaluate(challengeId, testCase.secondaryCode);
          } else {
            result = await evaluate(challengeId, testCase.code);
          }

          // Return execution telemetry ONLY — zero source code, zero testbenches
          res.setHeader('Content-Type', 'application/json');
          res.statusCode = 200;
          res.end(JSON.stringify({
            testId,
            status: result.status,
            passed: result.success,
            testsPassed: result.testsPassed,
            totalTests: result.totalTests,
            executionTimeMs: result.executionTimeMs,
            simulationNanoseconds: result.simulationNanoseconds,
            compilerOutput: result.compilerOutput || '',
            failedVector: result.failedVector,
          }));
        } catch (err: any) {
          res.setHeader('Content-Type', 'application/json');
          res.statusCode = 500;
          res.end(JSON.stringify({
            status: 'SYSTEM_ERROR',
            success: false,
            testsPassed: 0,
            totalTests: 0,
            compilerOutput: `Internal Matrix Evaluator Error: ${err?.message || String(err)}`,
            executionTimeMs: 0,
            simulationNanoseconds: 0,
          }));
        }
      });
    } else {
      next();
    }
  };

  return {
    name: 'iverilog-evaluator-plugin',
    configureServer(server) {
      server.middlewares.use(handler);
    },
    configurePreviewServer(server) {
      server.middlewares.use(handler);
    },
  };
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), iverilogEvaluatorPlugin()],
})
