// Owns formatting and active-document execution/inspection commands.
const vscode = require('vscode');
const path = require('path');
const fs = require('fs');
const childProcess = require('child_process');
const { executable } = require('./cli');
function createDocumentCommands(inspectionOutput) {
function formatDocument(document, token) {
  return new Promise((resolve, reject) => {
    const process = childProcess.spawn(executable(document),
      ['fmt', '-', '--source-name', document.fileName, '--no-color', '--no-interactive'],
      { cwd: path.dirname(document.fileName), stdio: ['pipe', 'pipe', 'pipe'] });
    let stdout = '';
    let stderr = '';
    process.stdout.on('data', chunk => { stdout += chunk.toString(); });
    process.stderr.on('data', chunk => { stderr += chunk.toString(); });
    const cancellation = token.onCancellationRequested(() => process.kill());
    process.on('error', error => { cancellation.dispose(); reject(error); });
    process.on('close', code => {
      cancellation.dispose();
      if (token.isCancellationRequested) return resolve([]);
      if (code !== 0) return reject(new Error(stderr.trim() || `ky fmt exited with ${code}`));
      const fullDocument = new vscode.Range(
        new vscode.Position(0, 0),
        document.positionAt(document.getText().length)
      );
      resolve(stdout === document.getText() ? [] : [vscode.TextEdit.replace(fullDocument, stdout)]);
    });
    process.stdin.end(document.getText());
  });
}

const formattingProvider = {
  async provideDocumentFormattingEdits(document, _options, token) {
    try {
      return await formatDocument(document, token);
    } catch (error) {
      vscode.window.showErrorMessage(`Kyna formatting failed: ${error.message}. Set kyna.executable if ky is not on PATH.`);
      return [];
    }
  }
};

async function runActive(command) {
  const editor = vscode.window.activeTextEditor;
  if (!editor || editor.document.languageId !== 'kyna') return;
  if (!await editor.document.save()) {
    vscode.window.showErrorMessage(`Kyna ${command} stopped because the active file could not be saved.`);
    return;
  }
  const program = executable(editor.document);
  const arguments = [command, editor.document.fileName, '--color', 'always'];
  const name = command === 'run' ? 'Kyna Run' : 'Kyna Check';
  const staleNames = command === 'run'
    ? ['Kyna Run', 'Kyna Project', 'Kyna Dev', 'Kyna Watch']
    : ['Kyna Check'];
  for (const existing of vscode.window.terminals.filter(terminal =>
    staleNames.some(stale => terminal.name.includes(stale))))
    existing.dispose();
  const folder = vscode.workspace.getWorkspaceFolder(editor.document.uri);
  const task = new vscode.Task(
    { type: 'kyna', command },
    folder || vscode.TaskScope.Workspace,
    name,
    'Kyna',
    new vscode.ProcessExecution(program, arguments, {
      cwd: path.dirname(editor.document.fileName)
    }),
    ['$kyna']
  );
  task.presentationOptions = {
    reveal: vscode.TaskRevealKind.Always,
    panel: vscode.TaskPanelKind.Dedicated,
    clear: true,
    focus: true,
    showReuseMessage: false
  };
  await vscode.tasks.executeTask(task);
}

async function inspectActive(command, title) {
  const editor = vscode.window.activeTextEditor;
  if (!editor || editor.document.languageId !== 'kyna') return;
  await editor.document.save();
  const document = editor.document;
  childProcess.execFile(executable(document),
    [command, document.fileName, '--no-color'],
    { cwd: path.dirname(document.fileName), maxBuffer: 8 * 1024 * 1024 },
    (error, stdout, stderr) => {
      inspectionOutput.clear();
      inspectionOutput.appendLine(`${title}: ${document.fileName}`);
      inspectionOutput.append(stdout);
      inspectionOutput.append(stderr);
      if (error && !stdout && !stderr) inspectionOutput.appendLine(error.message);
      inspectionOutput.show(true);
    });
}


return { formattingProvider, runActive, inspectActive };
}
module.exports = { createDocumentCommands };
