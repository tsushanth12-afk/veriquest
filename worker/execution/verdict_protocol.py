"""Server-only capability protocol. Keep in sync with verdictProtocol.ts.

Templates and execution metadata are trusted; student HDL and all ordinary
stdout are not. The source capability restriction is required for token secrecy.
"""
import re
import secrets


def prepare_testbench(testbench: str) -> dict:
    original = lex(testbench)
    offset = 0
    significant_original = []
    for text, kind in original:
        if kind != 'trivia':
            significant_original.append((text, kind, offset))
        offset += len(text)
    displays = []
    for i in range(len(significant_original) - 4):
        part = significant_original[i:i+5]
        if (part[0][0] == '$display' and part[1][0] == '(' and part[2][1] == 'string'
                and part[3][0] == ')' and part[4][0] == ';'):
            displays.append((part[0][2], part[4][2] + 1, part[2][0]))
    totals = [item for item in displays if re.fullmatch(r'"TOTAL: [1-9][0-9]*"', item[2])]
    if len(totals) != 1 or len(totals[0][2]) > 17 or int(totals[0][2][8:-1]) > 1000000:
        raise ValueError('Unsupported trusted testbench contract')
    total = int(totals[0][2][8:-1])
    nonce = secrets.token_hex(32)
    code = testbench
    replacements = []
    for status in ('ACCEPTED', 'WRONG_ANSWER'):
        found = [item for item in displays if item[2] == f'"VERIQUEST_STATUS: {status}"']
        if len(found) != 1:
            raise ValueError('Missing or duplicate grader emitter')
        replacements.append((found[0][0], found[0][1], f'$display("VQ_TRUSTED:{nonce}:{status}:{total}:%0d:%0d", passed, failed);'))
    for start, end, value in sorted(replacements, reverse=True):
        code = code[:start] + value + code[end:]
    tokens = lex(code)
    significant = [(text, kind) for text, kind in tokens if kind != 'trivia']
    reserved = set()
    for i, (keyword, _) in enumerate(significant):
        if keyword == 'function':
            raise ValueError('Unsupported trusted declaration profile')
        if keyword not in ('module', 'task', 'integer'):
            continue
        j = i + 1 + (i + 1 < len(significant) and significant[i + 1][0] == 'automatic')
        if j >= len(significant) or significant[j][1] != 'identifier' or significant[j][0].startswith('$'):
            raise ValueError('Unsupported trusted declaration profile')
        suffix = ';' if j + 1 < len(significant) and significant[j + 1][0] == ';' else ''.join(text for text, _ in significant[j+1:j+4])
        if (keyword in ('module', 'task') and not suffix.startswith(';')) or (keyword == 'integer' and suffix not in (';', '=0;')):
            raise ValueError('Unsupported trusted declaration profile')
        reserved.add(significant[j][0])
    if (not {'passed', 'failed'} <= reserved or any(not any(
            significant[i][0] == 'integer' and significant[i+1][0] == name
            and [text for text, _ in significant[i+2:i+5]] == ['=', '0', ';']
            for i in range(len(significant) - 4)) for name in ('passed', 'failed'))):
        raise ValueError('Missing grader counters')
    rewritten = []
    previous = ''
    for text, kind in tokens:
        rewritten.append('__vq_grader_' + text if kind == 'identifier' and previous != '.' and text in reserved else text)
        if kind != 'trivia':
            previous = text
    code = ''.join(rewritten)
    return dict(code=code, nonce=nonce, total=total,
                reserved={'__vq_grader_' + name for name in reserved})


def validate_student_source(source: str, reserved: set) -> None:
    safe_calls = {'$display', '$write', '$strobe', '$monitor', '$time', '$realtime',
                  '$signed', '$unsigned', '$clog2', '$bits', '$finish', '$fatal', '$isunknown'}
    forbidden = {'bind', 'defparam', 'force', 'release', 'import', 'export',
                 'program', 'interface', 'package', 'config'}
    source = source.replace('\r', '\n')
    tokens = lex(source)
    code = []
    offset = 0
    i = 0
    while i < len(tokens):
        token, kind = tokens[i]
        if kind == 'trivia':
            offset += len(token)
            i += 1
            continue
        if kind == 'string':
            code.append('STRING')
            offset += len(token)
            i += 1
            continue
        if (token == '`' and re.search(r'(?:^|\n)[ \t]*$', source[:offset])
                and re.match(r'`timescale[ \t]+[0-9]+(?:s|ms|us|ns|ps|fs)[ \t]*/[ \t]*[0-9]+(?:s|ms|us|ns|ps|fs)[ \t]*(?=\n|$)', source[offset:])):
            while i + 1 < len(tokens) and '\n' not in tokens[i + 1][0]:
                offset += len(tokens[i][0])
                i += 1
            offset += len(tokens[i][0])
            i += 1
            continue
        if (token in ('"', '`', '\\') or re.search(r'[^\x20-\x7e]', token)
                or (token.startswith('$') and token not in safe_calls)
                or token.startswith('__vq_grader_') or token in forbidden or token in reserved):
            raise ValueError(f'Unsupported HDL capability or reserved grader identifier: {token}')
        code.append(token)
        offset += len(token)
        i += 1
    for i, token in enumerate(code):
        if token == '.' and not (i > 0 and i + 2 < len(code) and code[i-1] in ('(', ',')
                and re.fullmatch(r'[A-Za-z_][A-Za-z0-9_$]*', code[i+1]) and code[i+2] in ('(', ',', ')')):
            raise ValueError('Hierarchical references are not permitted in student HDL')
        if token == ':' and i + 1 < len(code) and code[i+1] == ':':
            raise ValueError('Scope resolution is not permitted')


_TOKEN = re.compile(r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\[^\r\n]|[^"\\\r\n])*"|(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?|[A-Za-z_$][A-Za-z0-9_$]*|\s+|[\s\S]')


def lex(source: str):
    result = []
    for match in _TOKEN.finditer(source):
        text = match[0]
        kind = ('trivia' if text.isspace() or text.startswith(('//', '/*')) else
                'string' if text.startswith('"') and text.endswith('"') and len(text) > 1 else
                'identifier' if re.match(r'[A-Za-z_$]', text) else
                'number' if re.match(r'[0-9]|\.[0-9]', text) else 'symbol')
        result.append((text, kind))
    return result


def parse_trusted_verdict(output: str, nonce: str, expected_total: int):
    if (not isinstance(nonce, str) or not re.fullmatch(r'[a-f0-9]{64}', nonce)
            or type(expected_total) is not int or not 0 < expected_total <= 1000000):
        return None
    lines = [line for line in output.replace('\r\n', '\n').split('\n') if nonce in line]
    if len(lines) != 1:
        return None
    number = r'(0|[1-9][0-9]{0,6})'
    match = re.fullmatch(rf'VQ_TRUSTED:{nonce}:(ACCEPTED|WRONG_ANSWER):{number}:{number}:{number}', lines[0])
    if not match:
        return None
    total, passed, failed = map(int, match.groups()[1:])
    if (total != expected_total or passed + failed != total
            or (match[1] == 'ACCEPTED') != (failed == 0)):
        return None
    return dict(status=match[1], total=total, passed=passed, failed=failed)
