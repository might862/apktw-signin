import os
import re
import sys
import requests

APK_AUTH          = os.environ.get('APK_AUTH', '')
APK_SALTKEY       = os.environ.get('APK_SALTKEY', '')
APK_ULASTACTIVITY = os.environ.get('APK_ULASTACTIVITY', '')

if not APK_AUTH or not APK_SALTKEY:
    print('FAIL: Cookie 未設定，請確認 GitHub Secrets')
    sys.exit(1)

BASE_URL = 'https://apk.tw'
cookies = {
    'auth':           APK_AUTH,
    'saltkey':        APK_SALTKEY,
    '_ulastactivity': APK_ULASTACTIVITY,
}
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Referer':    BASE_URL + '/forum.php',
    'Accept':     'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-TW,zh;q=0.9,en;q=0.8',
}

session = requests.Session()
session.headers.update(headers)
session.cookies.update(cookies)

# ── 只訪問首頁 ─────────────────────────────────────────────────
# 簽到按鈕 (my_amupper) 和已簽圖示 (ppered) 都在首頁頂端導覽列
# apk.tw 用的是 dsu_amupper 外掛，不需要訪問任何外掛頁面
print('連線至 apk.tw 首頁...')
resp = session.get(BASE_URL + '/forum.php', timeout=20)
resp.encoding = 'utf-8'
html = resp.text

# ── 判斷登入狀態 ────────────────────────────────────────────────
is_login_page = (
    'mod=logging&action=login' in html and
    'my_amupper' not in html and
    'ppered'     not in html and
    'logout'     not in html
)
if is_login_page:
    print('FAIL: Cookie 已失效，請重新登入 apk.tw 並更新 GitHub Secrets')
    sys.exit(1)
print('OK: 登入狀態確認')

# ── 已簽到？ ─────────────────────────────────────────────────────
if 'id="ppered"' in html or "id='ppered'" in html:
    print('OK: 今日已簽到')
    sys.exit(0)

# ── 未簽到，找簽到按鈕並執行 ──────────────────────────────────
if 'id="my_amupper"' not in html and "id='my_amupper'" not in html:
    print('FAIL: 找不到簽到按鈕也找不到已簽標記，請確認帳號是否正常登入')
    sys.exit(1)

# 取得 onclick 裡的 ajaxget 參數
import re as _re
m = _re.search(r"ajaxget\\('([^']+)'", html)
if not m:
    print('FAIL: 找不到簽到 onclick 參數')
    sys.exit(1)

ajax_url = m.group(1)
print('簽到 URL: ' + ajax_url)

# 取 formhash
fh = _re.search(r'formhash["\x27]?\s*[:=]\s*["\x27]?([a-f0-9]{8})', html)
if not fh:
    print('FAIL: 無法取得 formhash')
    sys.exit(1)
formhash = fh.group(1)
print('formhash: ' + formhash)

# 送出簽到 POST
r2 = session.post(
    BASE_URL + '/' + ajax_url,
    data={'formhash': formhash, 'qdxq': 'kx', 'fastreply': '0'},
    headers={**headers,
             'X-Requested-With': 'XMLHttpRequest',
             'Content-Type': 'application/x-www-form-urlencoded'},
    timeout=20
)
r2.encoding = 'utf-8'
print('回應狀態: ' + str(r2.status_code))
print('回應內容: ' + r2.text[:300])

# 判斷結果
if any(kw in r2.text for kw in ['\u7c3d\u5230\u6210\u529f','\u7b7e\u5230\u6210\u529f','success']):
    print('OK: 簽到成功！')
    sys.exit(0)

if any(kw in r2.text for kw in ['\u5df2\u7d93\u7c3d\u5230','\u5df2\u7ecf\u7b7e\u5230','already']):
    print('OK: 今日已簽到')
    sys.exit(0)

# 最終驗證：再讀一次首頁確認
final = session.get(BASE_URL + '/forum.php', timeout=20)
final.encoding = 'utf-8'
if 'id="ppered"' in final.text or "id='ppered'" in final.text:
    print('OK: 簽到成功（首頁驗證確認）')
    sys.exit(0)

print('FAIL: 簽到失敗，請人工確認')
sys.exit(1)