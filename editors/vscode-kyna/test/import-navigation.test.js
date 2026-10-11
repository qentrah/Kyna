// Verify imported types, aliases, re-exports, visibility, and unsaved modules.
const test = require('node:test');
const assert = require('node:assert/strict');
const Module = require('node:module');
const path = require('node:path');
const documents = new Map();
function document(file, text) {
  const doc = { fileName: path.resolve('/project', file), getText: range => range ? text.split('\n')[range.start.line].slice(range.start.character, range.end.character) : text,
    lineAt: line => ({ text: doc.getText().split('\n')[line] }),
    get lineCount() { return doc.getText().split('\n').length; },
    getWordRangeAtPosition: position => {
      const line = doc.lineAt(position.line).text;
      for (const match of line.matchAll(/[A-Za-z_]\w*/g))
        if (position.character >= match.index && position.character <= match.index + match[0].length)
          return { start: { line: position.line, character: match.index }, end: { line: position.line, character: match.index + match[0].length } };
    }
  };
  doc.uri = { fsPath: doc.fileName };
  documents.set(doc.fileName, doc); return doc;
}
class Position { constructor(line, character) { Object.assign(this, { line, character }); } }
class Location { constructor(uri, position) { Object.assign(this, { uri, position }); } }
class MarkdownString { constructor(value = '') { this.value = value; } appendMarkdown(value) { this.value += value; } }
class Hover { constructor(contents, range) { Object.assign(this, { contents, range }); } }
const vscode = { Position, Location, MarkdownString, Hover, CompletionItemKind: {}, Uri: { file: fsPath => ({ fsPath }) }, workspace: {
  openTextDocument: async uri => {
    if (!documents.has(uri.fsPath)) throw new Error('missing module');
    return documents.get(uri.fsPath);
  }
} };
const load = Module._load;
Module._load = function(name, ...args) { return name === 'vscode' ? vscode : load.call(this, name, ...args); };
const { resolveImportedDeclaration, exportedSymbols } = require('../src/import-navigation');
const { hoverProvider, definitionProvider } = require('../src/language-features');
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

test('hover and definition retain imported alias and namespace contracts', async () => {
  const target = document('hover-types.ky', 'export type Shape = int;');
  const main = document('hover.ky', 'import type { Shape as Local } from "./hover-types.ky";\nvar value: Local;');
  const position = { line: 1, character: 12 };
  const hover = await hoverProvider.provideHover(main, position);
  assert.match(hover.contents.value, /type Shape = int/);
  const definition = await definitionProvider.provideDefinition(main, position);
  assert.equal(definition.uri.fsPath, target.fileName);
  assert.equal(definition.position.line, 0);
  const namespaced = document('hover-namespace.ky', 'import type * as Types from "./hover-types.ky";\ntype Shape = bool;\nvar value: Types.Shape;');
  const memberPosition = { line: 2, character: 19 };
  const member = await hoverProvider.provideHover(namespaced, memberPosition);
  assert.match(member.contents.value, /type Shape = int/);
  assert.equal((await definitionProvider.provideDefinition(namespaced, memberPosition)).uri.fsPath, target.fileName);
});

test('namespace exports include unsaved aliases and re-exports, excluding private types', async () => {
  document('completion-types.ky', 'export type Public = int;\ntype Private = bool;');
  const barrel = document('completion-barrel.ky', 'export type { Public as Alias } from "./completion-types.ky";\nexport type * from "./completion-types.ky";');
  assert.deepEqual((await exportedSymbols(barrel)).map(item => item.name).sort(), ['Alias', 'Public']);
  barrel.getText = () => 'export type Edited = string;';
  assert.deepEqual((await exportedSymbols(barrel)).map(item => item.name), ['Edited']);
});

test('bare package navigation follows native locks and path dependencies with compiler suffix priority', async () => {
  const fs = require('node:fs');
  const os = require('node:os');
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'kyna-navigation-'));
  try {
    fs.writeFileSync(path.join(root, 'kyna.toml'), '[project]\n');
    const main = document(path.join(root,'src/main.ky'), 'import type { Shape } from "geometry";');
    const manifest = document(path.join(root,'kyna.toml'), '[dependencies.shapes]\npath = "vendor/types"');
    const lock = document(path.join(root,'.kyna/native.lock'), 'schema = "kyna.native-lock/v1"\n[[package]]\nmodule_root = ".kyna/native/geometry-hash"');
    const target = document(path.join(root,'.kyna/native/geometry-hash/geometry.ky'), 'export type Shape = int;');
    assert.deepEqual(await resolveImportedDeclaration(main,'Shape'),{document:target,name:'Shape'});
    const typed = document(path.join(root,'vendor/types/shapes.kyna.d'), 'export type Shape = string;');
    document(path.join(root,'vendor/types/shapes.ky'), 'export type Shape = bool;');
    main.getText=()=> 'import type { Shape } from "shapes";';
    assert.deepEqual(await resolveImportedDeclaration(main,'Shape'),{document:typed,name:'Shape'});
    lock.getText=()=> 'schema = "kyna.native-lock/v1"\n[[package]]\nmodule_root = "../outside"';
    main.getText=()=> 'import type { Shape } from "geometry";';
    assert.equal(await resolveImportedDeclaration(main,'Shape'),undefined);
    manifest.getText=()=> '[broken';
    assert.equal(await resolveImportedDeclaration(main,'Shape'),undefined);
  } finally { fs.rmSync(root,{recursive:true,force:true}); }
});
