// TypeScript / JavaScript chunker using the real TypeScript compiler AST.
//
// Reads a JSON array of absolute file paths on stdin, writes a JSON array of
// chunks to stdout. Invoked by chunk.py; not usually run directly.
//
// Requires `typescript` to be resolvable. If it is not, this exits with code 3
// and chunk.py falls back to the generic structural chunker.

import { readFileSync } from 'node:fs'

let ts
try {
  ts = (await import('typescript')).default
} catch {
  process.stderr.write('typescript not resolvable\n')
  process.exit(3)
}

const readStdin = () =>
  new Promise((resolve) => {
    let buf = ''
    process.stdin.setEncoding('utf8')
    process.stdin.on('data', (d) => { buf += d })
    process.stdin.on('end', () => resolve(buf))
  })

const files = JSON.parse(await readStdin())
const chunks = []
const MIN_CHARS = 20

for (const file of files) {
  let text
  try { text = readFileSync(file, 'utf8') } catch { continue }

  const kind = /\.(tsx|jsx)$/.test(file) ? ts.ScriptKind.TSX : ts.ScriptKind.TS
  const sf = ts.createSourceFile(file, text, ts.ScriptTarget.ESNext, true, kind)
  const lines = text.split('\n')

  const emit = (node, type, name) => {
    const start = sf.getLineAndCharacterOfPosition(node.getStart(sf)).line + 1
    const end = sf.getLineAndCharacterOfPosition(node.getEnd()).line + 1
    const content = lines.slice(start - 1, end).join('\n')
    if (content.trim().length < MIN_CHARS) return
    chunks.push({ type, name: name || '<anon>', file, start_line: start, end_line: end, content })
  }

  const visit = (node) => {
    if (ts.isFunctionDeclaration(node)) emit(node, 'function', node.name?.text)
    else if (ts.isClassDeclaration(node)) emit(node, 'class', node.name?.text)
    else if (ts.isInterfaceDeclaration(node)) emit(node, 'interface', node.name.text)
    else if (ts.isTypeAliasDeclaration(node)) emit(node, 'type', node.name.text)
    else if (ts.isEnumDeclaration(node)) emit(node, 'enum', node.name.text)
    else if (ts.isMethodDeclaration(node) && ts.isIdentifier(node.name)) {
      emit(node, 'method', node.name.text)
    } else if (ts.isVariableStatement(node) && node.parent === sf) {
      for (const d of node.declarationList.declarations) {
        if (!ts.isIdentifier(d.name)) continue
        const init = d.initializer
        const isFn = init && (ts.isArrowFunction(init) || ts.isFunctionExpression(init))
        const isComponent = isFn && /\.(tsx|jsx)$/.test(file) && /^[A-Z]/.test(d.name.text)
        emit(node, isComponent ? 'component' : isFn ? 'function' : 'const', d.name.text)
      }
      return // already emitted this statement; do not descend
    }
    ts.forEachChild(node, visit)
  }
  ts.forEachChild(sf, visit)
}

process.stdout.write(JSON.stringify(chunks))
