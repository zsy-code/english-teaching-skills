/** Package an authored HTML/GSAP composition with the fixed lesson player. */
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import '../assets/lesson-player/contract.js';
const base=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../assets/lesson-player');
const json=v=>JSON.stringify(v).replaceAll('<','\\u003c').replaceAll('\u2028','\\u2028').replaceAll('\u2029','\\u2029');
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const hash=b=>createHash('sha256').update(b).digest('hex');
export async function packageCourse({scriptFile,timingFile,htmlFile,timelineKey,outDir,contentHeight}){
  const scriptBytes=await fs.readFile(scriptFile), script=JSON.parse(scriptBytes);
  const timing=JSON.parse(await fs.readFile(timingFile,'utf8'));
  if(hash(scriptBytes)!==timing.scriptSha256)throw Error('脚本已改变，需重新生成配音时间表');
  const audio=await fs.readFile(path.resolve(path.dirname(timingFile),timing.audio));
  if(hash(audio)!==timing.audioSha256)throw Error('配音文件与时间表不一致');
  let html=await fs.readFile(htmlFile,'utf8');
  // Authored code is trusted local production output, never an arbitrary upload.
  for(const m of [...html.matchAll(/<script\s+src=["']([^"']+)["']\s*><\/script>/g)]){
    if(!/^[\w./-]+$/.test(m[1])||m[1].startsWith('/')||m[1].split('/').includes('..'))throw Error('仅内联作品目录内的脚本');
    const code=await fs.readFile(path.join(path.dirname(htmlFile),m[1]),'utf8');
    html=html.replace(m[0],()=>'<script>'+code.replaceAll('</script','<\\/script')+'</script>');
  }
  if(/<(?:script|link)\b[^>]*(?:src|href)=/i.test(html))throw Error('作品仍有未内联的脚本或样式资源');
  const course=globalThis.LexiPlayerContract.validate({version:1,id:script.groupId,title:script.title,canvas:script.videoSize,duration:timing.duration,audio:'audio/narration.wav',source:{type:'html-gsap',timelineKey,contentHeight:contentHeight??script.videoSize.height*950/1200},segments:timing.scenes,captions:timing.captions,interactions:timing.interactions.map(item=>{
    const q=item.interaction; const [lead,...lines]=q.prompt.split('\n').filter(Boolean);
    if(q.type!=='choice')throw Error('尚未支持的互动类型');
    return {id:item.id,time:item.time,title:'互动练习',heading:'试着用一用',sentence:lines.length?lines.join('　 '):lead,hint:lines.length?lead:undefined,options:q.options.map(o=>o.text),correct:q.options.findIndex(o=>o.id===q.answerId),explanation:q.feedback.correct,retry:q.feedback.incorrect,reviewTime:timing.scenes.find(s=>s.id===item.beatId).start};
  })});
  const [contract,runtime,template,styles]=await Promise.all(['contract.js','runtime.js','shell.html','player.css'].map(f=>fs.readFile(path.join(base,f),'utf8')));
  const bundle=contract+'\n'+runtime.replace('"__PLAYER_TEMPLATE__"',()=>JSON.stringify(template)).replace('"__PLAYER_STYLES__"',()=>JSON.stringify(styles));
  await fs.mkdir(path.join(outDir,'audio'),{recursive:true});
  await fs.writeFile(path.join(outDir,'audio/narration.wav'),audio);
  await fs.writeFile(path.join(outDir,'lesson-player.js'),bundle);
  await fs.writeFile(path.join(outDir,'player-registration.json'),JSON.stringify(course,null,2));
  await fs.writeFile(path.join(outDir,'index.html'),`<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${esc(course.title)}</title><style>html,body{margin:0;height:100%;overflow:hidden}#lesson-player{display:block;height:100dvh}</style><body><div id="lesson-player"></div><script id="course-registration" type="application/json">${json({course,compositionHtml:html})}</script><script src="lesson-player.js"></script><script>const registration=JSON.parse(document.getElementById('course-registration').textContent);LexiPlayer.register(document.getElementById('lesson-player'),registration.course,{compositionHtml:registration.compositionHtml}).catch(error=>console.error(error.message));</script></body></html>`);
  await fs.writeFile(path.join(outDir,'build.json'),JSON.stringify({scriptSha256:hash(scriptBytes),audioSha256:hash(audio),compositionSha256:hash(await fs.readFile(htmlFile)),playerSha256:hash(bundle),duration:course.duration},null,2));
  return course;
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
  const args=process.argv.slice(2), flags={};
  for(let i=0;i<args.length;i+=2){if(!args[i].startsWith('--')||!args[i+1])throw Error('参数应为 --名称 值');flags[args[i].slice(2)]=args[i+1];}
  for(const k of ['script','timing','html','timeline','out'])if(!flags[k])throw Error('缺少 --'+k);
  const data=await packageCourse({scriptFile:flags.script,timingFile:flags.timing,htmlFile:flags.html,timelineKey:flags.timeline,outDir:flags.out,contentHeight:flags['content-height']?Number(flags['content-height']):undefined});
  console.log(JSON.stringify({out:flags.out,duration:data.duration,interactions:data.interactions.length}));
}
