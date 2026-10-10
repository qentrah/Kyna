// Verify imported types, aliases, re-exports, visibility, and unsaved modules.
const test = require('node:test');
const assert = require('node:assert/strict');
const Module = require('node:module');
const path = require('node:path');
const documents = new Map();
function document(file, text) {
  const doc = { fileName: path.resolve('/project', file), getText: () => text };
  documents.set(doc.fileName, doc); return doc;
}
const vscode = { Uri: { file: fsPath => ({ fsPath }) }, workspace: {
  openTextDocument: async uri => {
    if (!documents.has(uri.fsPath)) throw new Error('missing module');
    return documents.get(uri.fsPath);
  }
} };
const load = Module._load;
Module._load = function(name, ...args) { return name === 'vscode' ? vscode : load.call(this, name, ...args); };
const { resolveImportedDeclaration } = require('../src/import-navigation');
Module._load = load;
test('named type aliases navigate to the unsaved exported declaration', async () => {
  const target = document('t.ky', 'export intf Shape { width: int; }\ntype Hidden = int;');
  const main = document('main.ky', 'import type { Shape as Local } from "./t";\nvar value: Local;');
  assert.deepEqual(await resolveImportedDeclaration(main, 'Local'), { document: target, name: 'Shape' });
  target.getText = () => 'export type Shape = int;';
  assert.deepEqual(await resolveImportedDeclaration(main, 'Local'), { document: target, name: 'Shape' });
  const privateImport = document('private.ky', 'import type { Hidden } from "./t.ky";');
  assert.equal(await resolveImportedDeclaration(privateImport, 'Hidden'), undefined);
});
test('namespace types resolve aliases and chained re-exports', async () => {
  const target = document('types.kyna', 'export type Original = int;');
  document('barrel.ky', 'export type { Original as Public } from "./types.kyna";');
  const main = document('namespace.ky', 'import type * as Types from "./barrel.ky";');
  assert.deepEqual(await resolveImportedDeclaration(main, 'Public', 'Types'), { document: target, name: 'Original' });
  const legacy = document('legacy.ky', 'import "./types.kyna" as Types;');
  assert.deepEqual(await resolveImportedDeclaration(legacy, 'Original', 'Types'), { document: target, name: 'Original' });
});
test('star re-exports terminate cycles and missing modules safely', async () => {
  document('cycle-a.ky', 'export type * from "./cycle-b.ky";');
  document('cycle-b.ky', 'export type * from "./cycle-a.ky";');
  const main = document('cycle.ky', 'import type { Missing } from "./cycle-a.ky";');
  assert.equal(await resolveImportedDeclaration(main, 'Missing'), undefined);
  const missing = document('missing.ky', 'import type { Missing } from "./absent.ky";');
  assert.equal(await resolveImportedDeclaration(missing, 'Missing'), undefined);
});
