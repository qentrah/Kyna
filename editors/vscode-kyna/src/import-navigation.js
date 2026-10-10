// Resolves exported declarations through named/namespace imports and re-exports.
const vscode = require('vscode');
const path = require('path');
function bindings(list) {
  return list.split(',').map(value => value.trim().replace(/^type\s+/, ''))
    .map(value => value.match(/^([A-Za-z_]\w*)(?:\s+as\s+([A-Za-z_]\w*))?$/))
    .filter(Boolean).map(match => ({ original: match[1], local: match[2] || match[1] }));
}
function source(document) {
  return document.getText().replace(/^\s*#.*$/gm, line => ' '.repeat(line.length));
}
async function openModule(document, specifier) {
  if (!specifier.startsWith('.') && !path.isAbsolute(specifier)) return undefined;
  const base = path.resolve(path.dirname(document.fileName), specifier);
  const candidates = [base, ...['.ky', '.kyna', '.ky.d', '.kyna.d', '.d.ky'].map(suffix => base + suffix),
    path.join(base, 'index.ky'), path.join(base, 'index.kyna')];
  for (const file of candidates) {
    try { return await vscode.workspace.openTextDocument(vscode.Uri.file(file)); } catch (_) {}
  }
  return undefined;
}
async function resolveExport(document, name, seen) {
  const key = `${document.fileName}\0${name}`;
  if (seen.has(key) || seen.size >= 64) return undefined;
  seen.add(key);
  const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  if (new RegExp(`\\bexport\\s+(?:public\\s+)?(?:class|intf|type|fn|func|var|const|let|set)\\s+${escaped}\\b`).test(source(document)))
    return { document, name };
  for (const match of source(document).matchAll(/\bexport\s+(?:type\s+)?\{([^}]+)\}\s*(?:from\s*"([^"]+)")?\s*;/g)) {
    const binding = bindings(match[1]).find(item => item.local === name);
    if (!binding) continue;
    if (match[2]) {
      const target = await openModule(document, match[2]);
      return target ? resolveExport(target, binding.original, seen) : undefined;
    }
    const imported = await resolveImportedDeclaration(document, binding.original, undefined, seen);
    if (imported) return imported;
    const local = new RegExp(`\\b(?:class|intf|type|fn|func|var|const|let|set)\\s+${binding.original}\\b`);
    if (local.test(source(document))) return { document, name: binding.original };
  }
  // Star re-exports expose the original exported name.
  for (const match of source(document).matchAll(/\bexport\s+(?:type\s+)?\*\s+from\s*"([^"]+)"\s*;/g)) {
    const target = await openModule(document, match[1]);
    const declaration = target && await resolveExport(target, name, seen);
    if (declaration) return declaration;
  }
  return undefined;
}
async function resolveImportedDeclaration(document, name, receiver, seen = new Set()) {
  const text = source(document);
  for (const match of text.matchAll(/\bimport\s+(?:type\s+)?\{([^}]+)\}\s+from\s*"([^"]+)"\s*;/g)) {
    if (receiver) continue;
    const binding = bindings(match[1]).find(item => item.local === name);
    if (!binding) continue;
    const target = await openModule(document, match[2]);
    return target ? resolveExport(target, binding.original, seen) : undefined;
  }
  if (!receiver) return undefined;
  const patterns = [/\bimport\s+(?:type\s+)?"([^"]+)"\s+as\s+([A-Za-z_]\w*)\s*;/g,
    /\bimport\s+(?:type\s+)?\*\s+as\s+([A-Za-z_]\w*)\s+from\s*"([^"]+)"\s*;/g];
  for (let index = 0; index < patterns.length; index++) {
    for (const match of text.matchAll(patterns[index])) {
      const alias = match[index === 0 ? 2 : 1], specifier = match[index === 0 ? 1 : 2];
      if (alias !== receiver) continue;
      const target = await openModule(document, specifier);
      return target ? resolveExport(target, name, seen) : undefined;
    }
  }
  return undefined;
}
module.exports = { resolveImportedDeclaration };
