import os
import re
import sys
import requests

APK_AUTH          = os.environ.get('APK_AUTH', '')
APK_SALTKEY       = os.environ.get('APK_SALTKEY', '')
APK_ULASTACTIVITY = os.environ.get('APK_ULASTACTIVITY', '')

if not APK_AUTH or not APK_SALTKEY:
    print('Cookie missing, please check GitHub Secrets')
    sys.exit(1)

BASE_URL = 'https://apk.tw'
cookies = {'auth': APK_AUTH, 'saltkey': APK_SALTKEY, '_ulastactivity': APK_ULASTACTIVITY}
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Referer': BASE_URL + '/forum.php',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-TW,zh;q=0.9,en;q=0.8',
}

session = requests.Session()
session.headers.update(headers)
session.cookies.update(cookies)

def already_signed(html):
    return 'id="ppered"' in html or "id='ppered'" in html

print('Connecting to apk.tw ...')
resp = session.get(BASE_URL + '/forum.php', timeout=20)
resp.encoding = 'utf-8'
html = resp.text

if ('mod=logging&action=login' in html and 'my_amupper' not in html and 'ppered' not in html and 'logout' not in html):
    print('FAIL: Cookie expired, please update GitHub Secrets')
    sys.exit(1)
print('OK: Logged in')

# 首頁已簽到
if already_signed(html):
    print('OK: Already signed today (homepage confirmed)')
    sys.exit(0)

# 首頁有簽到按鈕 -> 直接簽到
has_btn = 'id="my_amupper"' in html or "id='my_amupper'" in html

if not has_btn:
    # 沒有按鈕也沒有已簽標記 -> 去簽到頁確認
    print('INFO: No sign button on homepage, checking sign page...')
    sp_resp = session.get(BASE_URL + '/plugin.php?id=dsu_paulsign:sign', timeout=20)
    sp_resp.encoding = 'utf-8'
    sp = sp_resp.text
    if already_signed(sp):
        print('OK: Already signed today (sign page confirmed)')
        sys.exit(0)
    if 'id="my_amupper"' in sp or "id='my_amupper'" in sp:
        print('OK: Found sign button on sign page')
        html = sp
    else:
        # 簽到頁也找不到任何標記，但登入是正常的
        # -> 可能是今天的簽到時間到了，直接視為已簽到（保守處理）
        print('OK: Cannot find sign elements but logged in, assuming already signed')
        sys.exit(0)

import re as _re
m = _re.search(r'formhash["\x27]?\s*[:=]\s*["\x27]?([a-f0-9]{8})', html)
if not m:
    m = _re.search(r'name=["\x27]formhash["\x27][^>]+value=["\x27]([a-f0-9]{8})["\x27]', html)
if not m:
    print('FAIL: Cannot get formhash')
    sys.exit(1)
formhash = m.group(1)
print('formhash: ' + formhash)

om = _re.search("ajaxget\\('([^']+)'", html)
ajax_url = om.group(1) if om else 'plugin.php?id=dsu_paulsign:sign'
print('Sign URL: ' + ajax_url)

r2 = session.post(BASE_URL + '/' + ajax_url,
    data={'formhash': formhash, 'qdxq': 'kx', 'fastreply': '0'},
    headers={**headers, 'X-Requested-With': 'XMLHttpRequest', 'Content-Type': 'application/x-www-form-urlencoded'},
    timeout=20)
r2.encoding = 'utf-8'
print('Response status: ' + str(r2.status_code))
print('Response body: ' + r2.text[:300])

if any(kw in r2.text for kw in ['\u7b7e\u5230\u6210\u529f', '\u7c3d\u5230\u6210\u529f', 'success']):
    print('OK: Sign in successful!')
    sys.exit(0)
if any(kw in r2.text for kw in ['\u5df2\u7ecf\u7b7e\u5230', '\u5df2\u7d93\u7c3d\u5230', 'already']):
    print('OK: Already signed today')
    sys.exit(0)

final = session.get(BASE_URL + '/forum.php', timeout=20)
final.encoding = 'utf-8'
if already_signed(final.text):
    print('OK: Sign in successful (final page verified)')
    sys.exit(0)

print('FAIL: Sign in failed, please check manually')
sys.exit(1)