# -*- coding: utf-8 -*-
"""把 template.html + data.js 合成一个自包含的单文件原型。"""
import os

BASE = os.path.dirname(os.path.abspath(__file__))
tpl = open(os.path.join(BASE, "template.html"), encoding="utf-8").read()
data = open(os.path.join(BASE, "..", "data.js"), encoding="utf-8").read()

assert "/*__DATA__*/" in tpl, "占位符缺失"
html = tpl.replace("/*__DATA__*/", data)

out = os.path.join(BASE, "..", "世界即卡片.html")
with open(out, "w", encoding="utf-8") as f:
    f.write(html)
print("wrote", os.path.abspath(out), os.path.getsize(out), "bytes")
