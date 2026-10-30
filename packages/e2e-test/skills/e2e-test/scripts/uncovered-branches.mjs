#!/usr/bin/env node
// 从 istanbul 的 coverage-final.json 中列出未覆盖的分支和函数，供 AI 补测试用。
// 用法: node uncovered-branches.mjs [coverage-final.json] [路径前缀]
import fs from 'node:fs'
import path from 'node:path'

const [reportPath = 'coverage/e2e/coverage-final.json', prefix = ''] = process.argv.slice(2)

if (!fs.existsSync(reportPath)) {
  console.error(`Coverage report not found: ${reportPath}\nRun the coverage script first.`)
  process.exit(1)
}

const report = JSON.parse(fs.readFileSync(reportPath, 'utf8'))
const cwd = process.cwd()

const ARM_LABELS = {
  if: ['if-true', 'else'],
  'cond-expr': ['?-true', ':-false'],
}

function armLabel(type, index) {
  if (ARM_LABELS[type]) return ARM_LABELS[type][index] ?? `arm#${index}`
  if (type === 'binary-expr') return `operand#${index}`
  if (type === 'switch') return `case#${index}`
  return `arm#${index}`
}

let totalArms = 0
let coveredArms = 0
const sections = []

for (const [absPath, file] of Object.entries(report)) {
  const relPath = path.relative(cwd, absPath)
  if (prefix && !relPath.startsWith(prefix)) continue

  const gaps = []

  for (const [id, branch] of Object.entries(file.branchMap)) {
    file.b[id].forEach((hits, i) => {
      totalArms++
      if (hits > 0) {
        coveredArms++
        return
      }
      // if 没有 else 时，else 分支的 location 没有行号，退回用整个分支的位置
      const line = branch.locations?.[i]?.start?.line ?? branch.loc.start.line
      gaps.push({ line, text: `${branch.type} ${armLabel(branch.type, i)}` })
    })
  }

  for (const [id, fn] of Object.entries(file.fnMap)) {
    if (file.f[id] === 0) {
      gaps.push({ line: fn.loc.start.line, text: `function ${fn.name} never called` })
    }
  }

  if (gaps.length) {
    gaps.sort((a, b) => a.line - b.line)
    sections.push(`${relPath}\n${gaps.map((g) => `  L${g.line}  ${g.text}`).join('\n')}`)
  }
}

console.log(sections.length ? sections.join('\n\n') : 'No uncovered branches.')

const pct = totalArms ? ((coveredArms / totalArms) * 100).toFixed(1) : '100.0'
console.log(`\nBranch coverage${prefix ? ` (${prefix})` : ''}: ${coveredArms}/${totalArms} (${pct}%)`)
console.log('Note: files never loaded in the browser are not listed.')
