# -*- coding: utf-8 -*-
"""把方案外壳（登录门 + 画板承接 + 免费/会员门控）注入搭档那版地球，生成演示文件。

用法：
    python build/mk_demo.py

输入：
    _dev/peer/orbis_peer.html   搭档的原版（未改动的副本）
    build/plan_shell.html       外壳：登录门 / 方案切换 / 门控
    build/peer_card.css         右侧国家档案卡（样式）
    build/card_data.js          卡片数据（由 mk_carddata.py 生成）
    build/peer_card.js          卡片逻辑
    build/peer_cmp.css          对比盒子（样式）
    build/peer_cmp.js           对比盒子（拖入国家 → 生成对比图）
    build/peer_dive.css         俯冲转场（样式）
    build/peer_dive.js          俯冲转场（点国家时地球放大、国家页落地）
    build/peer_space.css        飞升（太阳系）样式
    build/peer_space.js         飞升（独立 WebGL 场景，不碰搭档的渲染器）
输出：
    orbis_demo.html             可直接双击打开

为什么是「替换最后一段 script」而不是整体重写：
    搭档那版 = Three.js + 数据 + 2MB 压缩主逻辑 + 我们后来加的登录门。
    前三段属于他的成果，一个字节都不该动；登录门那段本来就是我们的，
    整段换掉最干净，也方便反复迭代。
"""
import base64
import os
import re

PEER = os.path.join('_dev', 'peer', 'orbis_peer.html')
SHELL = os.path.join('build', 'plan_shell.html')
CARD_CSS = os.path.join('build', 'peer_card.css')
CARD_DATA = os.path.join('build', 'card_data.js')
CARD_JS = os.path.join('build', 'peer_card.js')
CMP_CSS = os.path.join('build', 'peer_cmp.css')
CMP_JS = os.path.join('build', 'peer_cmp.js')
SPACE_CSS = os.path.join('build', 'peer_space.css')
SPACE_JS = os.path.join('build', 'peer_space.js')
EARTH_TEX = os.path.join('build', 'earth_tex.jpg')
DIVE_CSS = os.path.join('build', 'peer_dive.css')
DIVE_JS = os.path.join('build', 'peer_dive.js')
OUT = 'orbis_demo.html'

if not os.path.exists(PEER):
    raise SystemExit('缺少搭档原版：' + PEER)
if not os.path.exists(CARD_DATA):
    raise SystemExit('缺少卡片数据，先跑：python build/mk_carddata.py')

src = open(PEER, encoding='utf-8').read()
shell = open(SHELL, encoding='utf-8').read()

# 卡片三件套：样式 / 数据 / 逻辑，全部内联，保证双击本地文件也能跑
card = (
    '\n<!-- ==== 国家档案卡：样式 ==== -->\n'
    '<style id="pcard-css">\n' + open(CARD_CSS, encoding='utf-8').read() + '\n</style>\n'
    '<!-- ==== 国家档案卡：数据（26 年 × 10 指标 + 国旗 + 邻国）==== -->\n'
    '<script id="pcard-data">\n' + open(CARD_DATA, encoding='utf-8').read() + '</script>\n'
    '<!-- ==== 国家档案卡：逻辑 ==== -->\n'
    '<script id="pcard-js">\n' + open(CARD_JS, encoding='utf-8').read() + '</script>\n'
    '<!-- ==== 对比盒子：样式 ==== -->\n'
    '<style id="pcmp-css">\n' + open(CMP_CSS, encoding='utf-8').read() + '\n</style>\n'
    '<!-- ==== 对比盒子：逻辑 ==== -->\n'
    '<script id="pcmp-js">\n' + open(CMP_JS, encoding='utf-8').read() + '</script>\n'
    '<!-- ==== 飞升：地球贴图（内联，避免额外请求）==== -->\n'
    '<script id="pspace-tex">window.__EARTH_TEX__="data:image/jpeg;base64,' +
    base64.b64encode(open(EARTH_TEX, 'rb').read()).decode() + '";</script>\n'
    '<!-- ==== 飞升：样式 ==== -->\n'
    '<style id="pspace-css">\n' + open(SPACE_CSS, encoding='utf-8').read() + '\n</style>\n'
    '<!-- ==== 飞升：逻辑 ==== -->\n'
    '<script id="pspace-js">\n' + open(SPACE_JS, encoding='utf-8').read() + '</script>\n'
    '<!-- ==== 俯冲转场：样式 ==== -->\n'
    '<style id="pdive-css">\n' + open(DIVE_CSS, encoding='utf-8').read() + '\n</style>\n'
    '<!-- ==== 俯冲转场：逻辑 ==== -->\n'
    '<script id="pdive-js">\n' + open(DIVE_JS, encoding='utf-8').read() + '</script>\n'
)

pos = [m.start() for m in re.finditer(r'<script', src)]
if not pos:
    raise SystemExit('原版里没有 script')

last = pos[-1]
end = src.find('</script>', last) + len('</script>')
tail = src[last:end]

# 安全阀：最后一段必须是「登录门」，否则说明原版结构变了，不能盲替
if 'atlas.session' not in tail and 'orbis' not in tail.lower():
    raise SystemExit('最后一段 script 不像登录门，已中止：' + tail[:120])

out = src[:last] + shell + card + src[end:]
open(OUT, 'w', encoding='utf-8').write(out)

print('%s  %.2f MB' % (OUT, len(out.encode()) / 1048576))
print('外壳已注入：', 'plan-shell' in out)
print('卡片已注入：', 'pcard-js' in out)
print('对比盒子已注入：', 'pcmp-js' in out)
print('俯冲转场已注入：', 'pdive-js' in out)
print('飞升已注入：', 'pspace-js' in out)
print('旧门残留：', out.count('orbis-user'))
