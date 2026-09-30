/** Server-only capability protocol. Keep behavior in sync with verdict_protocol.py.
 * The token is secret from HDL only because validateStudentSource is mandatory.
 * Trusted templates use integer passed/failed and one literal TOTAL display.
 * Legacy stdout is diagnostic data, never a verdict or an assertion count.
 */
export function prepareTestbench(testbench: string, expectedTotal?: number) {
  const original = lex(testbench);
  let position = 0;
  const originalCode = original.map(t => { const item = { ...t, start: position }; position += t.text.length; return item; })
    .filter(t => t.kind !== 'trivia');
  const displays: { start: number; end: number; value: string }[] = [];
  for (let i = 0; i + 4 < originalCode.length; i++) {
    const part = originalCode.slice(i, i + 5);
    if (part[0].text === '$display' && part[1].text === '(' && part[2].kind === 'string' &&
        part[3].text === ')' && part[4].text === ';')
      displays.push({ start: part[0].start, end: part[4].start + 1, value: part[2].text });
  }
  const totals = displays.filter(d => /^"TOTAL: [1-9][0-9]*"$/.test(d.value));
  const total = Number(totals[0]?.value.slice(8, -1));
  if (totals.length !== 1 || !Number.isSafeInteger(total) || total > 1000000 ||
      (expectedTotal !== undefined && total !== expectedTotal))
    throw new Error('Unsupported trusted testbench contract');
  const nonce = Array.from(globalThis.crypto.getRandomValues(new Uint8Array(32)),
    byte => byte.toString(16).padStart(2, '0')).join('');
  let code = testbench;
  const replacements: { start: number; end: number; value: string }[] = [];
  for (const status of ['ACCEPTED', 'WRONG_ANSWER']) {
    const found = displays.filter(d => d.value === `"VERIQUEST_STATUS: ${status}"`);
    if (found.length !== 1) throw new Error('Missing or duplicate grader emitter');
    replacements.push({ ...found[0], value:
      `$display("VQ_TRUSTED:${nonce}:${status}:${total}:%0d:%0d", passed, failed);` });
  }
  for (const item of replacements.sort((a, b) => b.start - a.start))
    code = code.slice(0, item.start) + item.value + code.slice(item.end);
  // Put grader scope/tasks/counters in a reserved namespace. This prevents upward
  // resolution without banning ordinary DUT locals named i, passed, or failed.
  // Only the repository's simple task/integer template profile is supported.
  const tokens = lex(code);
  const significant = tokens.filter(t => t.kind !== 'trivia');
  const reserved = new Set<string>();
  for (let i = 0; i < significant.length; i++) {
    const keyword = significant[i].text;
    if (keyword === 'function') throw new Error('Unsupported trusted declaration profile');
    if (!['module', 'task', 'integer'].includes(keyword)) continue;
    let j = i + 1;
    if (significant[j]?.text === 'automatic') j++;
    const name = significant[j];
    if (!name || name.kind !== 'identifier' || name.text.startsWith('$'))
      throw new Error('Unsupported trusted declaration profile');
    if (keyword === 'module' || keyword === 'task') {
      if (significant[j + 1]?.text !== ';') throw new Error('Unsupported trusted declaration profile');
    } else {
      const suffix = significant[j + 1]?.text === ';' ? ';'
        : significant.slice(j + 1, j + 4).map(t => t.text).join('');
      if (suffix !== ';' && suffix !== '=0;') throw new Error('Unsupported trusted declaration profile');
    }
    reserved.add(name.text);
  }
  if (!reserved.has('passed') || !reserved.has('failed') ||
      !['passed', 'failed'].every(name => {
        const i = significant.findIndex((t, index) => t.text === 'integer' && significant[index + 1]?.text === name);
        return i >= 0 && significant.slice(i + 2, i + 5).map(t => t.text).join('') === '=0;';
      })) throw new Error('Missing grader counters');
  // Only lexical identifiers are rewritten. A comment/string mentioning a DUT
  // cannot add it to this set or change its instantiation.
  let previous = '';
  code = tokens.map(t => {
    if (t.kind === 'trivia') return t.text;
    const rewritten = t.kind === 'identifier' && previous !== '.' && reserved.has(t.text)
      ? `__vq_grader_${t.text}` : t.text;
    previous = t.text;
    return rewritten;
  }).join('');
  return { code, nonce, total, reserved: new Set([...reserved].map(name => `__vq_grader_${name}`)) };
}

