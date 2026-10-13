// Owns extension activation and subscriptions.
const vscode = require('vscode');
const path = require('path');
const fs = require('fs');

const languageSelector = { language: 'kyna', scheme: 'file' };
const manifestSelector = { language: 'kyna-manifest', scheme: 'file' };
const { executable } = require('./src/cli');
const { createDiagnostics } = require('./src/diagnostics');
const { validate, scheduleValidation, closeDocument, disposeValidation, dependencyChanged } = createDiagnostics(executable);
const { createDocumentCommands } = require('./src/document-commands');
const { findProjectRoot, resolveProjectRoot } = require('./src/project-context');
const { runProjectTask, openManifest, openProjectFile, openRouteEndpoint, generateRoute, configureProject } = require('./src/project-commands');
const { KynaProjectProvider, KynaRoutesProvider, projectDecorations } = require('./src/project-views');
const { completionProvider, definitionProvider, hoverProvider, symbolProvider, codeLensProvider, manifestCodeLensProvider, manifestCompletionProvider } = require('./src/language-features');

function activate(context) {
  const diagnostics = vscode.languages.createDiagnosticCollection('kyna');
  const inspectionOutput = vscode.window.createOutputChannel('Kyna Compiler');
  const documentCommands = createDocumentCommands(inspectionOutput);
  context.subscriptions.push(documentCommands);
  const { formattingProvider, runActive, inspectActive } = documentCommands;
  const runButton = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 100);
  runButton.text = '$(play) Run Kyna';
  runButton.command = 'kyna.runFile';
  runButton.tooltip = 'Run the active Kyna file';
  const projectStatus = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 99);
  projectStatus.command = 'kyna.openManifest';
  const projectProvider = new KynaProjectProvider();
  const routesProvider = new KynaRoutesProvider();
  const manifestWatcher = vscode.workspace.createFileSystemWatcher('**/kyna.toml');
  const routesWatcher = vscode.workspace.createFileSystemWatcher('**/src/routes/**/*.kyna');

  const updateButton = editor => {
    if (editor && editor.document.languageId === 'kyna') runButton.show();
    else runButton.hide();
    const root = editor ? findProjectRoot(editor.document.fileName) : undefined;
    if (root) {
      try {
        const source = fs.readFileSync(path.join(root, 'kyna.toml'), 'utf8');
        const name = source.match(/^name\s*=\s*"([^"]+)"/m)?.[1] || path.basename(root);
        const template = source.match(/^template\s*=\s*"([^"]+)"/m)?.[1] || 'custom';
        projectStatus.text = `$(package) ${name}`;
        projectStatus.tooltip = `Kyna ${template} project · Open kyna.toml`;
        projectStatus.show();
      } catch (_) { projectStatus.hide(); }
    } else projectStatus.hide();
  };

  context.subscriptions.push(
    diagnostics,
    inspectionOutput,
    runButton,
    projectStatus,
    manifestWatcher,
    routesWatcher,
    vscode.window.registerTreeDataProvider('kyna.project', projectProvider),
    vscode.window.registerTreeDataProvider('kyna.routes', routesProvider),
    vscode.window.registerFileDecorationProvider(projectDecorations),
    vscode.commands.registerCommand('kyna.runFile', () => runActive('run')),
    vscode.commands.registerCommand('kyna.checkFile', () => runActive('check')),
    vscode.commands.registerCommand('kyna.showTokens', () => inspectActive('tokens', 'Tokens')),
    vscode.commands.registerCommand('kyna.showAst', () => inspectActive('ast', 'Syntax tree')),
    vscode.commands.registerCommand('kyna.showHir', () => inspectActive('hir', 'HIR')),
    vscode.commands.registerCommand('kyna.showMir', () => inspectActive('mir', 'MIR')),
    vscode.commands.registerCommand('kyna.showBytecode', () => inspectActive('bytecode', 'Bytecode')),
    vscode.commands.registerCommand('kyna.runProject', resource => runProjectTask('run', resource)),
    vscode.commands.registerCommand('kyna.devProject', resource => runProjectTask('dev', resource)),
    vscode.commands.registerCommand('kyna.installDependencies', resource => runProjectTask('install', resource)),
    vscode.commands.registerCommand('kyna.generateRoute', resource => generateRoute(resource).then(() => {
      projectProvider.refresh(); routesProvider.refresh();
    })),
    vscode.commands.registerCommand('kyna.configureProject', resource => configureProject(resource).then(() => projectProvider.refresh())),
    vscode.commands.registerCommand('kyna.openManifest', resource => openManifest(resource)),
    vscode.commands.registerCommand('kyna.openProjectFile', (file, line) => openProjectFile(file, line)),
    vscode.commands.registerCommand('kyna.openRoute', route => openProjectFile(route?.file, 0)),
    vscode.commands.registerCommand('kyna.openRouteEndpoint', route => openRouteEndpoint(route)),
    vscode.commands.registerCommand('kyna.openRoutesFolder', async resource => {
      const root = await resolveProjectRoot(resource);
      if (root) await vscode.commands.executeCommand(
        'revealInExplorer', vscode.Uri.file(path.join(root, 'src', 'routes')));
    }),
    vscode.commands.registerCommand('kyna.refreshRoutes', () => routesProvider.refresh()),
    vscode.languages.registerCompletionItemProvider(languageSelector, completionProvider, '.', '"', '/'),
    vscode.languages.registerCompletionItemProvider(manifestSelector, manifestCompletionProvider, '[', '=', ' '),
    vscode.languages.registerDefinitionProvider(languageSelector, definitionProvider),
    vscode.languages.registerHoverProvider(languageSelector, hoverProvider),
    vscode.languages.registerDocumentSymbolProvider(languageSelector, symbolProvider),
    vscode.languages.registerCodeLensProvider(languageSelector, codeLensProvider),
    vscode.languages.registerCodeLensProvider(manifestSelector, manifestCodeLensProvider),
    vscode.languages.registerDocumentFormattingEditProvider(languageSelector, formattingProvider),
    vscode.workspace.onDidOpenTextDocument(document => scheduleValidation(document, diagnostics)),
    vscode.workspace.onDidChangeTextDocument(event => {
      scheduleValidation(event.document, diagnostics);
      for (const document of vscode.workspace.textDocuments)
        if (document !== event.document) scheduleValidation(document, diagnostics);
    }),
    vscode.workspace.onDidSaveTextDocument(document => {
      validate(document, diagnostics);
      for (const dependent of vscode.workspace.textDocuments)
        if (dependent !== document) scheduleValidation(dependent, diagnostics);
      if (path.basename(document.fileName) === 'kyna.toml') projectProvider.refresh();
      if (document.fileName.includes(`${path.sep}src${path.sep}routes${path.sep}`)) {
        routesProvider.refresh(); projectProvider.refresh();
      }
    }),
    vscode.workspace.onDidCloseTextDocument(document => {
      closeDocument(document, diagnostics);
    }),
    vscode.window.onDidChangeActiveTextEditor(editor => {
      updateButton(editor);
      if (editor) scheduleValidation(editor.document, diagnostics);
    }),
    manifestWatcher.onDidCreate(() => projectProvider.refresh()),
    manifestWatcher.onDidChange(() => projectProvider.refresh()),
    manifestWatcher.onDidDelete(() => projectProvider.refresh()),
    routesWatcher.onDidCreate(() => { routesProvider.refresh(); projectProvider.refresh(); }),
    routesWatcher.onDidChange(() => { routesProvider.refresh(); projectProvider.refresh(); }),
    routesWatcher.onDidDelete(() => { routesProvider.refresh(); projectProvider.refresh(); })
  );
  const sourceWatcher = vscode.workspace.createFileSystemWatcher('**/*.{ky,kyna,kyna.d,ky.d}');
  context.subscriptions.push(sourceWatcher,
    sourceWatcher.onDidCreate(() => dependencyChanged(diagnostics)),
    sourceWatcher.onDidChange(() => dependencyChanged(diagnostics)),
    sourceWatcher.onDidDelete(() => dependencyChanged(diagnostics)));
  vscode.workspace.textDocuments.forEach(document => scheduleValidation(document, diagnostics));
  updateButton(vscode.window.activeTextEditor);
}

function deactivate() {
  disposeValidation();
}

module.exports = { activate, deactivate };
