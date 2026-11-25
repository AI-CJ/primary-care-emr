// Retain the license text from the installed packages that contribute to
// the distributed JavaScript. No runtime requests or new dependencies.
import { existsSync, mkdirSync, readFileSync, copyFileSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = dirname(dirname(fileURLToPath(import.meta.url)))
const output = join(root, 'dist', 'third-party-notices', 'npm')
mkdirSync(output, { recursive: true })
const inventory = []
for (const name of ['react', 'react-dom', 'scheduler', 'vite']) {
  const directory = join(root, 'node_modules', name)
  const metadata = JSON.parse(readFileSync(join(directory, 'package.json'), 'utf8'))
  const files = ['LICENSE', 'LICENSE.md', 'LICENSE.txt', 'NOTICE', 'NOTICE.md', 'NOTICE.txt']
    .filter(file => existsSync(join(directory, file)))
  if (!files.some(file => file.startsWith('LICENSE'))) {
    throw new Error('Missing upstream license for ' + name)
  }
  inventory.push(name + ' ' + metadata.version + ' — ' + (metadata.license ?? 'see license text'))
  for (const file of files) {
    const destination = name + '-' + metadata.version + '-' + file
    copyFileSync(join(directory, file), join(output, destination))
    inventory.push('  ' + destination)
  }
}
writeFileSync(join(output, 'index.txt'), inventory.join('\n') + '\n', 'utf8')