export function validateStudentSource(source: string, reserved: Set<string>): void {
  // Deliberately restricted HDL profile, NOT a blacklist of known filesystem tasks.
  // No preprocessing, escaped identifiers, hierarchy, DPI/VPI, or unknown system calls.
  const safeCalls = new Set(['$display', '$write', '$strobe', '$monitor', '$time',
    '$realtime', '$signed', '$unsigned', '$clog2', '$bits', '$finish', '$fatal', '$isunknown']);
  const forbidden = new Set(['bind', 'defparam', 'force', 'release', 'import', 'export',
    'program', 'interface', 'package', 'config']);
  // Normalize lone CR for lexing too: it must not hide code in a // comment.
  const tokens = lex(source.replace(/\r/g, '\n'));
  const code: string[] = [];
  for (let i = 0; i < tokens.length; i++) {
    const { text: token, kind } = tokens[i];
    if (kind === 'trivia') continue;
    if (kind === 'string') { code.push('STRING'); continue; }
    if (token === '`' && tokens.slice(i + 1).find(t => t.kind !== 'trivia')?.text === 'timescale' &&
        /^`timescale[ \t]+(?:[0-9]+)(?:s|ms|us|ns|ps|fs)[ \t]*\/[ \t]*(?:[0-9]+)(?:s|ms|us|ns|ps|fs)[ \t]*(?=\r?\n|$)/.test(source.slice(tokens.slice(0, i).reduce((n, t) => n + t.text.length, 0))) &&
        /(?:^|\n)[ \t]*$/.test(source.slice(0, tokens.slice(0, i).reduce((n, t) => n + t.text.length, 0)))) {
      while (i + 1 < tokens.length && !tokens[i + 1].text.includes('\n')) i++;
      continue;
    }
    if (token === '"' || token === '`' || token === '\\' || /[^\x20-\x7e]/.test(token) ||
        (token.startsWith('$') && !safeCalls.has(token)) || token.startsWith('__vq_grader_') || forbidden.has(token) || reserved.has(token)) {
      throw new Error(`Unsupported HDL capability or reserved grader identifier: ${token}`);
    }
    code.push(token);
  }
  for (let i = 0; i < code.length; i++) {
    if (code[i] === '.' && !(('(' === code[i - 1] || ',' === code[i - 1]) &&
        /^[A-Za-z_][A-Za-z0-9_$]*$/.test(code[i + 1] || '') &&
        ['(', ',', ')'].includes(code[i + 2]))) {
      throw new Error('Hierarchical references are not permitted in student HDL');
    }
    if (code[i] === ':' && code[i + 1] === ':') throw new Error('Scope resolution is not permitted');
  }
}

type Token = { text: string; kind: 'trivia' | 'string' | 'identifier' | 'number' | 'symbol' };
function lex(source: string): Token[] {
  const pattern = /\/\/[^\n]*|\/\*[\s\S]*?\*\/|"(?:\\[^\r\n]|[^"\\\r\n])*"|(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?|[A-Za-z_$][A-Za-z0-9_$]*|\s+|[\s\S]/gy;
  const result: Token[] = [];
  for (const match of source.matchAll(pattern)) {
    const text = match[0];
    const kind = /^\s|^\/\//.test(text) || text.startsWith('/*') ? 'trivia'
      : text.startsWith('"') && text.endsWith('"') && text.length > 1 ? 'string'
      : /^[A-Za-z_$]/.test(text) ? 'identifier'
      : /^[0-9]/.test(text) || /^\.[0-9]/.test(text) ? 'number' : 'symbol';
    result.push({ text, kind });
  }
  return result;
}

export function parseTrustedVerdict(output: string, nonce: string, expectedTotal: number) {
  if (!/^[a-f0-9]{64}$/.test(nonce) || !Number.isSafeInteger(expectedTotal) || expectedTotal <= 0 || expectedTotal > 1000000) return null;
  const lines = output.split(/\r?\n/).filter(line => line.includes(nonce));
  if (lines.length !== 1) return null;
  const number = '(0|[1-9][0-9]{0,6})';
  const match = lines[0].match(new RegExp(`^VQ_TRUSTED:${nonce}:(ACCEPTED|WRONG_ANSWER):${number}:${number}:${number}$`));
  if (!match) return null;
  const [total, passed, failed] = match.slice(2).map(Number);
  if (![total, passed, failed].every(Number.isSafeInteger) || total !== expectedTotal ||
      passed + failed !== total || (match[1] === 'ACCEPTED') !== (failed === 0)) return null;
  return { status: match[1] as 'ACCEPTED' | 'WRONG_ANSWER', total, passed, failed };
}

export function redactVerdict(output: string, nonce: string): string {
  return (nonce ? output.replaceAll(nonce, '[grader-token]') : output).slice(0, 65536);
}
