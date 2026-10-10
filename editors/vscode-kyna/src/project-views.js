// Owns project and route tree views.
const vscode = require('vscode');
const path = require('path');
const fs = require('fs');
const { resolveProjectRoot } = require('./project-context');
const { routeMethodPresentation, routeIcon, readRoutes } = require('./project-routes');
class KynaProjectProvider {
  constructor() { this.changed = new vscode.EventEmitter(); this.onDidChangeTreeData = this.changed.event; }
  refresh() { this.changed.fire(); }
  getTreeItem(item) { return item; }
  async getChildren(parent) {
    if (parent?.kind !== 'project') return parent ? [] : this.projectRoot();
    const root = parent.root;
    const manifestFile = path.join(root, 'kyna.toml');
    let source = '';
    try { source = fs.readFileSync(manifestFile, 'utf8'); } catch (_) { return []; }
    const host = source.match(/^host\s*=\s*"([^"]+)"/m)?.[1] || '127.0.0.1';
    const port = source.match(/^port\s*=\s*(\d+)/m)?.[1] || '3000';
    const entry = source.match(/^entry\s*=\s*"([^"]+)"/m)?.[1] || 'src/main.kyna';
    const dependencyBlock = source.match(/\[dependencies\]([\s\S]*?)(?=\n\[|$)/)?.[1] || '';
    const dependencyCount = dependencyBlock.split('\n').filter(line => /^\s*[A-Za-z0-9_-]+\s*=/.test(line)).length;
    const detail = (label, description, icon, file = manifestFile) => {
      const item = new vscode.TreeItem(label, vscode.TreeItemCollapsibleState.None);
      item.description = description;
      item.iconPath = new vscode.ThemeIcon(icon);
      item.command = { command: 'kyna.openProjectFile', title: `Open ${label}`, arguments: [file] };
      return item;
    };
    const routesItem = detail('Routes', `${readRoutes(root).length} registered`, 'type-hierarchy-sub');
    routesItem.command = {
      command: 'kyna.openRoutesFolder', title: 'Open Routes Folder',
      arguments: [vscode.Uri.file(root)]
    };
    return [
      (() => {
        const item = detail('Backend', `http://${host}:${port}`, 'radio-tower');
        item.command = { command: 'kyna.openRouteEndpoint', title: 'Open Backend',
          arguments: [{ path: '/', parameters: [], registryFile: path.join(root, 'src', 'routes', 'index.kyna') }] };
        return item;
      })(),
      detail('Entry point', entry, 'file-code', path.join(root, entry)),
      routesItem,
      detail('Dependencies', `${dependencyCount}`, 'package'),
      detail('Manifest', 'kyna.toml', 'settings-gear')
    ];
  }
  async projectRoot() {
    const root = await resolveProjectRoot(undefined, false);
    if (!root) return [];
    let source = '';
    try { source = fs.readFileSync(path.join(root, 'kyna.toml'), 'utf8'); } catch (_) { return []; }
    const name = source.match(/^name\s*=\s*"([^"]+)"/m)?.[1] || path.basename(root);
    const version = source.match(/^version\s*=\s*"([^"]+)"/m)?.[1] || '0.0.0';
    const header = new vscode.TreeItem(`${name} · ${version}`, vscode.TreeItemCollapsibleState.Expanded);
    header.description = source.match(/^template\s*=\s*"([^"]+)"/m)?.[1] || 'custom';
    header.iconPath = new vscode.ThemeIcon('package');
    header.kind = 'project';
    header.root = root;
    header.tooltip = `Kyna ${header.description} project\n${root}`;
    return [header];
  }
}

class KynaRoutesProvider {
  constructor() { this.changed = new vscode.EventEmitter(); this.onDidChangeTreeData = this.changed.event; }
  refresh() { this.changed.fire(); }
  getTreeItem(item) { return item; }
  async getChildren(parent) {
    const root = parent?.root || await resolveProjectRoot(undefined, false);
    if (!root) return [];
    const routes = readRoutes(root);
    if (parent?.kind === 'method') return this.routeItems(routes.filter(route => route.method === parent.method));
    if (parent) return [];
    return Object.keys(routeMethodPresentation).flatMap(method => {
      const count = routes.filter(route => route.method === method).length;
      if (!count) return [];
      const presentation = routeMethodPresentation[method];
      const item = new vscode.TreeItem(presentation.label, vscode.TreeItemCollapsibleState.Expanded);
      item.kind = 'method'; item.method = method; item.root = root;
      item.description = `${count} route${count === 1 ? '' : 's'}`;
      item.iconPath = routeIcon(method);
      item.contextValue = 'kynaRouteMethod';
      return [item];
    });
  }
  routeItems(routes) {
    return routes.map(route => {
      const presentation = routeMethodPresentation[route.method];
      const item = new vscode.TreeItem(route.path, vscode.TreeItemCollapsibleState.None);
      item.description = `${presentation.label} · ${path.basename(route.file)}`;
      item.iconPath = routeIcon(route.method);
      item.contextValue = route.method === 'get' ? 'kynaRouteGet' : 'kynaRoute';
      item.command = { command: 'kyna.openRoute', title: `Open ${presentation.label} ${route.path}`, arguments: [route] };
      item.accessibilityInformation = { label: `${presentation.label} route ${route.path}` };
      const details = [
        `**${presentation.label} ${route.path}**`, '',
        `Handler: \`${route.alias}.${route.handler}\``,
        `File: \`${path.relative(path.dirname(route.registryFile), route.file)}\``
      ];
      if (route.parameters.length) details.push(`Parameters: ${route.parameters.map(value => `\`:${value}\``).join(', ')}`);
      item.tooltip = new vscode.MarkdownString(details.join('\n\n'));
      return item;
    });
  }
}

const projectDecorations = {
  provideFileDecoration(uri) {
    const name = path.basename(uri.fsPath);
    if (name === 'health.kyna') return { badge: '♥', tooltip: 'Health route', color: new vscode.ThemeColor('testing.iconPassed') };
    return undefined;
  }
};


module.exports = { KynaProjectProvider, KynaRoutesProvider, projectDecorations };
