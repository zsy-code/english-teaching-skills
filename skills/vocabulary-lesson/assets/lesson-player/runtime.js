/* Fixed player UI. Course authors register content; they do not own transport markup/styles. */
(function(global){
  const TEMPLATE="__PLAYER_TEMPLATE__";
  const STYLES="__PLAYER_STYLES__";
  const mounted=new WeakMap();
  async function register(host,course,{compositionHtml}={}){
    const m=global.LexiPlayerContract.validate(course);
    if(!(host instanceof HTMLElement))throw new Error('播放器需要一个 HTML 容器');
    if(typeof compositionHtml!=='string'||!compositionHtml.trim())throw new Error('缺少课程画面 HTML');
    mounted.get(host)?.();
    const root=host.shadowRoot||host.attachShadow({mode:'open'});
    root.innerHTML='<style>'+STYLES+'</style>'+TEMPLATE;
    const $=id=>root.getElementById(id),shell=$('canvas-shell'),transport=$('transport'),seek=$('seek');
    const quizzes=m.interactions,completed=new Set(),markerButtons=new Map(),tracks=[];
    const audio=new Audio(new URL(m.audio,document.baseURI).href);audio.preload='auto';
    const events=new AbortController(),cleanups=[];
    let disposed=false;
    function listen(target,event,fn){target.addEventListener(event,fn,{signal:events.signal});}
    function destroy(){
      if(disposed)return;disposed=true;events.abort();clearTimeout(hideTimer);cancelAnimationFrame(frame);
      audio.pause();audio.removeAttribute('src');audio.load();cleanups.forEach(fn=>fn());
      if(mounted.get(host)===destroy){mounted.delete(host);root.replaceChildren();}
    }
    mounted.set(host,destroy);
    shell.classList.toggle('safe-content',Boolean(m.source.contentHeight));
    $('course-title').textContent=m.title;seek.max=m.duration;
    // Generated CSS/DOM stays inside this frame; fixed controls and captions stay in the ShadowRoot.
    const iframe=document.createElement('iframe');iframe.title='课程讲解画面';iframe.tabIndex=-1;
    iframe.setAttribute('sandbox','allow-scripts');
    iframe.setAttribute('aria-hidden','true');iframe.style.visibility='hidden';
    $('play').disabled=true;$('transport-play').disabled=true;
  let activeQuiz=null,lastClock=0,visualTime=0,finishedFinalQuiz=false;
  let frame=0,wantsPlay=false,playTicket=0,hideTimer=0,dragging=false,resumeAfterSeek=false,keyboardMode=false,overBar=false;
    let renderer;
    try{
      renderer=await new Promise((resolve,reject)=>{
        const timeout=setTimeout(()=>reject(new Error('课程画面载入超时')),15000);
        const finish=()=>clearTimeout(timeout);cleanups.push(finish);
        events.signal.addEventListener('abort',()=>{finish();reject(new Error('播放器已卸载'));},{once:true});
        // The authored page has an opaque origin; it cannot read or redesign the host controls.
        const channel='lesson-'+crypto.randomUUID();
        const key=JSON.stringify(m.source.timelineKey).replaceAll('<','\\u003c');
        const bridge=`<script>(()=>{
          const channel=${JSON.stringify(channel)},tl=window.__timelines?.[${key}];
          if(!tl||typeof tl.seek!=='function'||typeof tl.render!=='function'){parent.postMessage({channel,error:'课程未注册约定的动画时间轴'},'*');return;}
          // A paused GSAP timeline at zero may not have applied its zero-time sets yet.
          // Backward rendering visits same-time sets in reverse order. Replay
          // time-zero children forward so the opening state matches first load.
          const renderStart=timeline=>{
            timeline.render(0,true,true);
            for(const child of timeline.getChildren?.(false,true,true)||[]){
              if(child.startTime()===0){
                if(typeof child.getChildren==='function')renderStart(child);
                else child.render(0,true,true);
              }
            }
          };
          const render=time=>{if(time===0)renderStart(tl);else tl.seek(time,true);};
          let pending=0,scheduled=0;
          window.addEventListener('message',e=>{
            if(e.source!==parent||e.data?.channel!==channel||!Number.isFinite(e.data.time))return;
            pending=e.data.time;
            if(!scheduled)scheduled=requestAnimationFrame(()=>{scheduled=0;render(pending);parent.postMessage({channel,renderedTime:pending},'*');});
          });
          render(0);parent.postMessage({channel,ready:true,renderedTime:0},'*');
        })();<\/script>`;
        listen(window,'message',event=>{
          if(event.source!==iframe.contentWindow||event.data?.channel!==channel)return;
          if(event.data.error){finish();reject(new Error(event.data.error));}
          if(Number.isFinite(event.data.renderedTime))$('course-visual').dataset.renderedTime=String(event.data.renderedTime);
          if(event.data.ready){iframe.style.visibility='visible';finish();resolve({seek:t=>iframe.contentWindow.postMessage({channel,time:t},'*')});}
        });
        iframe.srcdoc=compositionHtml.replace(/<\/body\s*>/i,()=>bridge+'</body>');$('course-visual').append(iframe);
      });
    }catch(e){if(!disposed)$('error').textContent=e.message;throw e;}
    if(disposed)throw new Error('播放器已卸载');
    $('play').disabled=false;$('transport-play').disabled=false;
  function fit(){const box=$('canvas-viewport');shell.style.transform=`translate(-50%,-50%) scale(${Math.min(box.clientWidth/1920,box.clientHeight/1200)})`;}
  const viewportObserver=new ResizeObserver(fit);viewportObserver.observe($('canvas-viewport'));cleanups.push(()=>viewportObserver.disconnect());fit();
  const fmt=t=>`${Math.floor(t/60)}:${String(Math.floor(t%60)).padStart(2,'0')}`;
  let reservedCaptionHeight=0;
  function measureCaptionSpace(){
    if(!m.source.contentHeight)return;
    const probe=$('player-caption').cloneNode();probe.removeAttribute('id');probe.hidden=false;
    probe.style.cssText='visibility:hidden!important;display:block!important;top:0;bottom:auto;transition:none';shell.append(probe);
    reservedCaptionHeight=0;
    for(const cue of m.captions){probe.textContent=cue.text;reservedCaptionHeight=Math.max(reservedCaptionHeight,probe.offsetHeight);}
    probe.remove();fitContent();
  }
  function fitContent(){
    if(!m.source.contentHeight)return;
    // Reserve the measured maximum once: caption gaps and scrubbing must not resize the lesson.
    const scale=global.LexiPlayerContract.contentScale({contentHeight:m.source.contentHeight,captionHeight:reservedCaptionHeight,captionBottom:160,controlsVisible:true});
    $('course-visual').style.transform=`scale(${scale})`;
  }
  measureCaptionSpace();document.fonts.ready.then(()=>{if(!disposed)measureCaptionSpace();});
  function setControls(visible){
    clearTimeout(hideTimer);
    visible=visible||Boolean(activeQuiz);
    shell.classList.toggle('controls-visible',visible);transport.inert=!visible;transport.setAttribute('aria-hidden',String(!visible));fitContent();
  }
  function activity(){
    setControls(true);
    if(!audio.paused&&!dragging&&!overBar&&!(keyboardMode&&transport.contains(root.activeElement))){
      hideTimer=setTimeout(()=>setControls(false),3500);
    }
  }
  function syncPlayButton(){
    const playing=!audio.paused,label=wantsPlay?'正在载入':playing?'暂停':'播放';
    shell.classList.toggle('is-playing',playing);
    for(const id of ['play','transport-play']){$(id).setAttribute('aria-label',label);$(id).setAttribute('aria-busy',String(wantsPlay));}
    $('transport-play').disabled=Boolean(activeQuiz&&!completed.has(activeQuiz.id));
    $('transport-play').title=$('transport-play').disabled?'答对后继续播放':'播放 / 暂停';
  }
  function paint(t){
    visualTime=Math.max(0,Math.min(t,m.duration));renderer.seek(visualTime);if(t>.05)shell.classList.add('has-started');
    const cue=m.captions.find(c=>t>=c.start&&t<c.end);$('player-caption').textContent=cue?.text||'';$('player-caption').hidden=!cue;fitContent();seek.value=t;paintTracks(t);
    $('time').textContent=fmt(t>=m.duration-.015?Math.ceil(m.duration):t)+' / '+fmt(Math.ceil(m.duration));
    seek.setAttribute('aria-valuetext',`${t.toFixed(1)} 秒，共 ${m.duration.toFixed(1)} 秒`);$('course-visual').dataset.playhead=t.toFixed(3);
  }
  function tick(){
    const t=audio.currentTime;
    const due=quizzes.find(q=>q.time>lastClock+.001&&q.time<=t+.001);
    if(due){showQuiz(due);return;}
    lastClock=t;paint(t);if(!audio.paused&&!audio.ended)frame=requestAnimationFrame(tick);
  }
  function pause({repaint=true}={}){wantsPlay=false;playTicket++;audio.pause();cancelAnimationFrame(frame);syncPlayButton();if(repaint&&!dragging&&!audio.seeking)paint(audio.currentTime);activity();}
  function hideQuiz(){activeQuiz=null;$('quiz').hidden=true;$('course-visual').inert=false;shell.classList.remove('quiz-active');updateMarkers();syncPlayButton();}
  function seekTo(t,{preferQuiz=true}={}){
    finishedFinalQuiz=false;
    const target=Math.max(0,Math.min(m.duration,t));
    // Numeric/keyboard seeks can land on a quiz timestamp; pointer seeks use the node's actual slot.
    const q=preferQuiz?quizzes.find(q=>Math.abs(q.time-target)<=.01):null;
    if(q){showQuiz(q,{duringSeek:dragging});return false;}
    hideQuiz();audio.currentTime=target;lastClock=target;paint(target);activity();return true;
  }
  function jump(t,{resume=false,preferQuiz=true}={}){pause({repaint:false});if(seekTo(t,{preferQuiz})&&resume)play();}
  async function play(){
    finishedFinalQuiz=false;
    if(wantsPlay||!audio.paused){pause();return}
    hideQuiz();if(audio.ended||audio.currentTime>=m.duration-.05){audio.currentTime=0;lastClock=0;}
    const ticket=++playTicket;wantsPlay=true;syncPlayButton();$('error').textContent='';
    try{await audio.play();if(ticket!==playTicket)return;wantsPlay=false;syncPlayButton();cancelAnimationFrame(frame);tick();activity();}
    catch(e){if(ticket!==playTicket)return;wantsPlay=false;syncPlayButton();activity();$('error').textContent='音频暂时无法播放，请确认课程包里的配音文件完整，然后重试。';}
  }
  function updateMarkers(){
    quizzes.forEach((q,i)=>{const b=markerButtons.get(q.id);if(!b)return;
      const status=completed.has(q.id)?'已完成':'未作答';
      b.dataset.done=String(completed.has(q.id));b.setAttribute('aria-current',activeQuiz?.id===q.id?'step':'false');
      const label=`互动题 ${i+1} · ${fmt(q.time)} · ${q.title} · ${status}`;
      b.setAttribute('aria-label',label);b.querySelector('.marker-tooltip').textContent=label;
    });
  }
  function showQuiz(q,{duringSeek=false}={}){
    finishedFinalQuiz=false;
    if(duringSeek&&activeQuiz?.id===q.id)return;
    // While scrubbing, keep following the pointer through both quiz slots and video segments.
    if(!duringSeek){dragging=false;resumeAfterSeek=false;}
    pause({repaint:false});activeQuiz=q;audio.currentTime=q.time;lastClock=q.time;paint(q.time);
    $('quiz').hidden=false;$('course-visual').inert=true;shell.classList.add('quiz-active');
    $('quiz-number').textContent=`互动练习 ${quizzes.indexOf(q)+1} / ${quizzes.length}`;
    $('quiz-heading').textContent=q.heading;$('quiz-sentence').textContent=q.sentence||'';$('quiz-hint').textContent=q.hint||'';
    $('quiz-answers').replaceChildren();
    q.options.forEach((text,i)=>{const b=document.createElement('button'),letter=document.createElement('strong');
      letter.textContent=String.fromCharCode(65+i);b.append(letter,document.createTextNode(text));b.dataset.answer=i;
      if(completed.has(q.id)&&i===q.correct)b.className='correct';
      b.onclick=()=>answer(i);$('quiz-answers').append(b);
    });
    $('feedback').textContent=completed.has(q.id)?q.explanation:'选择一个答案，完成后继续。';
    $('quiz-continue').disabled=!completed.has(q.id);
    $('quiz-continue').textContent=completed.has(q.id)?(q.time>=m.duration?'完成练习':'继续播放'):'答对后继续';
    $('quiz-replay').hidden=q.time<m.duration;
    updateMarkers();syncPlayButton();activity();if(!duringSeek)$('quiz').focus();
  }
  function answer(value){
    const q=activeQuiz;if(!q)return;
    const correct=value===q.correct;if(correct)completed.add(q.id);
    for(const b of $('quiz-answers').children)b.className=Number(b.dataset.answer)===value?(correct?'correct':'wrong'):'';
    $('feedback').textContent=correct?q.explanation:q.retry;
    $('quiz-continue').disabled=!completed.has(q.id);
    $('quiz-continue').textContent=completed.has(q.id)?(q.time>=m.duration?'完成练习':'继续播放'):'答对后继续';
    updateMarkers();syncPlayButton();
  }
  // Quiz nodes occupy their own slots; each teaching segment has its own rounded bar.
  function addTrack(start,end){
    if(end<=start)return;
    const el=document.createElement('span'),bar=document.createElement('span'),fill=document.createElement('span');
    el.className='lesson-track';el.style.flexGrow=end-start;el.setAttribute('aria-hidden','true');
    bar.className='track-bar';fill.className='track-fill';bar.append(fill);el.append(bar);$('seek-layout').append(el);tracks.push({start,end,el,fill});
  }
  let segmentStart=0;
  quizzes.forEach(q=>{addTrack(segmentStart,q.time);segmentStart=q.time;
    const b=document.createElement('button'),dot=document.createElement('i'),tooltip=document.createElement('span');
    b.className='quiz-marker';dot.className='dot';dot.setAttribute('aria-hidden','true');tooltip.className='marker-tooltip';tooltip.setAttribute('aria-hidden','true');b.append(dot,tooltip);b.onclick=()=>showQuiz(q);$('seek-layout').append(b);markerButtons.set(q.id,b);
  });
  addTrack(segmentStart,m.duration);
  function paintTracks(t){
    for(const track of tracks)track.fill.style.width=`${Math.max(0,Math.min(1,(t-track.start)/(track.end-track.start)))*100}%`;
    // At a completed quiz boundary, continue at the start of the next segment.
    const track=tracks.find(x=>t>=x.start&&t<x.end)||tracks[tracks.length-1];
    if(track){const pct=Math.max(0,Math.min(1,(t-track.start)/(track.end-track.start)));$('seek-knob').style.left=`${track.el.offsetLeft+pct*track.el.clientWidth}px`;}
  }
  const trackObserver=new ResizeObserver(()=>paintTracks(visualTime));trackObserver.observe($('seek-layout'));cleanups.push(()=>trackObserver.disconnect());
  updateMarkers();
  $('play').onclick=play;$('transport-play').onclick=()=>{if(activeQuiz)$('quiz-continue').click();else play();};
  function scrubTo(clientX){
    // A quiz is an actual seek target, including quizzes already completed.
    for(const q of quizzes){const rect=markerButtons.get(q.id).getBoundingClientRect();
      if(clientX>=rect.left&&clientX<=rect.right){showQuiz(q,{duringSeek:true});return;}
    }
    // Outside quiz slots, locate the exact time within the nearest teaching segment.
    let nearest=null,distance=Infinity;
    for(const track of tracks){const rect=track.el.getBoundingClientRect(),x=Math.max(rect.left,Math.min(rect.right,clientX)),d=Math.abs(clientX-x);
      if(d<distance){distance=d;nearest={track,pct:rect.width?(x-rect.left)/rect.width:0};}
    }
    if(!nearest)return;
    seekTo(nearest.track.start+nearest.pct*(nearest.track.end-nearest.track.start),{preferQuiz:false});
  }
  listen(seek,'pointerdown',e=>{if(e.button!==0)return;e.preventDefault();seek.focus();seek.setPointerCapture(e.pointerId);dragging=true;resumeAfterSeek=!audio.paused||wantsPlay;pause();scrubTo(e.clientX);});
  listen(seek,'pointermove',e=>{if(dragging)scrubTo(e.clientX);});
  listen(seek,'input',()=>seekTo(Number(seek.value)));
  function finishSeek(){if(!dragging)return;dragging=false;const resume=resumeAfterSeek;resumeAfterSeek=false;if(activeQuiz){$('quiz').focus();activity();return;}if(resume)play();else activity();}
  listen(window,'pointerup',finishSeek);listen(window,'pointercancel',finishSeek);listen(window,'blur',()=>{if(dragging){dragging=false;resumeAfterSeek=false;pause();}});
  $('quiz-replay').onclick=()=>jump(0,{resume:true});
  $('back-to-story').onclick=()=>{if(activeQuiz)jump(activeQuiz.reviewTime??0,{resume:true});};
  $('quiz-continue').onclick=()=>{if(!activeQuiz||!completed.has(activeQuiz.id))return;const t=activeQuiz.time;if(t>=m.duration){pause();finishedFinalQuiz=true;hideQuiz();paint(m.duration);shell.focus();return;}jump(t,{resume:true,preferQuiz:false});};
  $('captions-toggle').onclick=()=>{const off=shell.classList.toggle('captions-off');$('captions-toggle').setAttribute('aria-pressed',String(!off));activity();};
  listen(shell,'pointerdown',()=>{keyboardMode=false;});
  listen(shell,'focusin',()=>{if(keyboardMode)activity();});
  listen(shell,'focusout',()=>{queueMicrotask(()=>{if(shell.classList.contains('controls-visible')&&!transport.contains(root.activeElement))activity();});});
  const bar=root.querySelector('.player-controls');listen(bar,'pointerenter',()=>{overBar=true;if(shell.classList.contains('controls-visible'))activity();});listen(bar,'pointerleave',()=>{overBar=false;if(shell.classList.contains('controls-visible'))activity();});
  listen(shell,'click',e=>{if(!$('quiz').hidden||e.target.closest('button,input,.player-controls'))return;if(shell.classList.contains('controls-visible'))setControls(false);else activity();});
  listen(shell,'dblclick',e=>{if(!$('quiz').hidden||e.target.closest('button,input,.player-controls'))return;play();activity();});
  listen(audio,'ended',()=>{if(activeQuiz||finishedFinalQuiz)return;pause();paint(m.duration);const q=quizzes.find(q=>q.time>=m.duration-.001);if(q)showQuiz(q);});
  listen(audio,'error',()=>{pause();$('error').textContent='配音文件读取失败。请保留完整课程包，并重新打开 index.html。';});
  listen(shell,'keydown',e=>{
    keyboardMode=true;if(!$('quiz').hidden)return;activity();
    if(e.target.closest('button,input,a,textarea,select,[contenteditable]')||e.repeat)return;
    if(e.code==='Space'){e.preventDefault();play();}else if(e.code==='ArrowRight'){e.preventDefault();jump(audio.currentTime+5,{resume:!audio.paused});}else if(e.code==='ArrowLeft'){e.preventDefault();jump(audio.currentTime-5,{resume:!audio.paused});}
  });
  listen(window,'pagehide',pause);paint(0);activity();
  const api={
    play:()=>audio.paused?play():Promise.resolve(),pause,
    seek:(time)=>jump(time),
    destroy,
    getState:()=>({time:visualTime,playing:!audio.paused,quizId:activeQuiz?.id||null,completed:[...completed]})
  };
  return api;

  }
  global.LexiPlayer=Object.freeze({version:'1.0.0',register});
})(globalThis);
