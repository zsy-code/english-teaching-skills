/* Shared by the browser component and the server-side packager. All times use seconds. */
(function(global){
  function validate(course){
    const fail=message=>{throw new Error(`课程注册信息无效：${message}`);};
    const number=(v,label)=>{if(typeof v!=='number'||!Number.isFinite(v))fail(label);return v;};
    const text=(v,label)=>{if(typeof v!=='string'||!v.trim())fail(label);return v;};
    if(!course||course.version!==1)fail('version 必须为 1');
    text(course.id,'缺少课程 id');text(course.title,'缺少标题');
    if(number(course.duration,'时长必须是有限数字')<=0)fail('时长必须大于零');
    if(!course.canvas||!['width','height'].every(k=>Number.isInteger(course.canvas[k])&&course.canvas[k]>=320&&course.canvas[k]<=7680))fail('画布宽高必须为 320 到 7680 的整数');
    if(course.source?.type!=='html-gsap')fail('目前支持 html-gsap 画面');
    if(course.source.contentHeight!=null&&(number(course.source.contentHeight,'内容区域高度')<=0||course.source.contentHeight>course.canvas.height))fail('内容区域高度必须大于 0 且不超过画布高度');
    text(course.source.timelineKey,'缺少动画时间轴名称');
    const audio=text(course.audio,'缺少配音文件');
    if(!/^[\w./-]+$/.test(audio)||audio.startsWith('/')||audio.split('/').includes('..'))fail('配音必须为课程包内的相对路径');
    const interval=(v,label)=>{number(v.start,label);number(v.end,label);if(v.start<0||v.end<=v.start||v.end>course.duration+.001)fail(label);};
    const segments=course.segments??[],captions=course.captions??[],interactions=course.interactions??[];
    if(!Array.isArray(segments)||!Array.isArray(captions)||!Array.isArray(interactions))fail('片段、字幕、题目必须是数组');
    const ids=new Set();
    for(const s of segments){text(s.id,'片段 id');if(ids.has(s.id))fail('片段 id 重复');ids.add(s.id);interval(s,'片段时间范围');}
    for(const c of captions){text(c.text,'字幕文本');interval(c,'字幕时间范围');}
    ids.clear();
    for(const q of interactions){
      text(q.id,'题目 id');if(ids.has(q.id))fail('题目 id 重复');ids.add(q.id);
      number(q.time,'题目位置');if(q.time<0||q.time>course.duration+.001)fail('题目超出课程时长');
      for(const key of ['title','heading','explanation','retry'])text(q[key],`题目 ${key}`);
      if(!Array.isArray(q.options)||q.options.length<2||q.options.length>5)fail('选项数量');
      q.options.forEach(o=>text(o,'选项内容'));
      if(!Number.isInteger(q.correct)||q.correct<0||q.correct>=q.options.length)fail('正确答案序号');
      if(q.reviewTime!=null&&(number(q.reviewTime,'回看位置')<0||q.reviewTime>q.time))fail('回看位置必须在题目前');
    }
    return {...course,segments:[...segments],captions:[...captions].sort((a,b)=>a.start-b.start),interactions:[...interactions].sort((a,b)=>a.time-b.time)};
  }
  function contentScale({contentHeight,captionHeight=0,captionBottom=43.2,controlsVisible=false,canvasHeight=1200,uiScale=1}){
    const limit=Math.min(controlsVisible?canvasHeight-176*uiScale:canvasHeight,captionHeight?canvasHeight-captionBottom-captionHeight-32*uiScale:canvasHeight);
    return Math.min(1,Math.max(.1,limit/contentHeight));
  }
  global.LexiPlayerContract={validate,contentScale};
})(globalThis);
