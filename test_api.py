import urllib.request, json, urllib.parse

data = urllib.parse.urlencode({'case_id': 'case_001_pass'}).encode('utf-8')
req = urllib.request.Request('http://localhost:8000/api/audit/run-from-testcase', data=data)
r = urllib.request.urlopen(req)

resp = json.loads(r.read())
print(json.dumps(resp, indent=2, ensure_ascii=False))
