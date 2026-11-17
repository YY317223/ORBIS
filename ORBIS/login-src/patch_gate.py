# -*- coding: utf-8 -*-
"""把 ORBIS 登录封面换成「编辑部式」的版本（大字标 / 真实地球 / 无 HUD）。

用法：
    python build/patch_gate.py

输入：
    _dev/peer/orbis_live.html   线上那份（原始，未改）
    build/gate.css              新封面样式
    build/gate.html             新封面结构（含 {{EARTH_B64}} 占位）
    build/gate.js               新的地球渲染（Three.js 真实贴图）
    build/earth_tex.jpg         地球贴图（内联成 data URI）
输出：
    orbis.html                  可直接上传
"""
import base64
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, '_dev', 'peer', 'orbis_live.html')
OUT = os.path.join(ROOT, 'orbis.html')

src = open(SRC, encoding='utf-8').read()
css = open(os.path.join(ROOT, 'build', 'gate.css'), encoding='utf-8').read()
html = open(os.path.join(ROOT, 'build', 'gate.html'), encoding='utf-8').read()
js = open(os.path.join(ROOT, 'build', 'gate.js'), encoding='utf-8').read()

b64 = 'data:image/jpeg;base64,' + base64.b64encode(
    open(os.path.join(ROOT, 'build', 'earth_tex.jpg'), 'rb').read()).decode()
html = html.replace('{{EARTH_B64}}', b64)

# ---- 1. 样式：/* 登录封面 */ … /* 搜索 */ ----
# 注意：这一段里混着 6 条 #brand 规则（主页面左上角的品牌），不能整段删掉，
# 只能把门控相关的规则挑出来丢掉，其余原样保留。
def split_rules(seg):
    rules, i = [], 0
    while True:
        j = seg.find('{', i)
        if j < 0:
            break
        sel = seg[i:j].strip()
        depth, k = 1, j + 1
        while k < len(seg) and depth:
            if seg[k] == '{':
                depth += 1
            elif seg[k] == '}':
                depth -= 1
            k += 1
        rules.append((sel, seg[j + 1:k - 1]))
        i = k
    return rules

a = src.index('/* 登录封面 */')
b = src.index('/* 搜索 */')
assert a < b
kept = []
for sel, body in split_rules(src[a:b]):
    if sel.startswith('#brand'):
        kept.append(sel + '{' + body + '}')
rebuilt = '\n'.join(kept) + '\n/* 登录封面 */\n' + css + '\n'
src = src[:a] + rebuilt + src[b:]

# ---- 2. 结构：<!-- 登录封面 --> … <canvas id="globe"> ----
a = src.index('<!-- 登录封面：进入主界面之前 -->')
b = src.index('<canvas id="globe">')
assert a < b
src = src[:a] + html + '\n' + src[b:]

# ---- 3. 脚本：旧的线框地球 IIFE ----
mark = '/* ===== 登录页动态线框地球'
a = src.index(mark)
b = src.index('})();', a) + len('})();')
assert a < b
src = src[:a] + js.strip() + src[b:]

# ---- 4. 登录后的欢迎层 ----
# 原来给已登录用户写的是「从太空看地球 · 欢迎回来，探索者」，
# 「欢迎回来，探索者」已从封面删掉，这里也一并统一成新的副标。
src = src.replace('从太空看地球 · 欢迎回来，探索者', '从太空看地球 · 带你用数据看世界')

open(OUT, 'w', encoding='utf-8').write(src)

print('%s  %.2f MB' % ('orbis.html', len(src.encode()) / 1048576))
for k in ('id="authgate"', 'ag-word', 'agEarthTex', 'agGlobe', '带你用数据看世界', '欢迎回来'):
    print('%-22s %d' % (k, src.count(k)))
