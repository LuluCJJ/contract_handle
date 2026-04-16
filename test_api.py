import urllib.request, json, urllib.parse, sys
import io

# 解决 Windows 终端打印特殊字符 (如 ☑) 崩溃的问题
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

data = urllib.parse.urlencode({'case_id': 'case_014_boc_domestic_pass'}).encode('utf-8')
req = urllib.request.Request('http://localhost:8000/api/audit/run-from-testcase', data=data)
r = urllib.request.urlopen(req)

resp = json.loads(r.read())
print(json.dumps(resp, indent=2, ensure_ascii=False))
