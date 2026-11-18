# -*- coding: utf-8 -*-
"""把我们这一层（国家档案卡 + 右侧工具条入口 + 快照）叠到任意版本的 orbis.html 上。

和 patch_gate.py 的分工：
    patch_gate.py  从「未改过封面的原始页面」出发，换登录封面（结构/样式/脚本/文案）
    apply_ui.py    从「已经换过封面的页面」出发，只叠 UI 层——可重复执行
                   （上游更新 orbis.html 后，重跑这一个脚本即可）

用法：
    python build/apply_ui.py
    python build/apply_ui.py --src _remote/latest/ORBIS/orbis.html --out orbis.html

输出里会打印每个模块是否注入成功，方便和上游版本做对照。
"""
import argparse
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BEGIN = '<!-- ==== ORBIS UI 层：开始 ==== -->'
END = '<!-- ==== ORBIS UI 层：结束 ==== -->'


def read(rel):
    return open(os.path.join(ROOT, rel), encoding='utf-8').read()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', default=os.path.join('_remote', 'latest', 'ORBIS', 'orbis.html'))
    ap.add_argument('--out', default='orbis.html')
    args = ap.parse_args()

    src_path = args.src if os.path.isabs(args.src) else os.path.join(ROOT, args.src)
    out_path = args.out if os.path.isabs(args.out) else os.path.join(ROOT, args.out)
    if not os.path.exists(src_path):
        raise SystemExit('找不到源文件：' + src_path)

    src = open(src_path, encoding='utf-8').read()
    original_len = len(src)

    # 1) 清掉上一次注入，保证可重复执行
    if BEGIN in src:
        a = src.index(BEGIN)
        b = src.index(END) + len(END)
        src = src[:a] + src[b:]
        print('已清除上一次注入的 UI 层')

    card_data = read('build/card_data.js')
    card_css = read('build/peer_card.css')
    card_js = read('build/peer_card.js')
    ui_css = read('build/ui_patch.css')
    ui_js = read('build/ui_patch.js')

    block = (
        '\n' + BEGIN + '\n'
        '<!-- 国家档案卡：数据（内联，单文件可离线运行；卡片本身被 ui_patch.css 隐藏，只用于出快照）-->\n'
        '<script id="pcard-data">\n' + card_data + '\n</script>\n'
        '<style id="pcard-css">\n' + card_css + '\n</style>\n'
        '<script id="pcard-js">\n' + card_js + '\n</script>\n'
        '<!-- 一级界面：指南 / 对比 / 快照 -->\n'
        '<style id="ui-patch-css">\n' + ui_css + '\n</style>\n'
        '<script id="ui-patch-js">\n' + ui_js + '\n</script>\n'
        + END + '\n'
    )

    if '</body>' in src:
        k = src.rindex('</body>')
        src = src[:k] + block + src[k:]
    else:
        src += block

    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(src)

    print('%s  %.2f MB（源 %.2f MB，+%.2f MB）' %
          (os.path.basename(out_path), len(src.encode()) / 1048576,
           original_len / 1048576, (len(src) - original_len) / 1048576))
    for k, name in (('id="authgate"', '登录门'), ('ag-word', '新字标'),
                    ('pcard-data', '卡片数据'), ('pcard-js', '卡片模块'),
                    ('ui-patch-js', '工具条/快照脚本'), ('uzGuide', '指南入口'),
                    ('csnap', '左侧快照按钮')):
        print('%-16s %d' % (name, src.count(k)))


if __name__ == '__main__':
    main()
