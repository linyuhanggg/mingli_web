import { chromium } from '@playwright/test';
const B='http://106.14.10.235:18080';
const b = await chromium.launch({channel:'chrome'});
const p = await b.newPage({viewport:{width:1440,height:900}});
// 见相：填写后摘要应含保存范围
await p.goto(B+'/jianxiang',{waitUntil:'networkidle'});
await p.getByLabel('受测对象').fill('本人');
await p.getByLabel('用户补充信息').fill('左侧步态需要结合本人补充');
await p.waitForTimeout(500);
const sum = await p.locator('[aria-label="提交前摘要"]').innerText().catch(()=>'(未渲染)');
console.log('见相摘要:\n'+sum);
// 八字：时辰即时反馈
await p.goto(B+'/bazi',{waitUntil:'networkidle'});
await p.getByLabel('出生小时').selectOption('08');
await p.getByLabel('出生分钟').selectOption('30');
await p.waitForTimeout(400);
console.log('时辰反馈:', await p.locator('form').getByText(/民用钟表/).innerText());
// 首页截图
await p.goto(B+'/',{waitUntil:'networkidle'});
await p.waitForTimeout(1500);
await p.screenshot({path:'/tmp/srv/after-home.jpg', fullPage:true, type:'jpeg', quality:70});
console.log('首页高度:', await p.evaluate(()=>document.documentElement.scrollHeight));
await b.close();
