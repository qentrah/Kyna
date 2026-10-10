// Owns completion, symbols, hover, navigation, and language code lenses.
const vscode = require('vscode');
const path = require('path');
const fs = require('fs');
const { wordCompletions, namespaceMembers } = require('./language-catalog');
const { findProjectRoot } = require('./project-context');
const { resolveImportedDeclaration } = require('./import-navigation');
function declaredSymbols(text) {
  const symbols = [];
  const expression = /\b(class|intf|type|fn|func|var|const|let|set)\s+([A-Za-z_][A-Za-z0-9_]*)/g;
  for (const match of text.matchAll(expression)) {
    const kinds = {
      class: vscode.CompletionItemKind.Class,
      intf: vscode.CompletionItemKind.Interface,
      type: vscode.CompletionItemKind.Interface,
      fn: vscode.CompletionItemKind.Function,
      func: vscode.CompletionItemKind.Function,
      var: vscode.CompletionItemKind.Variable,
      let: vscode.CompletionItemKind.Variable,
      const: vscode.CompletionItemKind.Constant,
      set: vscode.CompletionItemKind.Constant
    };
    symbols.push([match[2], kinds[match[1]], `Declared ${match[1]}`]);
  }
  return symbols;
}

function completionItem(definition) {
  const [label, kind, detail, snippet] = definition;
  const item = new vscode.CompletionItem(label, kind);
  item.detail = detail;
  if (snippet) item.insertText = new vscode.SnippetString(snippet);
  return item;
}

async function importPathCompletions(document, position) {
  const before = document.lineAt(position.line).text.slice(0, position.character);
  if (!/\b(?:import\s+(?:type\s+)?|from\s+)"[^"]*$/.test(before)) return null;
  const files = await vscode.workspace.findFiles('**/*.{ky,kyna}', '**/{node_modules,build,build-*}/**', 300);
  return files.map(uri => {
    let relative = path.relative(path.dirname(document.fileName), uri.fsPath).replace(/\\/g, '/');
    if (!relative.startsWith('.')) relative = `./${relative}`;
    const item = new vscode.CompletionItem(relative, vscode.CompletionItemKind.File);
    item.insertText = relative;
    item.detail = 'Kyna module';
    return item;
  });
}

async function importedMemberCompletions(document, position) {
  const before = document.lineAt(position.line).text.slice(0, position.character);
  const receiver = before.match(/([A-Za-z_][A-Za-z0-9_]*)\.$/)?.[1];
  if (!receiver) return null;
  const source = document.getText();
  const escapedReceiver = receiver.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const serverBinding = new RegExp(
    `\\b(?:var|const|let|set)\\s+${escapedReceiver}(?:\\s*:[^=;]+)?\\s*=\\s*(?:http\\.server|[A-Za-z_][A-Za-z0-9_]*\\.createApp)\\s*\\(`
  );
  if (serverBinding.test(source))
    return ['get', 'post', 'put', 'patch', 'delete', 'use', 'listen'].map(name =>
      completionItem([name, vscode.CompletionItemKind.Method, `Kyna HTTP application method`])
    );
  if (namespaceMembers[receiver])
    return namespaceMembers[receiver].map(name => completionItem([
      name, vscode.CompletionItemKind.Method, `Kyna ${receiver} operation`
    ]));
  const responseBinding = new RegExp(
    `\\b(?:var|const|let|set)\\s+${escapedReceiver}(?:\\s*:[^=;]+)?\\s*=\\s*(?:fetch|http\\.fetch)\\s*\\(`
  );
  if (responseBinding.test(source))
    return ['ok', 'status', 'url', 'method', 'headers', 'text', 'json'].map(name =>
      completionItem([name, vscode.CompletionItemKind.Property, 'Kyna HTTP response member'])
    );
  const resultBinding = new RegExp(
    `\\b(?:var|const|let|set)\\s+${escapedReceiver}(?:\\s*:[^=;]+)?\\s*=\\s*(?:fetchResult|http\\.tryFetch)\\s*\\(`
  );
  if (resultBinding.test(source))
    return ['ok', 'response', 'error'].map(name =>
      completionItem([name, vscode.CompletionItemKind.Property, 'Kyna non-throwing HTTP result member'])
    );
  const declaration = source.match(new RegExp(`\\bimport\\s+"([^"]+)"\\s+as\\s+${escapedReceiver}\\s*;`))
    || source.match(new RegExp(`\\bimport\\s+(?:type\\s+)?\\*\\s+as\\s+${escapedReceiver}\\s+from\\s+"([^"]+)"\\s*;`));
  if (!declaration) return null;
  try {
    const uri = vscode.Uri.file(path.resolve(path.dirname(document.fileName), declaration[1]));
    const text = Buffer.from(await vscode.workspace.fs.readFile(uri)).toString('utf8');
    const exports = [];
    const expression = /\bexport\s+(?:public\s+)?(class|intf|type|fn|func|var|const|let|set)\s+([A-Za-z_][A-Za-z0-9_]*)/g;
    for (const match of text.matchAll(expression))
      exports.push(completionItem([match[2], match[1] === 'fn' || match[1] === 'func' ? vscode.CompletionItemKind.Function : vscode.CompletionItemKind.Field, `Exported ${match[1]} from ${declaration[1]}`]));
    return exports;
  } catch (_) {
    return [];
  }
}

