// Verifies npm installer platform, checksum, and download-origin contracts.

"use strict";

const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");

const { expectedChecksum, fileChecksum, verifyChecksum } = require("../scripts/checksum");
const { validateUrl } = require("../scripts/download");
const { releaseAsset } = require("../scripts/platform");

test("maps supported Node platforms to exact release assets", () => {
  assert.equal(releaseAsset("darwin", "arm64"), "kyna-darwin-arm64.tar.gz");
  assert.equal(releaseAsset("darwin", "x64"), "kyna-darwin-x86_64.tar.gz");
  assert.equal(releaseAsset("linux", "arm64"), "kyna-linux-arm64.tar.gz");
  assert.equal(releaseAsset("linux", "x64"), "kyna-linux-x86_64.tar.gz");
  assert.equal(releaseAsset("win32", "x64"), "kyna-windows-x86_64.zip");
  assert.throws(() => releaseAsset("win32", "arm64"), /does not publish/u);
});

test("selects only an exact checksum entry", () => {
  const digest = "a".repeat(64);
  const checksums = `${"b".repeat(64)}  other.tar.gz\n${digest} *kyna-linux-x86_64.tar.gz\n`;
  assert.equal(expectedChecksum(checksums, "kyna-linux-x86_64.tar.gz"), digest);
  assert.throws(() => expectedChecksum(checksums, "missing.tar.gz"), /missing/u);
});

test("hashes and rejects changed archive contents", () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "kyna-npm-test-"));
  const file = path.join(directory, "archive");
  try {
    fs.writeFileSync(file, "trusted archive");
    const digest = crypto.createHash("sha256").update("trusted archive").digest("hex");
    assert.equal(fileChecksum(file), digest);
    assert.doesNotThrow(() => verifyChecksum(file, digest));
    fs.writeFileSync(file, "changed archive");
    assert.throws(() => verifyChecksum(file, digest), /Checksum verification failed/u);
  } finally {
    fs.rmSync(directory, { force: true, recursive: true });
  }
});

test("accepts only the GitHub release download origins", () => {
  assert.equal(validateUrl("https://github.com/Up-to-code/Kyna").hostname, "github.com");
  assert.equal(
    validateUrl("https://release-assets.githubusercontent.com/file").hostname,
    "release-assets.githubusercontent.com",
  );
  assert.throws(() => validateUrl("http://github.com/Up-to-code/Kyna"), /untrusted/u);
  assert.throws(() => validateUrl("https://example.com/archive"), /untrusted/u);
});

test("prepared npm, CLI, and extension versions agree", () => {
  const root = path.resolve(__dirname, "../../..");
  const cmake = fs.readFileSync(path.join(root, "CMakeLists.txt"), "utf8");
  const version = cmake.match(/project\(kyna VERSION ([0-9.]+)/u)[1];
  assert.equal(require("../package.json").version.split("-")[0], version);
  assert.equal(JSON.parse(fs.readFileSync(path.join(root, "editors/vscode-kyna/package.json"))).version, version);
  assert.equal(require("../package-lock.json").version, require("../package.json").version);
});

test('verified payload staging retains libraries and licenses and rejects invalid replacement', () => {
  const {stagePayload}=require('../scripts/payload');
  const directory=fs.mkdtempSync(path.join(os.tmpdir(),'kyna-payload-'));
  const extracted=path.join(directory,'extracted'),vendor=path.join(directory,'vendor');
  try {
    for(const relative of ['bin/ky','lib/runtime/dependency.so','licenses/dependency.txt','share/kyna/templates/main.ky']) {
      const file=path.join(extracted,relative);fs.mkdirSync(path.dirname(file),{recursive:true});fs.writeFileSync(file,relative);
    }
    stagePayload(extracted,vendor,'linux');
    assert.equal(fs.readFileSync(path.join(vendor,'lib/runtime/dependency.so'),'utf8'),'lib/runtime/dependency.so');
    assert.ok(fs.statSync(path.join(vendor,'licenses/dependency.txt')).isFile());
    fs.unlinkSync(path.join(extracted,'bin/ky'));
    assert.throws(()=>stagePayload(extracted,vendor,'linux'),/does not contain/);
    assert.equal(fs.readFileSync(path.join(vendor,'bin/ky'),'utf8'),'bin/ky');
  } finally {fs.rmSync(directory,{recursive:true,force:true});}
});
