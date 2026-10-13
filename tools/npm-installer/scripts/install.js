// Installs the release matching this npm package after checksum verification.

"use strict";

const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

const { expectedChecksum, verifyChecksum } = require("./checksum");
const { downloadFile, downloadText } = require("./download");
const { extractArchive } = require("./extract");
const { releaseAsset } = require("./platform");
const { stagePayload } = require("./payload");
const packageMetadata = require("../package.json");

const REPOSITORY = "qentrah/Kyna";

async function install() {
  if (process.env.KYNA_NPM_SKIP_DOWNLOAD === "1") {
    return;
  }

  const asset = releaseAsset(process.platform, process.arch);
  const tag = `v${packageMetadata.version}`;
  const release = `https://github.com/${REPOSITORY}/releases/download/${tag}`;
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "kyna-npm-"));
  const archive = path.join(temporary, asset);
  const extracted = path.join(temporary, "payload");
  const vendor = path.join(__dirname, "..", "vendor");

  try {
    fs.mkdirSync(extracted);
    console.log(`Installing Kyna ${packageMetadata.version} for ${process.platform}-${process.arch}...`);
    const checksums = await downloadText(`${release}/SHA256SUMS`);
    await downloadFile(`${release}/${asset}`, archive);
    verifyChecksum(archive, expectedChecksum(checksums, asset));
    extractArchive(archive, extracted, process.platform);

    stagePayload(extracted, vendor, process.platform);
    console.log("Kyna installation complete. Run: ky --version");
  } finally {
    fs.rmSync(temporary, { force: true, recursive: true });
  }
}

if (require.main === module) {
  install().catch((error) => {
    console.error(`Kyna installation failed: ${error.message}`);
    process.exitCode = 1;
  });
}

module.exports = { install };
