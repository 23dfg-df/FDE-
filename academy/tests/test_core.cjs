const test=require('node:test');
const assert=require('node:assert/strict');
const C=require('../web/core.js');
const lesson={id:'eng-01',title:'事务与回滚',summary:'保存数据库',outcomes:['识别提交边界'],sections:[{title:'临时表',body:'SQLite 故障与恢复'}],exercise:{task:'观察回滚'},pitfalls:[{symptom:'锁等待',cause:'事务未结束'}],track:'engineering',level:'core',hours:6,quiz:[{options:['甲','乙','丙'],answer:1},{options:['甲','乙','丙'],answer:2}]};
test('日期按北京时间日历所指日期计算，包含首尾126小时',()=>{
  const p=C.schedule([lesson],C.DEFAULT_SETTINGS,0);assert.equal(p.days,46);assert.equal(p.capacity,126);assert.equal(p.allocations[0].end,'2026-11-18');
});
test('加速日期边界与核心108小时加18小时复盘',()=>{
  const lessons=Array.from({length:18},(_,i)=>({...lesson,id:'x'+i}));
  const p=C.schedule(lessons,C.DEFAULT_SETTINGS);assert.equal(p.required,126);assert.equal(p.shortfall,0);assert.equal(p.allocations.at(-1).end,'2026-12-31');
});
test('实践计划按六阶段重排126小时，不叠加旧课程和复盘预算',()=>{
  const {phases}=require('../content/practice.json');
  const p=C.schedule(phases,C.DEFAULT_SETTINGS,0);
  assert.equal(p.required,126);assert.equal(p.capacity,126);assert.equal(p.shortfall,0);
  assert.equal(p.allocations.length,6);
  for(let i=0;i<phases.length;i++){
    assert.equal(p.allocations[i].start,phases[i].start);
    assert.equal(p.allocations[i].end,phases[i].end);
    assert.equal(p.allocations[i].allocated,phases[i].hours);
    assert.equal(p.allocations[i].complete,true);
  }
});
test('实践预算不足只分配可用时间，不把未排完阶段显示为完成',()=>{
  const {phases}=require('../content/practice.json');
  const p=C.schedule(phases,{...C.DEFAULT_SETTINGS,deadline:'2026-11-24'},0);
  assert.equal(p.capacity,18);assert.equal(p.required,126);assert.equal(p.shortfall,108);
  assert.equal(p.allocations[0].complete,true);
  assert.equal(p.allocations[1].allocated,4);assert.equal(p.allocations[1].complete,false);
  assert.equal(p.allocations[2].start,null);
  assert.equal(p.allocations.reduce((sum,x)=>sum+x.allocated,0),18);
});
test('预算不足保留未完成任务，零时长日不会死循环',()=>{
  const p=C.schedule([lesson],{...C.DEFAULT_SETTINGS,startDate:'2026-12-30',deadline:'2026-12-31',acceleratedHours:0},0);assert.equal(p.shortfall,6);assert.equal(p.allocations[0].complete,false);assert.equal(p.allocations[0].start,null);
});
test('非法日期和过大窗口拒绝，不偷偷归一化日期',()=>{
  assert.throws(()=>C.parseDate('2026-02-30'));assert.throws(()=>C.validateSettings({...C.DEFAULT_SETTINGS,deadline:'2026-01-01'}));assert.throws(()=>C.validateSettings({...C.DEFAULT_SETTINGS,dailyHours:Infinity}));
});
test('搜索覆盖正文和故障、支持多词与类型筛选',()=>{
  assert.equal(C.filterLessons([lesson],'sqlite 回滚').length,1);assert.equal(C.filterLessons([lesson],'锁等待').length,1);assert.equal(C.filterLessons([lesson],'','ai').length,0);
});
test('阅读和正确选择不自动代表练习或掌握',()=>{
  const r={...C.blankRecord(),read:true,quizAnswers:[1,2],quizChecked:true};assert.equal(C.assess(lesson,r).quizPassed,true);assert.equal(C.assess(lesson,r).selfChecked,false);
});
test('自验必须有两类证据和提交过的正确自测',()=>{
  const r={...C.blankRecord(),read:true,practiced:true,quizAnswers:[1,2],quizChecked:true,implementationEvidence:'实际执行并记录事务提交前后各自的数据库行数，异常后零条。',learningEvidence:'我能够解释提交边界，提前提交的数据不能被后一次回滚撤销。'};
  assert.equal(C.assess(lesson,r).selfChecked,true);r.quizAnswers=[0,2];assert.equal(C.assess(lesson,r).selfChecked,false);
});
function backup(record=C.blankRecord()){return {schemaVersion:1,kind:'fde-academy-progress',contentVersion:'1',settings:C.DEFAULT_SETTINGS,records:{'eng-01':record}};}
test('课程内容升级保留旧版备份的笔记、学习证据和自定义时间设置',()=>{
  const record={...C.blankRecord(),read:true,practiced:true,note:'旧版已保存的学习笔记',implementationEvidence:'我保存了实际运行记录。',learningEvidence:'我能够解释自己的结果。',updatedAt:'2026-11-16T00:00:00Z'};
  const old={...backup(record),contentVersion:'2026.11.16-v1',settings:{...C.DEFAULT_SETTINGS,dailyHours:1.5}};
  const restored=C.validateBackup(old,[lesson]);
  assert.deepEqual(restored.records['eng-01'],{...record,updatedAt:new Date(record.updatedAt).toISOString()});
  assert.deepEqual(restored.settings,old.settings);
  const upgraded=C.validateBackup({...restored,contentVersion:'2026.11.16-v2'},[lesson]);
  assert.deepEqual(upgraded.records,restored.records);
  assert.equal(upgraded.settings.dailyHours,1.5);
});
test('备份严格验证，未知课程和伪造答案不写入',()=>{
  assert.equal(Object.keys(C.validateBackup(backup(),[lesson]).records).length,1);
  assert.throws(()=>C.validateBackup(backup({...C.blankRecord(),quizAnswers:[99]}),[lesson]));
  const b=backup();b.records.unknown=C.blankRecord();assert.throws(()=>C.validateBackup(b,[lesson]));assert.throws(()=>C.validateBackup({...backup(),schemaVersion:2},[lesson]));
});
test('导入只合并较新记录，旧备份不覆盖新笔记',()=>{
  const old={...C.blankRecord(),note:'旧',updatedAt:'2026-11-16T00:00:00Z'},fresh={...old,note:'新',updatedAt:'2026-11-17T00:00:00Z'};
  const result=C.mergeRecords({'eng-01':fresh},{'eng-01':old});assert.equal(result.records['eng-01'].note,'新');assert.equal(result.kept,1);
});
test('导入时钟超前的记录后仍能保存自己的新输入',()=>{
  const imported={...C.blankRecord(),note:'旧设备时钟超前',updatedAt:'2030-01-01T00:00:00Z'};
  const edited={...imported,note:'我刚刚亲自修改',updatedAt:C.nextTimestamp(imported.updatedAt,Date.parse('2026-11-16T00:00:00Z'))};
  assert.equal(C.mergeRecords({'eng-01':imported},{'eng-01':edited}).records['eng-01'].note,'我刚刚亲自修改');
});
test('脚本字符串只作为笔记数据保留，不作为HTML解析',()=>{
  const b=backup({...C.blankRecord(),note:'<img src=x onerror=alert(1)>'});assert.equal(C.validateBackup(b,[lesson]).records['eng-01'].note,b.records['eng-01'].note);
});
