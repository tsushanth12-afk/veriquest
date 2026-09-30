/// <reference types="node" />
import { randomUUID } from 'node:crypto';
import { Worker } from 'node:worker_threads';

export type CapturedWasm = { stage: 'compile' | 'run' | 'capture'; compileExitCode: number | null;
  simulationExitCode: number | null; output: string; outputComplete: boolean; outputTruncated: boolean };

export function runBoundedWasm(source: string, testbench: string): Promise<CapturedWasm> {
  const worker = new Worker(new URL('./boundedWasmWorker.mjs', import.meta.url),
    { execArgv: process.execArgv.filter(arg => !arg.startsWith('--input-type')) });
  const id = randomUUID();
  return new Promise((resolve, reject) => {
    let settled = false;
    let timer = setTimeout(() => settle(new Error('Icarus compilation timed out')), 5000);
    function settle(value: CapturedWasm | Error) {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      worker.removeAllListeners();
      void worker.terminate().then(() => value instanceof Error ? reject(value) : resolve(value), reject);
    }
    worker.on('message', reply => {
      if (reply?.id !== id) return settle(new Error('Invalid Icarus worker reply'));
      if (reply.progress === 'compiled') {
        clearTimeout(timer);
        timer = setTimeout(() => settle(new Error('Icarus simulation timed out')), 5000);
        return;
      }
      if (reply.error) return settle(new Error(reply.error));
      const result = reply.result as CapturedWasm;
      if (!result || typeof result.output !== 'string' || typeof result.outputComplete !== 'boolean' ||
          typeof result.outputTruncated !== 'boolean') return settle(new Error('Invalid Icarus capture evidence'));
      settle(result);
    });
    worker.on('error', error => settle(error));
    worker.on('exit', code => settle(new Error(`Icarus worker exited ${code}`)));
    worker.postMessage({ id, source, testbench });
  });
}
