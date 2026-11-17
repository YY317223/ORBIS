#!/bin/bash
for code in NV.AGR.TOTL.ZS NV.IND.TOTL.ZS NV.SRV.TOTL.ZS NV.IND.MANF.ZS; do
  echo "===$code==="
  curl -s --max-time 30 "https://api.worldbank.org/v2/country/CHN/indicator/$code?format=json&per_page=3&date=2021:2023" -o "/tmp/wb_$code.json"
  python3 -c "
import json
d=json.load(open('/tmp/wb_$code.json'))
print('total', d[0].get('total'), '|', [(x['date'], round(x['value'],1) if x['value'] is not None else None) for x in d[1]] if len(d)>1 else 'empty')
" 2>&1 | head -c 220
  echo
done
