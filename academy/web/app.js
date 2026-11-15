(function () {
  'use strict';
  const C=window.AcademyCore, data=JSON.parse(document.getElementById('knowledge-data').textContent);
  const lessons=data.lessons, lessonMap=new Map(lessons.map(x=>[x.id,x])), sourceMap=new Map(data.sources.map(x=>[x.id,x]));
  const KEY='fde-academy-progress-v1';
  let state={schemaVersion:1,kind:'fde-academy-progress',contentVersion:data.version,settings:{...C.DEFAULT_SETTINGS},records:{}};
  let storageError='',unreadableBackup='',searchText='',trackFilter='',levelFilter='',toastTimer;
  try {const saved=localStorage.getItem(KEY);if(saved){unreadableBackup=saved;state=C.validateBackup(JSON.parse(saved),lessons);unreadableBackup='';}}
  catch(e){storageError='学习记录未能读取，原数据未自动删除。请先导出当前记录或检查浏览器存储：'+e.message;}
  function E(tag,attrs,...children){
    const node=document.createElement(tag);
    for(const [key,value] of Object.entries(attrs||{})){
      if(key==='value'||key==='checked')continue;
      if(key==='className')node.className=value;
      else if(key.startsWith('on')&&typeof value==='function')node.addEventListener(key.slice(2),value);
      else if(value!==false&&value!==null&&value!==undefined)node.setAttribute(key,value===true?'':String(value));
    }
    for(const child of children.flat(Infinity)){if(child!==null&&child!==undefined&&child!==false)node.append(child instanceof Node?child:document.createTextNode(String(child)));}
    if(attrs&&'value'in attrs)node.value=attrs.value;
    if(attrs&&'checked'in attrs)node.checked=attrs.checked;
    return node;
  }
  const B=(text,fn,primary=false)=>E('button',{type:'button',className:primary?'primary':'',onclick:fn},text);
  const P=text=>E('p',{},text),list=(items,ordered=false)=>E(ordered?'ol':'ul',{},items.map(x=>E('li',{},x)));
  const link=(label,url,external=false)=>E('a',{href:url,...(external?{target:'_blank',rel:'noopener noreferrer'}:{})},label);
  const badge=level=>E('span',{className:'badge'+(level==='advanced'?' advanced':'')},level==='core'?'年底核心':'进阶实践');
  function paragraphs(text){return String(text).split(/\n\s*\n/).filter(Boolean).map(P);}
  function note(text,type=''){return E('div',{className:'callout '+type},text);}
  function toast(text){document.querySelector('.toast')?.remove();const node=E('div',{className:'toast',role:'status'},text);document.body.append(node);clearTimeout(toastTimer);toastTimer=setTimeout(()=>node.remove(),4200);}
  function persist(settingsChanged=false){
    state.contentVersion=data.version;
    if(unreadableBackup){toast('原记录格式无法读取。请先用顶部按钮导出原记录；当前新输入暂存在页面中。');return false;}
    try{
      const latest=localStorage.getItem(KEY);
      if(latest){const other=C.validateBackup(JSON.parse(latest),lessons);state.records=C.mergeRecords(other.records,state.records).records;if(!settingsChanged)state.settings=other.settings;}
      localStorage.setItem(KEY,JSON.stringify(state));storageError='';return true;
    }
    catch(e){storageError='浏览器保存失败；当前页面的记录仍在，请立即导出备份。';toast(storageError);return false;}
  }
  function record(id){return state.records[id]||C.blankRecord();}
  function updateRecord(id,changes){state.records[id]={...record(id),...changes,updatedAt:C.nextTimestamp(record(id).updatedAt)};persist();updateSideProgress();}
  function progress(){return {read:lessons.filter(x=>record(x.id).read).length,practiced:lessons.filter(x=>record(x.id).practiced).length,self:lessons.filter(x=>C.assess(x,record(x.id)).selfChecked).length};}
  function updateSideProgress(){const p=progress();const label=document.getElementById('side-count');if(label)label.textContent=p.read+' / '+lessons.length+' 已阅读 · '+p.self+' 课自验';const fill=document.getElementById('side-fill');if(fill)fill.style.width=(p.read/lessons.length*100)+'%';}
  function download(name,text,type='text/plain;charset=utf-8'){const url=URL.createObjectURL(new Blob([text],{type}));const a=E('a',{href:url,download:name});document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);}
  function exportProgress(){download('FDE学习记录-'+new Date().toISOString().slice(0,10)+'.json',JSON.stringify({...state,exportedAt:new Date().toISOString()},null,2),'application/json');toast('已导出学习记录；在另一设备的“笔记与备份”中导入。');}
  function go(route){if(location.hash.slice(1)===route){render();window.scrollTo(0,0);}else location.hash=route;}
  function route(){const hash=location.hash.slice(1);if(hash.startsWith('lesson:')&&lessonMap.has(hash.slice(7)))return {view:'lesson',id:hash.slice(7)};return {view:['sources','plan','projects','coverage','notes'].includes(hash)?hash:'courses'};}
  function heading(kicker,title,description){return E('div',{},E('div',{className:'eyebrow'},kicker),E('h1',{},title),E('p',{className:'lead'},description));}
  function shell(view){
    const names={courses:'学习工作台',lesson:'课程阅读',sources:'开源项目研究',plan:'核心与进阶计划',projects:'项目与交付模板',coverage:'原大纲逐项对照',notes:'笔记与备份'};
    const nav=[['courses','课程与练习'],['sources','开源项目研究'],['plan','学习计划'],['projects','项目与交付'],['coverage','大纲覆盖'],['notes','笔记与备份']];
    const sidebar=E('aside',{className:'sidebar',id:'sidebar'},E('div',{className:'brand-mark'},'ƒ'),E('div',{className:'brand'},'FDE 学习知识库',E('small',{},'BUILD · EXPLAIN · DELIVER')),E('nav',{'aria-label':'知识库导航'},nav.map(([id,name])=>E('button',{type:'button',className:'nav-button'+(view===id||(view==='lesson'&&id==='courses')?' active':''),onclick:()=>go(id)},name))),E('div',{className:'sidebar-footer'},E('div',{className:'side-label'},'LEARNING EVIDENCE'),E('div',{className:'side-meter'},E('span',{id:'side-fill'})),E('p',{id:'side-count'}),P('阅读、练习、自验分别记录。'),P('不自动认定已经掌握。'),E('hr'),link('FDE 知识库项目','https://github.com/23dfg-df/FDE-',true),E('br'),link('DocLens 文档解析','https://github.com/23dfg-df/fde2',true)));
    const top=E('header',{className:'topbar'},E('div',{},E('button',{className:'menu-toggle',type:'button','aria-label':'展开导航','aria-expanded':'false',onclick:e=>{const show=sidebar.classList.toggle('open');e.currentTarget.setAttribute('aria-expanded',String(show));}},'☰'),' ',E('strong',{},names[view])),E('div',{className:'topbar-actions'},E('span',{className:'mode-badge'},'离线可用 · 无需登录'),B('导出记录',exportProgress),B('打印本页',()=>window.print())));
    const main=E('main',{className:'content',id:'main',tabindex:'-1'});
    const recovery=storageError?note(storageError,'warn storage-warning'):null;
    if(unreadableBackup)recovery.append(E('br'),B('导出原记录并允许保存新记录',()=>{download('FDE原记录-恢复备份.json',unreadableBackup,'application/json');unreadableBackup='';try{localStorage.removeItem(KEY);}catch(e){}persist();render();}));
    const workspace=E('div',{className:'workspace'},top,recovery,main);
    document.getElementById('app').replaceChildren(E('div',{className:'layout'},sidebar,workspace));updateSideProgress();return main;
  }
  function footer(){return E('footer',{className:'footer'},E('span',{},'课程版本 '+data.version+' · 官方资料核对 '+data.checkedAt),E('span',{},'原创中文导读 · 开源项目按原许可使用 · 学习记录仅存当前浏览器'));}
  function renderCourses(main){
    const p=progress(),next=lessons.find(x=>x.level==='core'&&!C.assess(x,record(x.id)).selfChecked)||lessons.find(x=>!record(x.id).read)||lessons[0];
    main.append(E('section',{className:'hero'},E('div',{},heading('YOUR FIELD ENGINEERING PLAYBOOK','从写出代码，到完成交付','把计算机基础、AI 应用、云平台和客户交付串起来。每课先理解一个问题，再完成一个可验证的任务，留下你自己的运行与解释证据。'),E('div',{className:'hero-actions'},B('继续学习 · '+next.id.toUpperCase(),()=>go('lesson:'+next.id),true),B('查看年底与进阶安排',()=>go('plan')))),E('div',{className:'hero-aside'},E('div',{className:'eyebrow'},'CORE + PRACTICE'),E('strong',{},lessons.length+' 节'),P('18 节核心 · 18 节进阶'),P('工程 / AI / 交付三条主线'),P('2026 年底 → 2027 年前三个月'))));
    main.append(E('div',{className:'metrics'},[['110','原纲知识点映射'],[String(data.sources.filter(s=>s.kind==='repository'||s.kind==='course').length),'已研究开源项目 / 课程'],[String(p.read),'已阅读课程'],[String(p.self),'满足本地自验条件']].map(([v,t])=>E('div',{className:'metric'},E('b',{},v),E('span',{},t)))));
    main.append(note('本知识库提供完整的学习路线与入门到进阶教程；它不把大纲覆盖当作已经精通。示例、模拟实验和真实模型测量会明确区分。外部原始资料需要联网，课程正文和自测可以离线使用。'));
    const search=E('input',{type:'search',placeholder:'搜索概念、故障或任务，例如：事务、DNS、幂等、验收…',className:'search',value:searchText,'aria-label':'搜索全部课程'});
    const track=E('select',{'aria-label':'课程主线',value:trackFilter},E('option',{value:''},'全部主线'),data.tracks.map(t=>E('option',{value:t.id},t.title)));
    const level=E('select',{'aria-label':'学习阶段',value:levelFilter},E('option',{value:''},'核心 + 进阶'),E('option',{value:'core'},'年底核心'),E('option',{value:'advanced'},'后续进阶'));
    const count=E('div',{className:'results-count',role:'status'}),grid=E('div',{className:'course-grid'});
    function draw(){const filtered=C.filterLessons(lessons,searchText,trackFilter,levelFilter);count.textContent='找到 '+filtered.length+' 节课程 · 时间包含阅读、练习、排障与记录，是计划预算';grid.replaceChildren(...filtered.map(l=>{
      const r=record(l.id),a=C.assess(l,r),trackName=data.tracks.find(t=>t.id===l.track).title;
      return E('button',{type:'button',className:'course-card',onclick:()=>go('lesson:'+l.id)},E('div',{className:'card-top'},E('span',{className:'course-id'},l.id.toUpperCase()),badge(l.level)),E('h3',{},l.title),P(l.summary),E('div',{className:'card-bottom'},E('span',{},trackName+' · '+l.hours+' 小时'),E('span',{},a.selfChecked?'本课自验已通过':r.practiced?'已练习 · 待自验':r.read?'已读 · 待练习':'尚未开始')));
    }));if(!filtered.length)grid.append(E('div',{className:'empty'},'没有匹配课程。试试更短的关键词或清除筛选。'));}
    search.addEventListener('input',()=>{searchText=search.value;draw();});track.addEventListener('change',()=>{trackFilter=track.value;draw();});level.addEventListener('change',()=>{levelFilter=level.value;draw();});
    main.append(E('div',{className:'toolbar'},search,track,level),count,grid);draw();
  }
  function section(id,title,...content){return E('section',{className:'lesson-section',id},E('h2',{},title),...content);}
  function renderLesson(main,id){
    const l=lessonMap.get(id),article=E('article',{className:'lesson'}),r=record(id);
    article.append(E('header',{className:'lesson-header'},E('a',{href:'#courses',className:'back-link'},'← 返回全部课程'),E('div',{className:'lesson-meta'},E('span',{},l.id.toUpperCase()),badge(l.level),E('span',{},l.hours+' 小时 · 包含练习和排障')),E('h1',{},l.title),P(l.summary),l.prerequisites.length?E('div',{className:'small'},'建议先完成：',l.prerequisites.map(pid=>[link(lessonMap.get(pid).title,'#lesson:'+pid),'　'])):null));
    const items=[['outcomes','本课目标'],...l.sections.map((s,i)=>['part-'+i,s.title]),['example','运行与观察'],['exercise','动手练习'],['quiz','自测'],['evidence','笔记与证据'],['sources','继续阅读']];
    const toc=E('aside',{className:'toc','aria-label':'本课目录'},E('h3',{},'本课导航'),items.map(([anchor,title])=>E('a',{href:'#'+anchor,onclick:e=>{e.preventDefault();document.getElementById(anchor)?.scrollIntoView({behavior:'smooth',block:'start'});}},title)));
    article.append(section('outcomes','这一课要能做到',list(l.outcomes)));
    l.sections.forEach((s,i)=>article.append(section('part-'+i,s.title,...paragraphs(s.body))));
    const code=E('pre',{},E('code',{},l.example.code));
    article.append(section('example',l.example.title,E('div',{className:'code-header'},E('span',{},l.example.language.toUpperCase()),B('复制代码',async()=>{try{await navigator.clipboard.writeText(l.example.code);toast('代码已复制。请按本课环境要求运行。');}catch(e){const range=document.createRange();range.selectNodeContents(code);const sel=window.getSelection();sel.removeAllRanges();sel.addRange(range);toast('已选中代码，请使用系统复制快捷键。');}})),code,...paragraphs(l.example.explanation),l.lab?note('配套可运行实验：'+l.lab+'。请下载完整包，在解压目录运行；网页自身不会执行 Python 或连接服务器。'):null));
    article.append(section('exercise','先动手，再看参考',P(l.exercise.task),list(l.exercise.steps,true),E('details',{},E('summary',{},'遇到困难：逐步提示'),list(l.exercise.hints)),E('details',{},E('summary',{},'我已尝试或需要帮助：展开参考解释'),...paragraphs(l.exercise.solution)),E('h3',{},'验收时检查什么'),list(l.exercise.acceptance),note('需要保存：'+l.exercise.deliverable),E('h3',{},'失败时从哪里查起'),l.pitfalls.map(p=>E('div',{className:'pitfall'},E('b',{},p.symptom),P('可能原因：'+p.cause),P('下一步检查：'+p.check)))));
    const quiz=section('quiz','检查你的理解',P('先选择，再提交。答对题目只是局部自测，还需要自己的练习和解释。'));
    const answers=[...r.quizAnswers],feedbackBoxes=[];
    l.quiz.forEach((q,i)=>{const box=E('div',{});feedbackBoxes.push(box);quiz.append(E('fieldset',{className:'quiz-item',style:'border-left:0;border-right:0;border-top:0;min-width:0;padding-left:0;padding-right:0'},E('legend',{},(i+1)+'. '+q.question),q.options.map((option,j)=>E('label',{className:'quiz-option'},E('input',{type:'radio',name:'quiz-'+id+'-'+i,value:j,checked:answers[i]===j,onchange:()=>{answers[i]=j;updateRecord(id,{quizAnswers:answers,quizChecked:false});feedbackBoxes.forEach(b=>b.replaceChildren());updateEvidenceStatus();}}),E('span',{},option))),box));});
    function quizFeedback(){l.quiz.forEach((q,i)=>feedbackBoxes[i].replaceChildren(E('div',{className:'feedback'+(answers[i]===q.answer?'':' incorrect')},(answers[i]===q.answer?'回答正确。':'再检查一下。')+' '+q.explanation)));}
    quiz.append(B('提交自测',()=>{if(l.quiz.some((_,i)=>!Number.isInteger(answers[i]))){toast('请先回答本课的每一道题。');return;}updateRecord(id,{quizAnswers:answers,quizChecked:true});quizFeedback();updateEvidenceStatus();},true));
    if(r.quizChecked)quizFeedback();article.append(quiz);
    const status=E('div',{className:'save-status',role:'status'});
    function updateEvidenceStatus(){const a=C.assess(l,record(id));status.textContent=a.selfChecked?'本课自验条件已满足。此状态由你的记录与答案计算，不代表第三方已验证掌握。':'阅读、亲自练习、两类至少20字的证据和自测全部正确后，标记为“本课自验”。';}
    const evidence=section('evidence','把实现与掌握分开记录',note('记录保存在此浏览器，不自动上传或跨设备同步。请勿在笔记中记录密码、令牌或敏感业务原文。'));
    for(const [key,label] of [['read','我已阅读并理解本课讲解'],['practiced','我已亲自完成本课练习']])evidence.append(E('label',{className:'check-field'},E('input',{type:'checkbox',checked:r[key],onchange:e=>{updateRecord(id,{[key]:e.target.checked});updateEvidenceStatus();}}),label));
    for(const [key,label,placeholder] of [['implementationEvidence','实现证据：程序实际做到了什么','记录命令、输入、预期与实际结果；失败也应保留。'],['learningEvidence','学习掌握证据：你能解释和独立重做什么','用自己的话说明原因、边界和排障过程。复制参考答案不等于独立解释。'],['note','疑问与复习笔记','记下尚未理解的概念和下次要验证的问题。']]){
      evidence.append(E('label',{className:'field'},E('span',{},label),E('textarea',{value:r[key],placeholder,maxlength:20000,oninput:e=>{updateRecord(id,{[key]:e.target.value});updateEvidenceStatus();}})));
    }
    evidence.append(status,E('p',{className:'small'},'输入时自动保存；阅读状态与本课自验分开统计。'));updateEvidenceStatus();article.append(evidence);
    article.append(section('sources','这一课参考了什么',E('ul',{className:'source-list'},l.sources.map(sid=>{const s=sourceMap.get(sid);return E('li',{},link(s.title,s.url,true),E('small',{},s.use),E('small',{},'建议阅读：'+s.reading));}))));
    const index=lessons.findIndex(x=>x.id===id),previous=lessons[index-1],next=lessons[index+1];
    article.append(E('div',{className:'lesson-next'},previous?B('← '+previous.title,()=>go('lesson:'+previous.id)):E('span',{}),next?B(next.title+' →',()=>go('lesson:'+next.id),true):B('查看项目验收',()=>go('projects'),true)));
    main.append(E('div',{className:'lesson-layout'},article,toc));
  }
  function renderSources(main){
    main.append(heading('STUDY THE SYSTEM, THEN REPRODUCE A SLICE','开源项目研究与阅读地图','每个项目都说明用来学什么、从哪里读起、只复现哪一小块，以及不能据此声称什么。优先查看固定版本与实际环境，避免照抄最新主分支破坏现有部署。'),note('这是官方资料研究与课程映射，不代表已经部署过所有项目。教程为原创讲解；上游源码、模型权重和课程内容分别适用原许可。'));
    const search=E('input',{type:'search',className:'search',placeholder:'搜索项目、技术或复现目标…','aria-label':'搜索参考项目'}),listBox=E('div',{}),count=E('p',{className:'results-count',role:'status'});
    function draw(){const q=search.value.toLocaleLowerCase();const unique=[...new Map(data.sources.map(s=>[s.url,s])).values()].filter(s=>[s.title,s.use,s.reading,s.reproduction].join(' ').toLocaleLowerCase().includes(q));count.textContent=unique.length+' 个来源 · 核对日期 '+data.checkedAt;listBox.replaceChildren(...unique.map(s=>E('article',{className:'panel source-card'},E('div',{className:'card-top'},E('span',{className:'course-id'},s.kind==='repository'?'开源项目':s.kind==='course'?'公开课程':'官方文档'),E('span',{className:'small'},s.checked)),E('h3',{},link(s.title,s.url,true)),P(s.use),E('dl',{},E('dt',{},'先读哪里'),E('dd',{},s.reading),E('dt',{},'复现到什么程度'),E('dd',{},s.reproduction),E('dt',{},'边界与环境要求'),E('dd',{},s.limits),E('dt',{},'许可记录'),E('dd',{},s.license)))));}
    search.addEventListener('input',draw);main.append(E('div',{className:'toolbar',style:'grid-template-columns:1fr'},search),count,listBox);draw();
  }
  function table(headers,rows){return E('div',{className:'table-scroll'},E('table',{className:'data-table'},E('thead',{},E('tr',{},headers.map(h=>E('th',{scope:'col'},h)))),E('tbody',{},rows.map(row=>E('tr',{},row.map(cell=>E('td',{},cell)))))));}
  function renderPlan(main){
    main.append(heading('CORE BY YEAR END · THREE MONTHS OF PRACTICE','按可用时间安排，不把大纲压成承诺','默认从2026年11月16日开始，12月15日前每天2小时，此后每天4小时；年底完成核心路线，之后三个月用于进阶、项目与复盘。修改日期只改变计划，不改变学习证据。'));
    const form=E('form',{className:'panel'}),fields={};
    const labels=[['startDate','核心起始日期','date'],['deadline','核心目标日期','date'],['accelerationDate','每天4小时的开始日期','date'],['dailyHours','加速前每天小时数','number'],['acceleratedHours','加速后每天小时数','number']];
    form.append(E('div',{className:'form-grid'},labels.map(([key,label,type])=>{const input=E('input',{type,value:state.settings[key],required:true,...(type==='number'?{min:0,max:12,step:.5}:{})});fields[key]=input;return E('label',{className:'field'},E('span',{},label),input);})),E('div',{className:'hero-actions'},E('button',{type:'submit',className:'primary'},'保存并重新排期')));
    const results=E('div',{});function draw(){const p=C.schedule(lessons,state.settings);results.replaceChildren(E('div',{className:'metrics'},[[p.days,'可安排天数'],[p.capacity+' h','可用学习预算'],[p.required+' h','108小时核心 + 18小时复盘'],[Math.max(0,p.capacity-p.required)+' h','剩余缓冲']].map(([n,t])=>E('div',{className:'metric'},E('b',{},n),E('span',{},t)))));if(p.shortfall)results.append(note('当前计划比核心路线少 '+p.shortfall+' 小时。请延长目标日期或缩小任务，不把未排完课程标成按时完成。','warn'));results.append(table(['任务','预算','计划日期','安排状态'],p.allocations.map(a=>[a.id==='core-review'?a.title:link(a.id.toUpperCase()+' '+a.title,'#lesson:'+a.id),a.hours+' h',a.start?(a.start+' → '+a.end):'尚无可用时段',a.complete?'已分配学习时段':'尚缺 '+(a.hours-a.allocated)+' h'])));}
    form.addEventListener('submit',e=>{e.preventDefault();try{const values={};for(const [key,,type]of labels)values[key]=type==='number'?Number(fields[key].value):fields[key].value;state.settings=C.validateSettings(values);persist(true);draw();toast('学习计划已更新。');}catch(error){toast(error.message);}});main.append(form,results);draw();
    main.append(E('div',{className:'section-heading'},E('h2',{},'2027 年前三个月：进阶与作品交付')),P('12周安排18节进阶课程（144小时）与每周8小时项目实践（96小时）；剩余日期用于补漏和最终演示。约240小时是任务预算，按每周真实可用时间调整。下表固定为你选择的2027年第一季度，不随上面的核心日期自动移动。'));
    const advanced=lessons.filter(x=>x.level==='advanced'),weeks=data.advancedWeeks;
    main.append(E('div',{className:'timeline'},weeks.map((w,i)=>E('div',{className:'week-card'},E('div',{className:'eyebrow'},'WEEK '+String(i+1).padStart(2,'0')),E('h3',{},w.title),E('small',{},w.dates),w.lessons.map(id=>link(id.toUpperCase()+' '+lessonMap.get(id).title,'#lesson:'+id)),P(w.practice),E('small',{},'课程 '+w.lessons.reduce((n,id)=>n+lessonMap.get(id).hours,0)+' h + 项目 8 h')))));
    main.append(note('先修不足时，使用缓冲补基础；已经做过的实验可以先自测与复做，不需要重复安装。每周只把一个能展示输入、过程、输出和边界的小任务作为验收单位。'));
  }
  function renderProjects(main){
    main.append(heading('DELIVERABLES, NOT JUST DEMOS','四个阶段项目，把知识接起来','项目书明确目标、范围、验收证据和学习解释。复用你已有的文档服务、知识库与DocLens；每个阶段从一个小任务开始，逐步形成可复现的交付包。'));
    main.append(E('div',{className:'project-grid'},data.projects.map(p=>E('article',{className:'panel'},E('div',{className:'eyebrow'},p.id.toUpperCase()),E('h3',{},p.title),P(p.description),E('h4',{},'先完成这一小步'),P(p.firstTask),E('h4',{},'阶段验收'),list(p.acceptance),E('details',{},E('summary',{},'需要自己讲清的事情'),list(p.explain)),E('p',{className:'small'},'资源边界：'+p.resources)))));
    main.append(E('div',{className:'section-heading'},E('h2',{},'可直接填写的交付模板')),P('下载后填写自己的实际情况。空白项与“未执行”可以保留，不能把模板中的建议当作已经发生的事实。'));
    const preview=E('div',{});main.append(E('div',{className:'template-list'},data.templates.map(t=>B(t.title,()=>{preview.replaceChildren(section('template-preview',t.title,E('pre',{},E('code',{},t.content)),B('下载 Markdown 模板',()=>download(t.filename,t.content))));preview.scrollIntoView({behavior:'smooth',block:'start'});}))),preview);
  }
  function renderCoverage(main){
    main.append(heading('ORIGINAL OUTLINE · 22 MODULES / 110 TOPICS','逐项对照原始学习大纲','原大纲是你提供的24周能力规划。本版保留全部110项，并列出相应教程。映射只表示有阅读和练习入口，不表示所有知识点已在年底前深入掌握。'),note('核心路线聚焦能完成一次小型交付；算法拓展、Agent复杂编排、Kubernetes、多卡并行等放在进阶阶段。遇到没有当前环境的部分，以方案和模拟实验学习，实际运行状态单独记录。'));
    for(const module of data.outline.modules){const covered=data.coverage.filter(x=>x.module===module.id);main.append(E('details',{className:'coverage-row'},E('summary',{},E('span',{},module.id.toUpperCase()+' · '+module.title),E('span',{className:'small'},covered.length+' 项')),E('ol',{},covered.map(x=>E('li',{},E('div',{},x.topic),x.lessons.map(id=>link(id.toUpperCase()+' '+lessonMap.get(id).title,'#lesson:'+id)))))));}
  }
  function renderNotes(main){
    const p=progress();main.append(heading('YOUR OWN EXPLANATIONS MATTER','学习记录留在自己手里','这里保存的是阅读、练习、自测、实现证据和学习解释。当前浏览器与当前地址分别存储，换设备前导出JSON；打开网页不需要账号。'),note('这份完整知识库使用独立的记录格式，不会覆盖原“FDE学习工坊”或旧项目页面的笔记。旧页面的备份请在旧页面导入。'));
    const file=E('input',{type:'file',accept:'.json,application/json','aria-label':'选择知识库学习备份'}),importBox=E('div',{});
    const panel=E('section',{className:'panel'},E('h2',{},'备份与跨设备接续'),P('导出包含学习计划与全部记录。导入前先校验，再由你确认合并；同一课程保留时间较新的记录。'),E('div',{className:'hero-actions'},B('导出当前全部记录',exportProgress,true)),E('label',{className:'field'},E('span',{},'导入另一设备的备份（不超过8 MiB）'),file),importBox);
    file.addEventListener('change',async()=>{importBox.replaceChildren();try{const selected=file.files[0];if(!selected)return;if(selected.size>8*1024*1024)throw Error('备份超过8 MiB限制，请检查是否选对文件。');const incoming=C.validateBackup(JSON.parse(await selected.text()),lessons);const diff=C.mergeRecords(state.records,incoming.records);const restore=E('input',{type:'checkbox'});importBox.append(note('校验通过：将新增或更新 '+diff.changed+' 课，保留本地较新或相同记录 '+diff.kept+' 课。建议先导出当前记录。'),E('label',{className:'check-field'},restore,'同时恢复备份中的学习计划'),B('确认合并导入',()=>{const now=C.mergeRecords(state.records,incoming.records);state.records=now.records;if(restore.checked)state.settings=incoming.settings;const saved=persist(restore.checked);updateSideProgress();importBox.replaceChildren(note(saved?'合并完成，已保存在当前浏览器。':'已在当前页面合并，但浏览器保存失败；请立即导出备份。',saved?'':'warn'));refreshRows();},true));}catch(e){importBox.append(E('div',{className:'callout danger',role:'alert'},'未导入任何记录：'+e.message));}});
    const rows=E('div',{});function refreshRows(){const entries=lessons.filter(l=>state.records[l.id]);rows.replaceChildren(table(['课程','状态','最近保存','证据'],entries.map(l=>{const r=record(l.id),a=C.assess(l,r);return [link(l.title,'#lesson:'+l.id),a.selfChecked?'本课自验':r.practiced?'已练习':r.read?'已阅读':'草稿',new Date(r.updatedAt).toLocaleString('zh-CN'),(r.implementationEvidence?'实现 ✓':'实现待补')+' / '+(r.learningEvidence?'解释 ✓':'解释待补')];})));if(!entries.length)rows.append(E('div',{className:'empty'},'还没有学习记录。从一节核心课程开始即可。'));}
    main.append(panel,E('div',{className:'section-heading'},E('h2',{},'已保存的课程')),rows);refreshRows();
    main.append(note('清除浏览器数据、更换文件位置或使用无痕模式可能影响本地存储。课程文件可以长期保留；学习记录请定期导出。应用不会把自验结果上传，也不会自动把阅读打勾写成能力证明。'));
  }
  function render(){const current=route(),main=shell(current.view);if(current.view==='lesson')renderLesson(main,current.id);else ({courses:renderCourses,sources:renderSources,plan:renderPlan,projects:renderProjects,coverage:renderCoverage,notes:renderNotes})[current.view](main);main.append(footer());document.title=(current.id?lessonMap.get(current.id).title+' · ':'')+'FDE 学习知识库';}
  window.addEventListener('hashchange',()=>{render();window.scrollTo(0,0);});
  window.addEventListener('storage',e=>{if(e.key===KEY&&e.newValue){try{const other=C.validateBackup(JSON.parse(e.newValue),lessons);state.records=C.mergeRecords(state.records,other.records).records;state.settings=other.settings;updateSideProgress();toast('另一标签页更新了记录。数据已合并，刷新可更新正在查看的表单。');}catch(error){toast('另一标签页写入的记录无法读取，当前记录已保留。');}}});
  render();
})();
