// Atomically replaces a complete verified runtime payload, retaining dependencies.
'use strict';
const fs = require('node:fs');
const path = require('node:path');
function stagePayload(extracted, vendor, platform) {
  const binary = path.join('bin', platform === 'win32' ? 'ky.exe' : 'ky');
  if (!fs.statSync(path.join(extracted,binary), {throwIfNoEntry:false})?.isFile())
    throw new Error('The verified Kyna archive does not contain bin/ky.');
  const pending = vendor+'.pending';
  const previous = vendor+'.previous';
  fs.rmSync(pending,{force:true,recursive:true});
  fs.mkdirSync(pending,{recursive:true});
  try {
    fs.cpSync(extracted,pending,{recursive:true});
    if (platform !== 'win32') fs.chmodSync(path.join(pending,binary),0o755);
    fs.rmSync(previous,{force:true,recursive:true});
    const hadPrevious=fs.existsSync(vendor);
    if(hadPrevious) fs.renameSync(vendor,previous);
    try { fs.renameSync(pending,vendor); }
    catch(error) { if(hadPrevious) fs.renameSync(previous,vendor); throw error; }
    fs.rmSync(previous,{force:true,recursive:true});
  } finally { fs.rmSync(pending,{force:true,recursive:true}); }
}
module.exports={stagePayload};
