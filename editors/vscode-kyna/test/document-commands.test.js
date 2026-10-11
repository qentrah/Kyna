// Verify formatter transport failures and inspection process ownership.
const assert = require('node:assert/strict');
const { EventEmitter } = require('node:events');
const { PassThrough } = require('node:stream');
const Module = require('node:module');
const test = require('node:test');
const errors = [];
const vscode = {
  Position: class { constructor(line, character) { Object.assign(this, { line, character }); } },
  Range: class { constructor(start, end) { Object.assign(this, { start, end }); } },
  TextEdit: { replace: (range, text) => ({ range, text }) },
  window: { showErrorMessage: message => errors.push(message) }
};
const original = Module._load;
Module._load = function(name, ...args) {
  if (name === 'vscode') return vscode;
  if (name === './cli') return { executable: () => 'ky' };
  return original.call(this, name, ...args);
};
const { createDocumentCommands } = require('../src/document-commands');
Module._load = original;
function setup() {
  errors.length = 0;
  const children = [], callbacks = [], output = [];
  const document = { fileName: '/project/main.ky', languageId: 'kyna', getText: () => 'x',
    positionAt: character => new vscode.Position(0, character), save: async () => true };
  vscode.window.activeTextEditor = { document };
  const child = () => {
    const process = new EventEmitter();
    process.stdin = new PassThrough(); process.stdout = new PassThrough(); process.stderr = new PassThrough();
    process.kill = () => { process.killed = true; }; children.push(process); return process;
  };
  const runner = { spawn: child, execFile: (_program, _args, _options, callback) => {
    callbacks.push(callback); return child();
  } };
  const commands = createDocumentCommands({ clear: () => { output.length = 0; },
    append: text => output.push(text), appendLine: text => output.push(text), show() {} }, runner);
  const token = { isCancellationRequested: false, onCancellationRequested: () => ({ dispose() {} }) };
  return { commands, token, document, children, callbacks, output };
}
test('formatter decodes Unicode split across output chunks', async () => {
  const s = setup();
  const pending = s.commands.formattingProvider.provideDocumentFormattingEdits(s.document, {}, s.token);
  s.children[0].stdout.write(Buffer.from([0xf0, 0x9f]));
  s.children[0].stdout.write(Buffer.from([0x98, 0x80, 0x0a]));
  s.children[0].emit('close', 0);
  assert.equal((await pending)[0].text, '😀\n'); assert.deepEqual(errors, []);
});
test('cancelled formatter tolerates a broken input pipe', async () => {
  const s = setup();
  const pending = s.commands.formattingProvider.provideDocumentFormattingEdits(s.document, {}, s.token);
  s.token.isCancellationRequested = true;
  s.children[0].stdin.emit('error', Object.assign(new Error('broken pipe'), { code: 'EPIPE' }));
  assert.deepEqual(await pending, []); assert.equal(s.children[0].killed, true); assert.deepEqual(errors, []);
});
test('formatter reports input failures and avoids starting pre-cancelled requests', async () => {
  const s = setup();
  s.token.isCancellationRequested = true;
  assert.deepEqual(await s.commands.formattingProvider.provideDocumentFormattingEdits(s.document, {}, s.token), []);
  assert.equal(s.children.length, 0);
  s.token.isCancellationRequested = false;
  const pending = s.commands.formattingProvider.provideDocumentFormattingEdits(s.document, {}, s.token);
  s.children[0].stdin.emit('error', new Error('input failed'));
  assert.deepEqual(await pending, []); assert.match(errors[0], /input failed/);
});
test('inspection ignores stale and disposed process output', async () => {
  const s = setup();
  await s.commands.inspectActive('tokens', 'Tokens');
  await s.commands.inspectActive('hir', 'HIR');
  assert.equal(s.children[0].killed, true);
  s.callbacks[0](null, 'old output', ''); assert.deepEqual(s.output, []);
  s.callbacks[1](null, 'new output', ''); assert.ok(s.output.includes('new output'));
  await s.commands.inspectActive('mir', 'MIR');
  s.commands.dispose(); assert.equal(s.children[2].killed, true);
  s.callbacks[2](null, 'late output', ''); assert.ok(!s.output.includes('late output'));
});
test('inspection stops after save failure', async () => {
  const s = setup(); s.document.save = async () => false;
  await s.commands.inspectActive('tokens', 'Tokens');
  assert.equal(s.children.length, 0); assert.match(errors[0], /could not be saved/);
});
