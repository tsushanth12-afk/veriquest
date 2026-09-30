// Server-only Icarus adapter. The upstream package buffers output without a cap;
// these print callbacks enforce the budget before retaining each line.
import { parentPort } from 'node:worker_threads';
import { fileURLToPath } from 'node:url';

const root = new URL('.', import.meta.resolve('@veriflow/iverilog-wasm'));
const LIMIT = 65536;
class OutputExceeded extends Error {}

function collector(id) {
  const chunks = [];
  let bytes = 0;
  let reported = false;
  function add(value) {
    const incoming = Buffer.byteLength(value, 'utf8') + 1;
    if (bytes + incoming > LIMIT) {
      if (!reported) {
        reported = true;
        parentPort.postMessage({ id, result: { stage: 'capture', compileExitCode: null,
          simulationExitCode: null, output: Buffer.concat(chunks, bytes).toString('utf8'),
          outputComplete: false, outputTruncated: true } });
      }
      throw new OutputExceeded('Simulator output limit exceeded');
    }
    const next = Buffer.from(`${value}\n`, 'utf8');
    chunks.push(next);
    bytes += next.length;
  }
  return { add, get text() { return Buffer.concat(chunks, bytes).toString('utf8'); } };
}

async function runtime(name, out) {
  const url = new URL(`runtime/${name}.mjs`, root);
  const factory = (await import(url.href)).default;
  return factory({ locateFile: file => fileURLToPath(new URL(file, url)),
    print: out.add, printErr: out.add });
}

function main(vm, args) {
  const prior = process.exitCode;
  try {
    try { return vm.callMain(args) ?? 0; }
    catch (error) {
      if (error instanceof OutputExceeded) throw error;
      if (Number.isInteger(error?.status)) return error.status;
      throw error;
    }
  } finally { process.exitCode = prior; }
}

function setup(vm) {
  vm.FS.mkdirTree('/work');
  vm.FS.mkdirTree('/.iverilog');
  vm.FS.chdir('/work');
}

async function execute({ id, source, testbench }) {
  const out = collector(id);
  try {
    const pp = await runtime('ivlpp', out);
    setup(pp);
    pp.FS.writeFile('/work/solution.v', source);
    pp.FS.writeFile('/work/testbench.v', testbench);
    pp.FS.writeFile('/.iverilog/ivlpp.flags', 'D:__ICARUS__=1\n');
    let exit = main(pp, ['-F', '/.iverilog/ivlpp.flags', '-L', '-o', '/.iverilog/preprocessed.v', 'testbench.v', 'solution.v']);
    if (exit !== 0) return { stage: 'compile', compileExitCode: exit, simulationExitCode: null, output: out.text, outputComplete: true, outputTruncated: false };
    const preprocessed = pp.FS.readFile('/.iverilog/preprocessed.v');
    const cc = await runtime('ivl', out);
    setup(cc);
    cc.FS.writeFile('/.iverilog/preprocessed.v', preprocessed);
    cc.FS.writeFile('/.iverilog/ivl.conf', [
      'basedir:/work', 'module:system.vpi', 'module:v2005_math.vpi', 'module:v2009.vpi',
      '-t:dll', 'flag:DLL=vvp.tgt', 'generation:2012', 'generation:no-specify',
      'out:/.iverilog/program.vvp', 'iwidth:32', 'widthcap:65536', 'functor:cprop', 'functor:nodangle', '',
    ].join('\n'));
    exit = main(cc, ['-C/.iverilog/ivl.conf', '--', '/.iverilog/preprocessed.v']);
    if (exit !== 0) return { stage: 'compile', compileExitCode: exit, simulationExitCode: null, output: out.text, outputComplete: true, outputTruncated: false };
    parentPort.postMessage({ id, progress: 'compiled' });
    const program = cc.FS.readFile('/.iverilog/program.vvp');
    const vm = await runtime('vvp', out);
    setup(vm);
    vm.FS.writeFile('/.iverilog/program.vvp', program);
    exit = main(vm, ['/.iverilog/program.vvp']);
    return { stage: 'run', compileExitCode: 0, simulationExitCode: exit, output: out.text, outputComplete: true, outputTruncated: false };
  } catch (error) {
    if (error instanceof OutputExceeded) return { stage: 'capture', compileExitCode: null, simulationExitCode: null,
      output: out.text, outputComplete: false, outputTruncated: true };
    throw error;
  }
}

parentPort.on('message', async request => {
  try { parentPort.postMessage({ id: request.id, result: await execute(request) }); }
  catch (error) { parentPort.postMessage({ id: request.id, error: String(error) }); }
});
