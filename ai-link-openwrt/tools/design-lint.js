#!/usr/bin/env node
/**
 * AI-LINK Aster Design Language v1.0.0 + v2.3.4 Enhanced 16-Rule Design Linter
 * Enforces all 14 canonical Aster rules plus:
 *   Rule 15 (css-parse): Balanced parens/braces, zero unclosed functions, and >= 600 top-level rules
 *   Rule 16 (hidden-override): No bare class selector overrides [hidden] without :not([hidden]) or explicit #id[hidden] guard
 */
const fs = require('fs');
const path = require('path');

const webuiDir = process.argv[2] || path.join(__dirname, '../site/ai-link-openwrt/root/usr/share/ai-link/webui');
const htmlFile = path.join(webuiDir, 'index.html');
const cssFile = path.join(webuiDir, 'nexus.css');
const jsFile = path.join(webuiDir, 'nexus.js');
const js3dFile = path.join(webuiDir, 'nexus3d.js');

const html = fs.readFileSync(htmlFile, 'utf8');
const css = fs.readFileSync(cssFile, 'utf8');
const js = fs.readFileSync(jsFile, 'utf8');
const js3d = fs.readFileSync(js3dFile, 'utf8');

const stripComments = s => s.replace(/\/\*[\s\S]*?\*\//g, '');
const cssClean = stripComments(css);

// Split :root block vs component rules
const rootMatch = cssClean.match(/:root\s*\{([\s\S]*?)\}/);
const rootBody = rootMatch ? rootMatch[1] : '';
const nonRootCss = cssClean.replace(/:root\s*\{[\s\S]*?\}/, '');

const results = [];
function gate(id, desc, ok, detail = '') {
  results.push({ id, desc, ok, detail });
  console.log(`  ${ok ? 'PASS' : 'FAIL'}  [${id}] ${desc}${detail ? ' -> ' + detail : ''}`);
}

// 1. raw-color
const rawColorHits = [];
nonRootCss.split('\n').forEach((line, idx) => {
  if (line.includes('@ds-exception')) return;
  if (/#[0-9a-fA-F]{3,8}\b/.test(line) || /\brgba?\s*\(/.test(line) || /\bhsla?\s*\(/.test(line)) {
    rawColorHits.push(`L${idx + 1}: ${line.trim()}`);
  }
});
gate('1. raw-color', '组件 CSS 零裸色值 (全部引用 :root 令牌)', rawColorHits.length === 0, `violations=${rawColorHits.length}`);

// 2. font-size
const allowedFs = new Set(['11px', '12px', '13px', '14px', '15px', '16px', '19px', '24px', '32px', '40px', 'clamp(24px, 2.7vw, 40px)']);
const badFs = [];
for (const m of nonRootCss.matchAll(/font-size\s*:\s*([^;\}]+)/g)) {
  const v = m[1].trim();
  if (!v.startsWith('var(--fs-') && !allowedFs.has(v) && v !== 'inherit') {
    badFs.push(v);
  }
}
gate('2. font-size', '全部字号严格对齐 10 级字阶 (11~40px)', badFs.length === 0, `bad=${JSON.stringify(badFs)}`);

// 3. font-weight
const allowedFw = new Set(['400', '500', '600', '700', 'normal', 'bold', 'inherit']);
const badFw = [];
for (const m of nonRootCss.matchAll(/font-weight\s*:\s*([^;\}]+)/g)) {
  const v = m[1].trim();
  if (!allowedFw.has(v)) badFw.push(v);
}
gate('3. font-weight', '字重严格收敛于 {400, 500, 600, 700}', badFw.length === 0, `bad=${JSON.stringify(badFw)}`);

// 4. line-height
const hasNormalLh = /line-height\s*:\s*normal\b/.test(nonRootCss);
const hasBodyLh = /body\s*\{[^}]*line-height\s*:\s*1\.57/.test(nonRootCss);
gate('4. line-height', '禁用 line-height: normal 且 body 显式声明 1.57', !hasNormalLh && hasBodyLh);

