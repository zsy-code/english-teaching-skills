import test from 'node:test';
import assert from 'node:assert/strict';
import {createClient,ServiceError} from '../skills/vocabulary-lesson/scripts/service-client.mjs';
const connection={baseUrl:'http://127.0.0.1:4174/api/agent/runs/test',key:'test-task-key'};
const wav=Buffer.alloc(48);wav.write('RIFF');wav.write('WAVE',8);
test('task endpoints share auth, do not follow redirects, return real audio bytes',async()=>{
 const calls=[];const client=createClient(connection,async(url,init)=>{calls.push({url,init});return url.endsWith('/tts')?new Response(wav,{headers:{'content-type':'audio/wav'}}):Response.json({ok:true})});
 await client.capabilities();await client.progress();await client.event({eventId:'e1'});assert.deepEqual(await client.tts({text:'hello'}),wav);
 assert.equal(calls.length,4);for(const c of calls){assert.equal(c.init.headers.Authorization,'Bearer test-task-key');assert.equal(c.init.redirect,'error')}
 assert.equal(calls[3].init.body,'{"text":"hello"}');
});
test('remote plaintext, embedded credentials and invalid connections are rejected before fetch',()=>{
 for(const baseUrl of ['http://remote.example','https://user:pass@example.com','https://example.com/?key=x','file:///tmp/service'])assert.throws(()=>createClient({...connection,baseUrl}),ServiceError);
 assert.throws(()=>createClient({...connection,key:'a\nb'}),ServiceError);
});
test('HTTP errors retain status but never leak provider response or connection credentials',async()=>{
 const c=createClient(connection,async()=>new Response('secret-vendor-body',{status:503}));
 await assert.rejects(c.tts({}),e=>e.status===503&&!e.message.includes('secret-vendor-body')&&!e.message.includes(connection.key));
 const failed=createClient(connection,async()=>{throw Error('secret-network-url')});await assert.rejects(failed.capabilities(),e=>!e.message.includes('secret-network-url'));
});
test('JSON error body and corrupt audio cannot become successful WAV files',async()=>{
 for(const [body,type] of [['{"error":"failed"}','application/json'],['not a wav','audio/wav']]){
  const c=createClient(connection,async()=>new Response(body,{headers:{'content-type':type}}));await assert.rejects(c.tts({}),ServiceError);
 }
});

test('material, binary delivery and reference download use scoped auth without serializing ZIP',async()=>{
 const calls=[],zip=Buffer.from('ZIP'),ref=Buffer.from('reference');const c=createClient(connection,async(url,init)=>{calls.push({url,init});return url.includes('/references/')?new Response(ref):Response.json({received:true})});
 await c.material({groupId:'g1',kind:'plan',version:1,content:'# plan'});assert.equal((await c.upload(zip)).received,true);assert.deepEqual(await c.reference('ref-1'),ref);
 assert.equal(calls[1].init.body,zip);assert.equal(calls[1].init.headers['Content-Type'],'application/octet-stream');
 for(const item of calls)assert.equal(item.init.headers.Authorization,'Bearer test-task-key');
 assert.throws(()=>c.reference('../secret'),ServiceError);
});

test('shared player validates arbitrary supported canvas and protects captions',async()=>{
 await import('../skills/vocabulary-lesson/assets/lesson-player/contract.js');
 const course={version:1,id:'test',title:'test',canvas:{width:1080,height:1920},duration:10,audio:'audio/test.wav',source:{type:'html-gsap',timelineKey:'test',contentHeight:1500}};
 assert.equal(globalThis.LexiPlayerContract.validate(course).canvas.height,1920);
 assert.throws(()=>globalThis.LexiPlayerContract.validate({...course,canvas:{width:0,height:1920}}));
 const scale=globalThis.LexiPlayerContract.contentScale({canvasHeight:1920,uiScale:.5625,contentHeight:1700,captionHeight:120,captionBottom:90,controlsVisible:true});assert.ok(scale*1700+120+90+18<=1920);
});
