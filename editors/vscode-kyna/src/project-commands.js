// Owns project execution, route generation, and configuration commands.
const vscode = require('vscode');
const path = require('path');
const fs = require('fs');
const { executable } = require('./cli');
const { findProjectRoot, resolveProjectRoot, projectDocument } = require('./project-context');
async function runProjectTask(command, resource) {
  const root = await resolveProjectRoot(resource);
  if (!root) return;
  await vscode.workspace.saveAll(false);
  const labels = {
    run: 'Kyna Project · Run',
    dev: 'Kyna Project · Watch & Restart',
    install: 'Kyna Project · Install Dependencies'
  };
  const name = labels[command] || `Kyna ${command}`;
  const staleNames = command === 'install'
    ? ['Kyna Install', 'Install Dependencies']
    : ['Kyna Run', 'Kyna Project', 'Kyna Dev', 'Kyna Watch'];
  for (const terminal of vscode.window.terminals.filter(item =>
    staleNames.some(stale => item.name.includes(stale))))
    terminal.dispose();
  const folder = vscode.workspace.getWorkspaceFolder(vscode.Uri.file(root));
  const task = new vscode.Task(
    { type: 'kyna', command, project: root },
    folder || vscode.TaskScope.Workspace,
    name,
    'Kyna',
    new vscode.ProcessExecution(executable(projectDocument(root)),
      [command, '--color', 'always'], { cwd: root }),
    ['$kyna']
  );
  task.presentationOptions = {
    reveal: vscode.TaskRevealKind.Always,
    panel: vscode.TaskPanelKind.Dedicated,
    clear: command !== 'dev',
    focus: true,
    showReuseMessage: false
  };
  await vscode.tasks.executeTask(task);
}

async function openManifest(resource) {
  const root = await resolveProjectRoot(resource);
  if (!root) return;
  await vscode.window.showTextDocument(vscode.Uri.file(path.join(root, 'kyna.toml')));
}

async function openProjectFile(fileName, line = 0) {
  if (!fileName) return;
  const document = await vscode.workspace.openTextDocument(vscode.Uri.file(fileName));
  const position = new vscode.Position(Math.max(0, Math.min(line, document.lineCount - 1)), 0);
  await vscode.window.showTextDocument(document, { selection: new vscode.Range(position, position) });
}

function readServerAddress(root) {
  let source = '';
  try { source = fs.readFileSync(path.join(root, 'kyna.toml'), 'utf8'); } catch (_) { /* defaults */ }
  const configuredHost = source.match(/^host\s*=\s*"([^"]+)"/m)?.[1] || '127.0.0.1';
  const host = configuredHost === '0.0.0.0' || configuredHost === '::' ? '127.0.0.1' : configuredHost;
  const port = source.match(/^port\s*=\s*(\d+)/m)?.[1] || '3000';
  return { host, port };
}

async function openRouteEndpoint(routeOrResource) {
  const route = routeOrResource?.path ? routeOrResource : { path: '/' };
  const root = route.registryFile
    ? path.dirname(path.dirname(path.dirname(route.registryFile)))
    : await resolveProjectRoot(routeOrResource);
  if (!root) return;
  let endpointPath = route.path || '/';
  for (const parameter of route.parameters || []) {
    const value = await vscode.window.showInputBox({
      title: `Open ${route.method?.toUpperCase() || 'GET'} ${route.path}`,
      prompt: `Value for :${parameter}`,
      placeHolder: parameter
    });
    if (value === undefined) return;
    endpointPath = endpointPath.replace(`:${parameter}`, encodeURIComponent(value));
  }
  const { host, port } = readServerAddress(root);
  await vscode.commands.executeCommand('simpleBrowser.show', `http://${host}:${port}${endpointPath}`);
}