// 5. radius
const allowedRadius = new Set(['0', '0px', '50%', '999px', '4px', '6px', '10px', '14px', '20px']);
const badRadius = [];
for (const m of nonRootCss.matchAll(/border-radius\s*:\s*([^;\}]+)/g)) {
  const v = m[1].trim();
  if (!v.includes('var(--r') && !v.includes('var(--radius') && !allowedRadius.has(v)) {
    badRadius.push(v);
  }
}
gate('5. radius', '圆角严格使用 6 档令牌 (--r-xs ~ --r-full)', badRadius.length === 0, `bad=${JSON.stringify(badRadius)}`);

// 6. spacing
const badGap = [];
for (const m of nonRootCss.matchAll(/\bgap\s*:\s*([^;\}]+)/g)) {
  const v = m[1].trim();
  if (v !== '0' && !v.includes('var(--sp-')) badGap.push(v);
}
gate('6. spacing', '网格与弹性间距严格使用 4pt 令牌 (--sp-0 ~ --sp-10)', badGap.length === 0, `bad=${JSON.stringify(badGap)}`);

// 7. duration
const badDur = [];
for (const m of nonRootCss.matchAll(/transition(?:-duration)?\s*:\s*([^;\}]+)/g)) {
  const v = m[1].trim();
  for (const dm of v.matchAll(/(\d+(?:\.\d+)?)(ms|s)\b/g)) {
    const ms = dm[2] === 's' ? parseFloat(dm[1]) * 1000 : parseFloat(dm[1]);
    if (ms > 480) badDur.push(dm[0]);
  }
}
gate('7. duration', '交互过渡时长全部 <= 480ms', badDur.length === 0, `bad=${JSON.stringify(badDur)}`);

// 8. z-index
const badZ = [];
for (const m of nonRootCss.matchAll(/z-index\s*:\s*([^;\}]+)/g)) {
  const v = m[1].trim();
  if (!v.startsWith('var(--z-') && v !== '0' && v !== '1' && v !== 'auto') {
    badZ.push(v);
  }
}
gate('8. z-index', 'z-index 零裸魔数 (全部使用 --z-* 命名层)', badZ.length === 0, `bad=${JSON.stringify(badZ)}`);

// 9. important
const nonReducedMotionCss = nonRootCss.replace(/@media\s*\(\s*prefers-reduced-motion\s*:\s*reduce\s*\)\s*\{[\s\S]*?\}\s*\}/g, '');
const impCount = (nonReducedMotionCss.match(/!important/g) || []).length;
gate('9. important', '非 reduced-motion 区域零 !important', impCount === 0, `count=${impCount}`);

// 10. inline-style
const inlineStyleBlocks = (html.match(/<style\b[\s\S]*?<\/style>/gi) || []);
gate('10. inline-style', 'index.html 零内联 <style> 块', inlineStyleBlocks.length === 0, `blocks=${inlineStyleBlocks.length}`);

// 11. duplicate-sheet
gate('11. duplicate-sheet', '无内联与外联样式表重复', inlineStyleBlocks.length === 0 && html.includes('nexus.css'));

// 12. emoji
const emojiRe = /[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}\u{FE0F}]/u;
const hasEmoji = emojiRe.test(html) || emojiRe.test(css) || emojiRe.test(js) || emojiRe.test(js3d);
gate('12. emoji', 'HTML/CSS/JS 全量零 Emoji 与零 U+FE0F 变异符', !hasEmoji);

// 13. dead-asset
const webuiFiles = [];
function walkDir(d, rel = '') {
  for (const ent of fs.readdirSync(d, { withFileTypes: true })) {
    const r = rel ? `${rel}/${ent.name}` : ent.name;
    if (ent.isDirectory()) walkDir(path.join(d, ent.name), r);
    else if (ent.name !== 'index.html') webuiFiles.push(r);
  }
}
walkDir(webuiDir);
const deadAssets = webuiFiles.filter(f => !html.includes(f));
gate('13. dead-asset', 'webui 目录零未引用死资源文件', deadAssets.length === 0, `files=${JSON.stringify(webuiFiles)}, dead=${JSON.stringify(deadAssets)}`);

// 14. focus-removed
const hasFocusVisible = nonRootCss.includes('button:focus-visible') && nonRootCss.includes('outline: 2px solid var(--accent)');
gate('14. focus-removed', '全局交互控件具备 2px solid var(--accent) 焦点环', hasFocusVisible);

