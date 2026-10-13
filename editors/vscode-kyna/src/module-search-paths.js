// Reads project dependency search roots with the same ordering as CLI sessions.
const vscode = require('vscode');
const path = require('path');
const os = require('os');
const { parse } = require('smol-toml');
const { findProjectRoot } = require('./project-context');

async function readTable(file) {
  try { return parse((await vscode.workspace.openTextDocument(vscode.Uri.file(file))).getText()); }
  catch (_) { return undefined; }
}
async function moduleSearchPaths(document) {
  const root = findProjectRoot(document.fileName);
  if (!root) return [];
  const paths = [];
  const lock = await readTable(path.join(root, '.kyna/native.lock'));
  if (lock?.schema === 'kyna.native-lock/v1' && Array.isArray(lock.package)) {
    for (const entry of lock.package) {
      if (typeof entry.module_root !== 'string') continue;
      const directory = path.resolve(root, entry.module_root);
      const relative = path.relative(root, directory);
      if (!relative || path.isAbsolute(relative) || relative === '..' || relative.startsWith('..'+path.sep)) continue;
      paths.push(directory);
    }
    paths.push(root);
  }
  const manifest = await readTable(path.join(root, 'kyna.toml'));
  for (const entry of Object.values(manifest?.dependencies || {})) {
    if (entry && typeof entry.path === 'string') paths.push(path.resolve(root, entry.path));
    else if (entry && typeof entry.git === 'string') {
      const cache = process.platform === 'win32' ? (process.env.LOCALAPPDATA ? path.join(process.env.LOCALAPPDATA,'Kyna/cache') : path.join(os.tmpdir(),'kyna-cache')) :
        process.platform === 'darwin' ? path.join(os.homedir(),'Library/Caches/Kyna') :
        path.join(process.env.XDG_CACHE_HOME || path.join(os.homedir(),'.cache'),'kyna');
      paths.push(path.join(cache,'git'));
    }
  }
  return paths;
}
module.exports = { moduleSearchPaths };
