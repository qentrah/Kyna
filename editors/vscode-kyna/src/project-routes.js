// Owns route registry discovery and presentation metadata.
const vscode = require('vscode');
const path = require('path');
const fs = require('fs');
const routeMethodPresentation = {
  get: { label: 'GET', icon: 'arrow-down', color: 'charts.green' },
  post: { label: 'POST', icon: 'add', color: 'charts.blue' },
  put: { label: 'PUT', icon: 'replace-all', color: 'charts.yellow' },
  patch: { label: 'PATCH', icon: 'edit', color: 'charts.orange' },
  delete: { label: 'DELETE', icon: 'trash', color: 'charts.red' }
};

function routeIcon(method) {
  const presentation = routeMethodPresentation[method] ||
    { icon: 'circle-filled', color: 'charts.purple' };
  return new vscode.ThemeIcon(presentation.icon, new vscode.ThemeColor(presentation.color));
}

function readRoutes(root) {
  const indexFile = path.join(root, 'src', 'routes', 'index.kyna');
  let source;
  try { source = fs.readFileSync(indexFile, 'utf8'); } catch (_) { return []; }
  const imports = new Map();
  for (const match of source.matchAll(/import\s+"([^"]+)"\s+as\s+([A-Za-z_][A-Za-z0-9_]*)\s*;/g))
    imports.set(match[2], path.resolve(path.dirname(indexFile), match[1]));
  const routes = [];
  const routeExpression = /app\.(get|post|put|patch|delete)\(\s*"([^"]+)"\s*,\s*([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)\s*\)\s*;/g;
  for (const match of source.matchAll(routeExpression)) {
    const parameters = [...match[2].matchAll(/:([A-Za-z_][A-Za-z0-9_]*)/g)].map(item => item[1]);
    routes.push({
      method: match[1], path: match[2], alias: match[3], handler: match[4],
      file: imports.get(match[3]) || indexFile,
      registryFile: indexFile,
      registryLine: source.slice(0, match.index).split('\n').length - 1,
      parameters
    });
  }
  return routes;
}


module.exports = { routeMethodPresentation, routeIcon, readRoutes };