const completionProvider = {
  async provideCompletionItems(document, position) {
    const paths = await importPathCompletions(document, position);
    if (paths) return paths;
    const members = await importedMemberCompletions(document, position);
    if (members) return members;
    return [...wordCompletions, ...declaredSymbols(document.getText())].map(completionItem);
  }
};

function declarationAt(document, name) {
  const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const expression = new RegExp(`\\b(?:class|intf|type|fn|func|var|const|let|set)\\s+${escaped}\\b`);
  for (let line = 0; line < document.lineCount; line += 1) {
    const match = document.lineAt(line).text.match(expression);
    if (match) {
      const column = document.lineAt(line).text.indexOf(name, match.index);
      return new vscode.Location(document.uri,
        new vscode.Position(line, Math.max(0, column)));
    }
  }
  return undefined;
}

const definitionProvider = {
  async provideDefinition(document, position) {
    const range = document.getWordRangeAtPosition(position);
    if (!range) return undefined;
    const name = document.getText(range);
    const local = declarationAt(document, name);

    const linePrefix = document.lineAt(position.line).text.slice(0, range.start.character);
    const receiver = linePrefix.match(/([A-Za-z_][A-Za-z0-9_]*)\.$/)?.[1];
    if (local && !receiver) return local;
    const imported = await resolveImportedDeclaration(document, name, receiver);
    return imported ? declarationAt(imported.document, imported.name) : undefined;
  }
};

const kynaKeywords = new Set(wordCompletions.map(([word]) => word));

function captureDocumentation(lines, index) {
  const docs = [];
  for (let cursor = index - 1; cursor >= 0; cursor -= 1) {
    const trimmed = lines[cursor].trim();
    if (trimmed === '') continue;
    const comment = trimmed.match(/^#\s?(.*)$/);
    if (!comment) break;
    docs.unshift(comment[1]);
  }
  return docs.join('\n\n');
}

function collectDeclarations(text) {
  const declarations = new Map();
  const lines = text.split('\n');
  const modifiers = '(?:export\\s+|public\\s+|private\\s+|protected\\s+|static\\s+|override\\s+|final\\s+|abstract\\s+)*';
  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index].trim();
    const declaration = line.match(
      new RegExp(`^${modifiers}(class|intf|type|fn|func|var|const|let|set)\\s+([A-Za-z_][A-Za-z0-9_]*)\\s*(.*)$`)
    );
    if (declaration) {
      const [, kind, name, rest] = declaration;
      let label, signature;
      if (kind === 'class' || kind === 'intf') {
        label = kind === 'class' ? 'class' : 'interface';
        const parent = rest.match(/extends\s+([A-Za-z_][A-Za-z0-9_]*)/);
        signature = `${kind} ${name}${parent ? ` extends ${parent[1]}` : ''}`;
      } else if (kind === 'fn' || kind === 'func') {
        label = 'function';
        const params = rest.match(/^\s*\(([^)]*)\)/);
        const tail = params ? rest.slice(params.index + params[0].length) : rest;
        const returns = tail.match(/^\s*:\s*([^;{]+)/);
        signature = `fn ${name}(${params ? params[1].trim() : ''})`
          + (returns ? ` → ${returns[1].trim()}` : '');
      } else {
        label = kind;
        const type = rest.match(/:\s*([^=;]+)/);
        signature = name + (type ? ` : ${type[1].trim()}` : '');
      }
      declarations.set(name, {
        label,
        signature,
        line: index + 1,
        doc: captureDocumentation(lines, index)
      });
      continue;
    }
    const field = line.match(
      new RegExp(`^${modifiers}([A-Za-z_][A-Za-z0-9_]*)\\s*:\\s*([^;={}]+)\\s*(=.*)?;`)
    );
    if (field && !kynaKeywords.has(field[1])) {
      const [, name, type] = field;
      declarations.set(name, {
        label: 'field',
        signature: `${name} : ${type.trim()}`,
        line: index + 1,
        doc: captureDocumentation(lines, index)
      });
      continue;
    }
    const method = line.match(
      new RegExp(`^${modifiers}([A-Za-z_][A-Za-z0-9_]*)\\s*\\(([^)]*)\\)\\s*(?::\\s*([^;{]+))?\\s*(?:;|\\{)`)
    );
    if (method && !kynaKeywords.has(method[1])) {
      const [, name, params, returns] = method;
      declarations.set(name, {
        label: name === 'init' ? 'constructor' : 'method',
        signature: `${name}(${params.trim()})` + (returns ? ` → ${returns.trim()}` : ''),
        line: index + 1,
        doc: captureDocumentation(lines, index)
      });
    }
  }
  return declarations;
}

