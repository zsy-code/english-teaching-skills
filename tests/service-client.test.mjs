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
