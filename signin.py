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
cookies = {
    'auth':           APK_AUTH,
    'saltkey':        APK_SALTKEY,
    '_ulastactivity': APK_ULASTACTIVITY,
}
headers = {
    'User-Agent':      'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Referer':         BASE_URL + '/forum.php',
    'Accept':          'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-TW,zh;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection':      'keep-alive',
}

session = requests.Session()
session.headers.update(headers)
session.cookies.update(cookies)

def already_signed(html):
    return 'id="ppered"' in html or "id='ppered'" in html

# Step 1: Connect
print('Connecting to apk.tw ...')
resp = session.get(BASE_URL + '/forum.php', timeout=20)
resp.encoding = 'utf-8'
html = resp.text

# Step 2: Check login
if ('mod=logging&action=login' in html and
        'my_amupper' not in html and
        'ppered' not in html and
        'logout' not in html):
    print('FAIL: Cookie expired, please update GitHub Secrets')
    sys.exit(1)
print('OK: Logged in')

# Step 3: Already signed? (homepage)
if already_signed(html):
    print('OK: Already signed today (homepage confirmed)')
    sys.exit(0)

# Step 4: No button on homepage -> check sign page
if 'id="my_amupper"' not in html and "id='my_amupper'" not in html:
    print('INFO: No sign button on homepage, checking sign page...')
    sp_resp = session.get(BASE_URL + '/plugin.php?id=dsu_paulsign:sign', timeout=20)
    sp_resp.encoding = 'utf-8'
    sp = sp_resp.text
    # KEY FIX: already signed on sign page -> exit 0 immediately
    if already_signed(sp):
        print('OK: Already signed today (sign page confirmed)')
        sys.exit(0)
    # Found button on sign page
    if 'id="my_amupper"' in sp or "id='my_amupper'" in sp:
        print('OK: Found sign button on sign page')
        html = sp
    else:
        print('FAIL: Cannot find sign button or already-signed marker')
        print('Page snippet: ' + sp[:400])
        sys.exit(1)

# Step 5: Get formhash
m = re.search(r'formhash["\']?\s*[:=]\s*["\']?([a-f0-9]{8})', html)
if not m:
    m = re.search(r'name=["\']formhash["\'][^>]+value=["\']([a-f0-9]{8})["\']', html)
if not m:
    print('FAIL: Cannot get formhash')
    print('Page snippet: ' + html[:400])
    sys.exit(1)
formhash = m.group(1)
print('formhash: ' + formhash)

# Step 6: Get sign URL
om = re.search(r"ajaxget\('([^']+)'", html)
ajax_url = om.group(1) if om else 'plugin.php?id=dsu_paulsign:sign'
print('Sign URL: ' + ajax_url)

# Step 7: POST sign in
r2 = session.post(BASE_URL + '/' + ajax_url,
    data={(formhash': formhash, 'qdxq': 'kx', 'fastreply': '0'},
    headers={**headers, 'X-Requested-With': 'XMLHttpRequest',
             'Content-Type': 'application/x-www-form-urlencoded'},
    timeout=20)
r2.encoding = 'utf-8'
print('Response status: ' + str(r2.status_code))
print('Response body: ' + r2.text[:300])

# Step 8: Check result
if any(kg in r2.text for kw in ['签到成功', '簽到成功', 'success']):
    print('OK: Sign in successful!')
    sys.exit(0)
if any(kw in r2.text for kw in ['已经签到', '已结簽到', 'already']):
    print('OK: Already signed today')
    sys.exit(0)

# Step 9: Final page verification
final = session.get(BASE_URL + '/forum.php', timeout=20)
final.encoding = 'utf-8'
if already_signed(final.text):
    print('OK: Sign in successful (final page verified)')
    sys.exit(0)

print('FAIL: Sign in failed, please check manually')
sys.exit(1)