function validateRoutePath(value) {
  if (!value.startsWith('/')) return 'The URL path must begin with /.';
  if (/[?#\s"]/.test(value)) return 'Do not include a query, fragment, whitespace, or quote.';
  const parameters = new Set();
  for (const segment of value.slice(1).split('/')) {
    if (!segment) return value === '/' ? undefined : 'The path cannot contain empty segments.';
    if (segment.startsWith(':')) {
      const parameter = segment.slice(1);
      if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(parameter))
        return 'Route parameters must look like :userId.';
      if (parameters.has(parameter)) return `Duplicate route parameter :${parameter}.`;
      parameters.add(parameter);
    } else if (!/^[A-Za-z0-9._~-]+$/.test(segment)) {
      return `Unsupported characters in “${segment}”.`;
    }
  }
  return undefined;
}

async function generateRoute(resource) {
  const root = await resolveProjectRoot(resource);
  if (!root) return;
  const methodChoice = await vscode.window.showQuickPick(
    [
      { label: 'GET', description: 'Read a resource' },
      { label: 'POST', description: 'Create a resource' },
      { label: 'PUT', description: 'Replace a resource' },
      { label: 'PATCH', description: 'Update part of a resource' },
      { label: 'DELETE', description: 'Delete a resource' }
    ],
    { title: 'Generate Kyna Route', placeHolder: 'Select the HTTP method' }
  );
  if (!methodChoice) return;
  const method = methodChoice.label;
  const name = await vscode.window.showInputBox({
    title: 'Generate Kyna Route',
    prompt: 'Module name (creates src/routes/<name>.kyna)',
    placeHolder: 'users',
    validateInput: value => /^[A-Za-z0-9_-]+$/.test(value)
      ? undefined : 'Use letters, numbers, hyphens, or underscores.'
  });
  if (!name) return;
  const shape = await vscode.window.showQuickPick([
    { label: '/', description: 'Homepage / root route' },
    { label: `/${name}`, description: 'Static collection route' },
    { label: `/${name}/:id`, description: 'One named path parameter' },
    { label: `/${name}/:parentId/items/:itemId`, description: 'Nested route with multiple parameters' },
    { label: 'Custom path…', description: 'Enter any static or :parameter segment layout' }
  ], { title: 'Route Path', placeHolder: 'Choose a scalable route shape' });
  if (!shape) return;
  const routePath = await vscode.window.showInputBox({
    title: `${method} Route Path`,
    prompt: 'Named parameters become request.params; query strings arrive in request.query.',
    value: shape.label === 'Custom path…' ? `/${name}` : shape.label,
    validateInput: validateRoutePath
  });
  if (!routePath) return;
  await vscode.workspace.saveAll(false);
  await vscode.window.withProgress({
    location: vscode.ProgressLocation.Notification,
    title: `Generating ${method} ${routePath}`,
    cancellable: false
  }, () => new Promise((resolve, reject) => {
    childProcess.execFile(executable(projectDocument(root)),
      ['generate', 'route', name, '--method', method.toLowerCase(), '--path', routePath,
        '--no-color', '--no-interactive'],
      { cwd: root }, (error, stdout, stderr) => {
        if (error) reject(new Error(stderr.trim() || stdout.trim() || error.message));
        else resolve();
      });
  })).then(async () => {
    const uri = vscode.Uri.file(path.join(root, 'src', 'routes', `${name}.kyna`));
    await vscode.commands.executeCommand('kyna.routes.focus');
    const actions = method === 'GET' ? ['Open endpoint', 'Open route file'] : ['Open route file'];
    const action = await vscode.window.showInformationMessage(
      `Generated and registered ${method} ${routePath}.`, ...actions);
    if (action === 'Open endpoint') {
      await openRouteEndpoint({ method: method.toLowerCase(), path: routePath,
        parameters: [...routePath.matchAll(/:([A-Za-z_][A-Za-z0-9_]*)/g)].map(match => match[1]),
        registryFile: path.join(root, 'src', 'routes', 'index.kyna') });
    } else {
      await vscode.window.showTextDocument(uri);
    }
  }, error => vscode.window.showErrorMessage(`Kyna route generation failed: ${error.message}`));
}

async function configureProject(resource) {
  const root = await resolveProjectRoot(resource);
  if (!root) return;
  const uri = vscode.Uri.file(path.join(root, 'kyna.toml'));
  const document = await vscode.workspace.openTextDocument(uri);
  const source = document.getText();
  const currentHost = source.match(/^host\s*=\s*"([^"]+)"/m)?.[1] || '127.0.0.1';
  const currentPort = source.match(/^port\s*=\s*(\d+)/m)?.[1] || '3000';
  const host = await vscode.window.showInputBox({ title: 'Kyna Backend Host', value: currentHost });
  if (!host) return;
  const port = await vscode.window.showInputBox({
    title: 'Kyna Backend Port', value: currentPort,
    validateInput: value => /^\d+$/.test(value) && Number(value) > 0 && Number(value) <= 65535
      ? undefined : 'Enter a port from 1 to 65535.'
  });
  if (!port) return;
  let updated = source;
  if (/^\[server\]/m.test(updated)) {
    updated = updated.replace(/^host\s*=\s*"[^"]*"/m, `host = "${host.replace(/"/g, '')}"`);
    updated = updated.replace(/^port\s*=\s*\d+/m, `port = ${port}`);
  } else {
    updated += `\n[server]\nhost = "${host.replace(/"/g, '')}"\nport = ${port}\n`;
  }
  const edit = new vscode.WorkspaceEdit();
  edit.replace(uri, new vscode.Range(document.positionAt(0), document.positionAt(source.length)), updated);
  await vscode.workspace.applyEdit(edit);
  await document.save();
  vscode.window.showInformationMessage(
    `Kyna backend configured for http://${host}:${port}. kyna.toml now controls Run, Serve, and Dev.`);
}


module.exports = { runProjectTask, openManifest, openProjectFile, openRouteEndpoint, generateRoute, configureProject };
