// Owns project discovery and selection.
const vscode = require('vscode');
const path = require('path');
const fs = require('fs');
function findProjectRoot(startPath) {
  let directory = startPath;
  try {
    if (fs.statSync(directory).isFile()) directory = path.dirname(directory);
  } catch (_) {
    directory = path.dirname(directory);
  }
  for (;;) {
    if (fs.existsSync(path.join(directory, 'kyna.toml'))) return directory;
    const parent = path.dirname(directory);
    if (parent === directory) return undefined;
    directory = parent;
  }
}

async function resolveProjectRoot(resource, allowSelection = true) {
  const candidate = resource?.fsPath || vscode.window.activeTextEditor?.document.fileName;
  const direct = candidate ? findProjectRoot(candidate) : undefined;
  if (direct) return direct;
  const manifests = await vscode.workspace.findFiles('**/kyna.toml', '**/{.git,node_modules,build,build-*}/**', 50);
  if (manifests.length === 0) {
    if (allowSelection)
      vscode.window.showWarningMessage('No kyna.toml project was found. Run “ky new” or “ky init” first.');
    return undefined;
  }
  if (manifests.length === 1) return path.dirname(manifests[0].fsPath);
  if (!allowSelection) return path.dirname(manifests[0].fsPath);
  const selected = await vscode.window.showQuickPick(
    manifests.map(uri => ({ label: path.basename(path.dirname(uri.fsPath)), description: path.dirname(uri.fsPath), uri })),
    { placeHolder: 'Select a Kyna project' }
  );
  return selected ? path.dirname(selected.uri.fsPath) : undefined;
}

function projectDocument(root) {
  const uri = vscode.Uri.file(path.join(root, 'kyna.toml'));
  return { fileName: uri.fsPath, uri };
}


module.exports = { findProjectRoot, resolveProjectRoot, projectDocument };
