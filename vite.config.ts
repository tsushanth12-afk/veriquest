import react from '@vitejs/plugin-react'
import { defineConfig, type Plugin } from 'vite'
import { evaluate } from './src/evaluator/evaluator.ts'
import { getTestMatrixExecutable } from './src/evaluator/testbenchCatalog.ts'

// In-memory sliding-window rate limiter for live dev-server evaluation endpoints.
// Serves as an immediate stopgap protecting CPU/memory against floods/infinite loops.
// Keyed by client IP pending true per-user authentication.
interface RateLimitRecord {
  timestamps: number[];
}

const RATE_LIMIT_WINDOW_MS = 60_000; // 60-second sliding window
const MAX_REQUESTS_PER_WINDOW = 20;  // 20 requests per minute per IP

const clientRequests = new Map<string, RateLimitRecord>();

function getClientIp(req: any): string {
  const forwarded = req.headers['x-forwarded-for'];
  if (typeof forwarded === 'string' && forwarded.length > 0) {
    return forwarded.split(',')[0].trim();
  }
  return req.socket?.remoteAddress || req.connection?.remoteAddress || '127.0.0.1';
}

function checkRateLimit(ip: string): { allowed: boolean; retryAfterMs: number } {
  const now = Date.now();
  const windowStart = now - RATE_LIMIT_WINDOW_MS;

  // Prune expired entries to prevent memory leaks in long-running dev sessions
  if (clientRequests.size > 200) {
    for (const [key, record] of clientRequests.entries()) {
      record.timestamps = record.timestamps.filter((ts) => ts > windowStart);
      if (record.timestamps.length === 0) {
        clientRequests.delete(key);
      }
    }
  }

  let record = clientRequests.get(ip);
  if (!record) {
    record = { timestamps: [] };
    clientRequests.set(ip, record);
  }

  // Filter timestamps to the active 60-second sliding window
  record.timestamps = record.timestamps.filter((ts) => ts > windowStart);

  if (record.timestamps.length >= MAX_REQUESTS_PER_WINDOW) {
    const oldestInWindow = record.timestamps[0];
    const retryAfterMs = Math.max(1000, oldestInWindow + RATE_LIMIT_WINDOW_MS - now);
    return { allowed: false, retryAfterMs };
  }

  record.timestamps.push(now);
  return { allowed: true, retryAfterMs: 0 };
}

function iverilogEvaluatorPlugin(): Plugin {
  const handler = (req: any, res: any, next: any) => {
    const isEvaluate = req.url === '/api/internal/evaluate' && req.method === 'POST';
    const isMatrix = req.url === '/api/internal/evaluate-matrix' && req.method === 'POST';

    if (!isEvaluate && !isMatrix) {
      return next();
    }

    let body = '';
    req.on('data', (chunk: any) => {
      body += chunk.toString();
    });

    req.on('end', async () => {
      // 1. Enforce generic sliding-window rate limit (identically across all endpoints & challenges)
      const clientIp = getClientIp(req);
      const { allowed, retryAfterMs } = checkRateLimit(clientIp);

      if (!allowed) {
        res.setHeader('Content-Type', 'application/json');
        res.setHeader('Retry-After', Math.ceil(retryAfterMs / 1000).toString());
        res.statusCode = 429;
        res.end(JSON.stringify({
          status: 'RATE_LIMITED',
          message: `Too many evaluation requests. Rate limit of ${MAX_REQUESTS_PER_WINDOW} requests per minute exceeded.`,
          retryAfterMs,
        }));
        return;
      }

      // 2. Dispatch to specific evaluator handler
      if (isEvaluate) {
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
      } else if (isMatrix) {
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
      }
    });
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
