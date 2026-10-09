// Adapt an existing local TTS provider. No keys, vendor endpoint, or project path here.
import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';

const args=process.argv.slice(2), opts={};
for(let i=0;i<args.length;i+=2)opts[args[i]]=args[i+1];
if(!opts['--request']||!opts['--provider-module']){
  console.error('Usage: node synthesize.mjs --request /path/audio-request.json --provider-module /path/provider.mjs');process.exit(1);
}
const requestPath=path.resolve(opts['--request']),out=path.dirname(requestPath);
const hash=b=>createHash('sha256').update(b).digest('hex');
const raw=await fs.readFile(requestPath),request=JSON.parse(raw);
if(!Array.isArray(request.lines)||!request.lines.length)throw Error('Empty audio request');
const seen=new Set();
for(const line of request.lines){
  if(!/^[A-Za-z0-9_-]+$/.test(line.id)||seen.has(line.id)||!['zh','en'].includes(line.lang)||typeof line.text!=='string'||!line.text.trim())throw Error('Invalid speech entry');
  seen.add(line.id);
}
const manifest={version:1,requestSha256:hash(raw),status:'running',completed:0,total:request.lines.length,lines:[]};
const save=async()=>{const tmp=path.join(out,'audio-manifest.json.tmp');await fs.writeFile(tmp,JSON.stringify(manifest,null,2));await fs.rename(tmp,path.join(out,'audio-manifest.json'))};
await fs.mkdir(path.join(out,'clips'),{recursive:true});await save();
const controller=new AbortController();
for(const event of ['SIGINT','SIGTERM'])process.on(event,()=>controller.abort());
let current=null;
try{
  const provider=await import(pathToFileURL(path.resolve(opts['--provider-module'])).href);
  if(typeof provider.synthesize!=='function')throw Error('Missing synthesize export');
  for(const line of request.lines){
    current=line.id;controller.signal.throwIfAborted();
    // The provider owns the voice/config-aware cache. Call it even on resume so a changed voice cannot reuse stale files.
    if(line.spokenText!==undefined&&(typeof line.spokenText!=='string'||!line.spokenText.trim()))throw Error('Invalid spoken text');
    const result=await provider.synthesize(line.spokenText??line.text,line.lang,controller.signal);
    const wav=await fs.readFile(result.file);
    if(wav.toString('ascii',0,4)!=='RIFF'||wav.toString('ascii',8,12)!=='WAVE')throw Error('Invalid WAV');
    const file='clips/'+line.id+'.wav',tmp=path.join(out,file+'.tmp');
    await fs.writeFile(tmp,wav);await fs.rename(tmp,path.join(out,file));
    manifest.lines.push({id:line.id,file,sha256:hash(wav)});manifest.completed++;
    await save();console.log(`配音 ${manifest.completed}/${manifest.total} · ${line.id}`);
  }
  manifest.status='complete';await save();
}catch(err){
  manifest.status=controller.signal.aborted?'paused':'failed';manifest.failedSpeechId=current;
  // Service bodies/errors may contain credentials; publish only status and the failed source ID.
  manifest.error=controller.signal.aborted?'执行已中止':'配音未完成；检查本地服务配置、权限与连接后重试';
  const http=String(err.message).match(/HTTP\s+(\d{3})/);if(http)manifest.httpStatus=Number(http[1]);
  await save();console.error(manifest.error+' · '+(current||'provider'));process.exitCode=1;
}
