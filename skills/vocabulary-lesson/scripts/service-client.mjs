// Task-scoped service client. Credentials only come from a local connection file.
import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';

export class ServiceError extends Error {
  constructor(code,status){super(`服务调用未完成：${code}${status?' HTTP '+status:''}`);this.code=code;this.status=status}
}
export function createClient(connection,fetcher=globalThis.fetch){
  let url;
  try{url=new URL(connection.baseUrl)}catch{throw new ServiceError('invalid_connection')}
  if(!['http:','https:'].includes(url.protocol)||url.username||url.password||url.search||url.hash||
    (url.protocol==='http:'&&!['127.0.0.1','localhost','[::1]'].includes(url.hostname))||
    typeof connection.key!=='string'||!connection.key||/[\r\n]/.test(connection.key))throw new ServiceError('invalid_connection');
  const base=url.href.replace(/\/$/,'');
  async function call(endpoint,body,signal,audio=false,binary=false){
    let response;
    try{response=await fetcher(base+'/'+endpoint,{method:body?'POST':'GET',redirect:'error',headers:{Authorization:'Bearer '+connection.key,...(body?{'Content-Type':binary?'application/octet-stream':'application/json'}:{})},body:body?(binary?body:JSON.stringify(body)):undefined,signal:AbortSignal.any([AbortSignal.timeout(audio||binary?150000:15000),...(signal?[signal]:[])])})}
    catch{throw new ServiceError(signal?.aborted?'cancelled':'connection_failed')}
    if(!response.ok){await response.body?.cancel();throw new ServiceError('request_failed',response.status)}
    try{
      if(!audio)return await response.json();
      if(audio!=='reference'&&!response.headers.get('content-type')?.startsWith('audio/wav'))throw new ServiceError('invalid_audio');
      const reader=response.body.getReader(),chunks=[];let size=0;
      while(true){const {done,value}=await reader.read();if(done)break;size+=value.length;if(size>(audio==='reference'?10:20)*1024*1024){await reader.cancel();throw new ServiceError('audio_too_large')}chunks.push(value)}
      const bytes=Buffer.concat(chunks);
      if(audio==='reference')return bytes;
      if(bytes.length<44||bytes.toString('ascii',0,4)!=='RIFF'||bytes.toString('ascii',8,12)!=='WAVE')throw new ServiceError('invalid_audio');
      return bytes;
    }catch(e){if(e instanceof ServiceError)throw e;throw new ServiceError('invalid_response')}
  }
  return {material:(data,signal)=>call('materials',data,signal),upload:(bytes,signal)=>call('delivery',bytes,signal,false,true),reference:(id,signal)=>{if(!/^[A-Za-z0-9_-]+$/.test(id))throw new ServiceError('invalid_reference');return call('references/'+id,null,signal,'reference')},capabilities:signal=>call('capabilities',null,signal),progress:signal=>call('progress',null,signal),event:(data,signal)=>call('events',data,signal),tts:(data,signal)=>call('tts',data,signal,true)};
}
export async function loadClient(file,fetcher){
  let connection;try{connection=JSON.parse(await fs.readFile(file,'utf8'))}catch{throw new ServiceError('invalid_connection_file')}
  return createClient(connection,fetcher);
}
async function main(){
  const [command,...args]=process.argv.slice(2),opts={};for(let i=0;i<args.length;i+=2)opts[args[i]]=args[i+1];
  if(!opts['--connection']||!['capabilities','progress','event','material','upload','reference'].includes(command))throw new ServiceError('usage: capabilities|progress|event|material|upload|reference --connection FILE [--data FILE | --id ID --out FILE]');
  const client=await loadClient(opts['--connection']);
  let result;
  if(command==='reference'){if(!opts['--out'])throw new ServiceError('missing_output');await fs.writeFile(opts['--out'],await client.reference(opts['--id']),{flag:'wx'});result={saved:true}}
  else if(command==='upload'){const info=await fs.stat(opts['--data']);if(info.size>100*1024*1024)throw new ServiceError('archive_too_large');result=await client.upload(await fs.readFile(opts['--data']))}
  else if(['event','material'].includes(command))result=await client[command](JSON.parse(await fs.readFile(opts['--data'],'utf8')));
  else result=await client[command]();
  console.log(JSON.stringify(result,null,2));
}
if(process.argv[1]&&import.meta.url===pathToFileURL(path.resolve(process.argv[1])).href)main().catch(e=>{console.error(e instanceof ServiceError?e.message:'服务指令失败，请核对输入文件');process.exitCode=1});