const hoverDetails = new Map(wordCompletions.map(([word, , detail]) => [word, detail]));
const hoverProvider = {
  async provideHover(document, position) {
    const range = document.getWordRangeAtPosition(position);
    if (!range) return undefined;
    const word = document.getText(range);
    let fields = collectDeclarations(document.getText()).get(word);
    const prefix = document.lineAt(position.line).text.slice(0, range.start.character);
    const receiver = prefix.match(/([A-Za-z_][A-Za-z0-9_]*)\.$/)?.[1];
    if (receiver) fields = undefined;
    if (receiver || !fields) {
      const imported = await resolveImportedDeclaration(document, word, receiver);
      if (imported) fields = collectDeclarations(imported.document.getText()).get(imported.name);
    }
    if (fields) {
      const markdown = new vscode.MarkdownString();
      markdown.appendMarkdown(`**\`${fields.signature}\`** — *${fields.label}*\n\n`);
      markdown.appendMarkdown(`**declared at line ${fields.line}**\n\n`);
      if (fields.doc) markdown.appendMarkdown(`${fields.doc}\n\n`);
      return new vscode.Hover(markdown, range);
    }
    const detail = hoverDetails.get(word);
    if (detail) return new vscode.Hover(new vscode.MarkdownString(`**${word}** — ${detail}`), range);
    return undefined;
  }
};

const symbolProvider = {
  provideDocumentSymbols(document) {
    const symbols = [];
    const expression = /\b(class|intf|type|fn|func|var|const|let|set)\s+([A-Za-z_][A-Za-z0-9_]*)/g;
    for (let line = 0; line < document.lineCount; line += 1) {
      const text = document.lineAt(line).text;
      for (const match of text.matchAll(expression)) {
        const kinds = {
          class: vscode.SymbolKind.Class,
          intf: vscode.SymbolKind.Interface,
          type: vscode.SymbolKind.Interface,
          fn: vscode.SymbolKind.Function,
          func: vscode.SymbolKind.Function,
          var: vscode.SymbolKind.Variable,
          let: vscode.SymbolKind.Variable,
          const: vscode.SymbolKind.Constant,
          set: vscode.SymbolKind.Constant
        };
        const start = new vscode.Position(line, match.index);
        const end = new vscode.Position(line, match.index + match[0].length);
        symbols.push(new vscode.DocumentSymbol(match[2], match[1], kinds[match[1]],
          new vscode.Range(start, end), new vscode.Range(start, end)));
      }
    }
    return symbols;
  }
};

const codeLensProvider = {
  provideCodeLenses(document) {
    const range = new vscode.Range(0, 0, 0, 0);
    const lenses = [
      new vscode.CodeLens(range, { command: 'kyna.runFile', title: '$(play) Run Kyna' }),
      new vscode.CodeLens(range, { command: 'kyna.checkFile', title: '$(check) Check Kyna' })
    ];
    if (findProjectRoot(document.fileName))
      lenses.push(new vscode.CodeLens(range,
        { command: 'kyna.devProject', title: '$(sync) Watch Project & Restart', arguments: [document.uri] }));
    return lenses;
  }
};

const manifestCodeLensProvider = {
  provideCodeLenses(document) {
    const range = new vscode.Range(0, 0, 0, 0);
    const argument = [document.uri];
    return [
      new vscode.CodeLens(range, { command: 'kyna.runProject', title: '$(play) Run Project · port from kyna.toml', arguments: argument }),
      new vscode.CodeLens(range, { command: 'kyna.devProject', title: '$(sync) Watch & Restart', arguments: argument }),
      new vscode.CodeLens(range, { command: 'kyna.installDependencies', title: '$(cloud-download) Install Dependencies', arguments: argument }),
      new vscode.CodeLens(range, { command: 'kyna.generateRoute', title: '$(git-branch-create) Generate Route', arguments: argument }),
      new vscode.CodeLens(range, { command: 'kyna.configureProject', title: '$(settings-gear) Configure Host & Port', arguments: argument })
    ];
  }
};

const manifestCompletionProvider = {
  provideCompletionItems() {
    const definitions = [
      ['project', '[project]\nname = "${1:app}"\nversion = "${2:0.1.0}"\nentry = "${3:src/main.kyna}"\ntemplate = "${4:backend}"'],
      ['server', '[server]\nhost = "${1:127.0.0.1}"\nport = ${2:3000}'],
      ['scripts', '[scripts]\ncheck = "ky check"\ntest = "ky check tests"'],
      ['dependency-git', '${1:name} = { git = "${2:https://github.com/example/project.git}", rev = "${3:commit}" }'],
      ['dependency-path', '${1:name} = { path = "${2:../shared}" }']
    ];
    return definitions.map(([label, snippet]) => {
      const item = new vscode.CompletionItem(label, vscode.CompletionItemKind.Snippet);
      item.insertText = new vscode.SnippetString(snippet);
      item.detail = 'Kyna manifest block';
      return item;
    });
  }
};


module.exports = { completionProvider, definitionProvider, hoverProvider, symbolProvider, codeLensProvider, manifestCodeLensProvider, manifestCompletionProvider };
