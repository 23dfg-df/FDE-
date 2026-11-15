(function (root, factory) {
  const api = factory();
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.AcademyCore = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const DAY = 86400000;
  const DEFAULT_SETTINGS = {startDate:'2026-11-16', deadline:'2026-12-31', accelerationDate:'2026-12-15', dailyHours:2, acceleratedHours:4};
  function parseDate(value) {
    if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) throw Error('日期请使用 YYYY-MM-DD 格式。');
    const stamp = Date.parse(value+'T00:00:00Z');
    if (!Number.isFinite(stamp) || new Date(stamp).toISOString().slice(0,10)!==value) throw Error('日期不存在。');
    return stamp;
  }
  function dateString(stamp) { return new Date(stamp).toISOString().slice(0,10); }
  function validateSettings(value) {
    if (!value || typeof value !== 'object' || Array.isArray(value)) throw Error('学习计划格式不正确。');
    const out = {};
    for (const key of ['startDate','deadline','accelerationDate']) { parseDate(value[key]); out[key]=value[key]; }
    const days = (parseDate(out.deadline)-parseDate(out.startDate))/DAY+1;
    if (days<1 || days>366) throw Error('核心计划日期范围应在 1–366 天内。');
    for (const key of ['dailyHours','acceleratedHours']) {
      const hours=value[key];
      if (typeof hours!=='number' || !Number.isFinite(hours) || hours<0 || hours>12) throw Error('每天学习时长应为 0–12 小时。');
      out[key]=hours;
    }
    return out;
  }
  function daysFor(settings) {
    const s=validateSettings(settings), days=[];
    for (let stamp=parseDate(s.startDate);stamp<=parseDate(s.deadline);stamp+=DAY) days.push({date:dateString(stamp),hours:stamp>=parseDate(s.accelerationDate)?s.acceleratedHours:s.dailyHours});
    return days;
  }
  function schedule(lessons, settings, reviewHours=18) {
    const days=daysFor(settings), tasks=lessons.filter(x=>x.level==='core').map(x=>({id:x.id,title:x.title,hours:x.hours}));
    if (reviewHours>0) tasks.push({id:'core-review',title:'核心项目验收、补漏与复盘',hours:reviewHours});
    let i=0, remaining=days.length?days[0].hours:0;
    const allocations=tasks.map(task=>{
      let need=task.hours, start=null, end=null, allocated=0;
      while (need>1e-9 && i<days.length) {
        if (remaining<=1e-9) { i++;remaining=i<days.length?days[i].hours:0;continue; }
        const used=Math.min(need,remaining);start=start||days[i].date;end=days[i].date;need-=used;remaining-=used;allocated+=used;
      }
      return {...task,start,end,allocated:Math.round(allocated*100)/100,complete:need<1e-9};
    });
    const capacity=days.reduce((sum,x)=>sum+x.hours,0),required=tasks.reduce((sum,x)=>sum+x.hours,0);
    return {days:days.length,capacity:Math.round(capacity*100)/100,required,shortfall:Math.max(0,Math.round((required-capacity)*100)/100),allocations};
  }
  function blankRecord() {return {read:false,practiced:false,note:'',implementationEvidence:'',learningEvidence:'',quizAnswers:[],quizChecked:false,updatedAt:new Date(0).toISOString()};}
  function nextTimestamp(previous, now=Date.now()) {
    const before=Date.parse(previous);
    return new Date(Math.max(now,Number.isFinite(before)?before+1:0)).toISOString();
  }
  function assess(lesson, record) {
    const r={...blankRecord(),...record};
    const correct=lesson.quiz.reduce((sum,q,i)=>sum+(r.quizAnswers[i]===q.answer?1:0),0);
    const quizPassed=r.quizChecked && lesson.quiz.length>0 && correct===lesson.quiz.length;
    return {correct,total:lesson.quiz.length,quizPassed,selfChecked:!!(r.read&&r.practiced&&quizPassed&&r.implementationEvidence.trim().length>=20&&r.learningEvidence.trim().length>=20)};
  }
  function searchable(lesson) {
    return [lesson.id,lesson.title,lesson.summary,...lesson.outcomes,...lesson.sections.map(s=>s.title+' '+s.body),lesson.exercise.task,...lesson.pitfalls.map(p=>p.symptom+' '+p.cause)].join(' ').toLocaleLowerCase();
  }
  function filterLessons(lessons, query='', track='', level='') {
    const terms=query.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
    return lessons.filter(x=>(!track||x.track===track)&&(!level||x.level===level)&&terms.every(term=>searchable(x).includes(term)));
  }
  function validateRecord(value, lesson) {
    if (!value || typeof value!=='object' || Array.isArray(value)) throw Error('学习记录应是对象：'+lesson.id);
    const out=blankRecord();
    for(const key of ['read','practiced','quizChecked']) {
      if(typeof value[key]!=='boolean')throw Error('学习状态应为布尔值：'+lesson.id);
      out[key]=value[key];
    }
    for(const key of ['note','implementationEvidence','learningEvidence']) {
      if(typeof value[key]!=='string'||value[key].length>20000)throw Error('笔记或证据过长/格式不正确：'+lesson.id);
      out[key]=value[key];
    }
    if(!Array.isArray(value.quizAnswers)||value.quizAnswers.length>lesson.quiz.length)throw Error('自测答案格式不正确：'+lesson.id);
    out.quizAnswers=value.quizAnswers.map((a,i)=>{
      if(a!==null&&(!Number.isInteger(a)||a<0||a>=lesson.quiz[i].options.length))throw Error('自测答案超出范围：'+lesson.id);
      return a;
    });
    if(typeof value.updatedAt!=='string'||!Number.isFinite(Date.parse(value.updatedAt)))throw Error('记录时间格式不正确：'+lesson.id);
    out.updatedAt=new Date(value.updatedAt).toISOString();
    return out;
  }
  function validateBackup(value, lessons) {
    if(!value||value.schemaVersion!==1||value.kind!=='fde-academy-progress')throw Error('这不是本知识库版本支持的学习备份；旧学习工坊记录请继续在原页面使用。');
    if(!value.records||typeof value.records!=='object'||Array.isArray(value.records))throw Error('备份缺少有效记录。');
    const byId=new Map(lessons.map(l=>[l.id,l])),records={};
    for(const [id,record] of Object.entries(value.records)) {
      if(!byId.has(id))throw Error('备份含当前版本未知的课程：'+id);
      records[id]=validateRecord(record,byId.get(id));
    }
    const settings=validateSettings(value.settings);
    return {schemaVersion:1,kind:'fde-academy-progress',contentVersion:String(value.contentVersion||''),settings,records};
  }
  function mergeRecords(current,incoming) {
    const merged={...current};let changed=0,kept=0;
    for(const [id,r] of Object.entries(incoming)) {
      if(!merged[id]||Date.parse(r.updatedAt)>Date.parse(merged[id].updatedAt)) {merged[id]={...r,quizAnswers:[...r.quizAnswers]};changed++;}
      else kept++;
    }
    return {records:merged,changed,kept};
  }
  return {DEFAULT_SETTINGS,parseDate,dateString,validateSettings,daysFor,schedule,blankRecord,nextTimestamp,assess,filterLessons,validateBackup,mergeRecords};
});
