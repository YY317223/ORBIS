# -*- coding: utf-8 -*-
"""把 Three.js、地球贴图、指标数据内联为单文件 3D 地球网页。"""
import base64, os

BASE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(BASE, "globe_assets")

tpl = open(os.path.join(BASE, "globe_template.html"), encoding="utf-8").read()
three = open(os.path.join(ASSETS, "three.min.js"), encoding="utf-8").read()
data = open(os.path.join(BASE, "..", "data.js"), encoding="utf-8").read()

if "</script" in three.lower():
    raise SystemExit("three.min.js 含有 </script>，需要转义")

def uri(name, mime):
    with open(os.path.join(ASSETS, name), "rb") as f:
        return "data:%s;base64,%s" % (mime, base64.b64encode(f.read()).decode("ascii"))

# 日间贴图默认用 4K：8K 原图 base64 后 5.8MB，占全页 56%，而球体在屏幕上最多 800px 宽。
# 需要极致画质时用 ORBIS_TEX=8k 重新构建。
DAY = os.environ.get("ORBIS_TEX", "4k").lower()
day_file = "earth_day_8k.jpg" if DAY == "8k" else "earth_day_4k.jpg"

TEX = {
    "__TEX_DAY__": uri(day_file, "image/jpeg"),
    "__TEX_NORMAL__": uri("earth_normal_2048.jpg", "image/jpeg"),
    "__TEX_SPEC__": uri("earth_specular_2048.jpg", "image/jpeg"),
    "__TEX_CLOUDS__": uri("earth_clouds_1024.png", "image/png"),
}

html = tpl.replace("/*__THREE_JS__*/", three).replace("/*__GLOBE_DATA__*/", data)
for k, v in TEX.items():
    if k not in html:
        raise SystemExit("模板缺少占位符 " + k)
    html = html.replace(k, v)

out = os.path.join(BASE, "..", "orbis.html")
with open(out, "w", encoding="utf-8") as f:
    f.write(html)
print("wrote", os.path.abspath(out), "%.1f MB" % (os.path.getsize(out) / 1048576), "| 贴图", day_file)