// 15. css-parse (NEW in v2.3.4: catches P0-1 unclosed parens / braces / truncated rules)
const parenMismatchLines = [];
cssClean.split('\n').forEach((line, idx) => {
  const openP = (line.match(/\(/g) || []).length;
  const closeP = (line.match(/\)/g) || []).length;
  if (openP !== closeP) parenMismatchLines.push(`L${idx + 1}: ${line.trim()}`);
});
const openBraces = (cssClean.match(/\{/g) || []).length;
const closeBraces = (cssClean.match(/\}/g) || []).length;
const undefinedAlphaInRoot = rootBody.includes('var(--alpha)');
gate(
  '15. css-parse',
  'CSS 括号/花括号 100% 闭合、规则数 >= 650、:root 零未定义动态变量引用',
  parenMismatchLines.length === 0 && openBraces === closeBraces && openBraces >= 650 && !undefinedAlphaInRoot,
  `rules=${openBraces}, parenMismatch=${JSON.stringify(parenMismatchLines)}, undefinedAlphaInRoot=${undefinedAlphaInRoot}`
);

// 16. hidden-override (NEW in v2.3.4: catches P0-2 .modal-backdrop / .webgl-fallback overriding [hidden])
const hasModalNotHidden = nonRootCss.includes('.modal-backdrop:not([hidden])');
const hasWebglNotHidden = nonRootCss.includes('.webgl-fallback:not([hidden])');
const hasIdHiddenGuards = nonRootCss.includes('#modal[hidden]') && nonRootCss.includes('#webgl-fallback[hidden]');
gate(
  '16. hidden-override',
  '[hidden] 属性受 :not([hidden]) 与高优先级选择器双重保护',
  hasModalNotHidden && hasWebglNotHidden && hasIdHiddenGuards,
  `modalGuard=${hasModalNotHidden}, webglGuard=${hasWebglNotHidden}, idGuards=${hasIdHiddenGuards}`
);

// 17. no-fake-color-tokens (Apple HIG Audit: forbid auto-generated --_c-1 .. --_c-317 tokens)
const fakeColorMatches = cssClean.match(/--_c-\d+\b/g) || [];
gate(
  '17. no-fake-color-tokens',
  '禁止使用 --_c-* 机械序号伪色彩变量 (100% 采用语义化色彩令牌)',
  fakeColorMatches.length === 0,
  `fakeCount=${fakeColorMatches.length}`
);

// 18. apple-hig-consistency (Apple HIG Audit: card action bottom-pinning, 44px mobile touch targets, 14px base text, zero leaked ticket/API IDs)
const hasAutoPoolPin = /\.auto-pool-actions\s*\{[\s\S]*?margin-top\s*:\s*auto/.test(nonRootCss);
const hasSubActionsPin = /\.sub-actions\s*\{[\s\S]*?margin-top\s*:\s*auto/.test(nonRootCss);
const hasMobile44px = nonRootCss.includes('min-height: 44px');
const hasBase14px = /body[\s\S]*?font-size\s*:\s*14px/.test(nonRootCss);
const leakedTickets = (html + js).match(/\(T\d+\)/g) || [];
const leakedApiTitles = js.match(/\(\/api\/[a-z0-9_\/]+\)/g) || [];
gate(
  '18. apple-hig-consistency',
  'Apple HIG 卡片操作栏贴底锚定、移动端 44px 触控下限、14px 正文基准、零内部工单号/裸API泄露',
  hasAutoPoolPin && hasSubActionsPin && hasMobile44px && hasBase14px && leakedTickets.length === 0 && leakedApiTitles.length === 0,
  `autoPoolPin=${hasAutoPoolPin}, subPin=${hasSubActionsPin}, mobile44=${hasMobile44px}, base14=${hasBase14px}, tickets=${leakedTickets.length}, apiTitles=${leakedApiTitles.length}`
);

const failed = results.filter(r => !r.ok);
console.log('==============================================================================');
console.log(` Aster Design Lint v2.0 (18 Gates): PASS=${results.length - failed.length} / FAIL=${failed.length}`);
console.log('==============================================================================');
process.exit(failed.length ? 1 : 0);
