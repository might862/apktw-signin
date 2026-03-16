import os
import re
import sys
import requests

# ── 讀取設定 ──────────────────────────────────────────────────────
# 優先使用帳號密碼登入（其他人只需設定這兩個 Secrets）
APK_USERNAME = os.environ.get('APK_USERNAME', '')
APK_PASSWORD = os.environ.get('APK_PASSWORD', '')
# 也支援舊版 cookie 登入方式（向下相容）
APK_AUTH          = os.environ.get('APK_AUTH', '')
APK_SALTKEY       = os.environ.get('APK_SALTKEY', '')
APK_ULASTACTIVITY = os.environ.get('APK_ULASTACTIVITY', '')

if not APK_USERNAME and not APK_AUTH:
    print('FAIL: 請設定 APK_USERNAME + APK_PASSWORD 或 APK_AUTH + APK_SALTKEY')
    sys.exit(1)

BASE_URL = 'https://apk.tw'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Referer': BASE_URL + '/forum.php',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-TW,zh;q=0.9,en;q=0.8',
}

session = requests.Session()
session.headers.update(headers)

def already_signed(html):
    return 'id="ppered"' in html or "id='ppered'" in html

# ── Step 1：登入 ───────────────────────────────────────────────────
if APK_USERNAME and APK_PASSWORD:
    print('使用帳號密碼登入...')
    # 取得登入頁面的 formhash
    login_page = session.get(BASE_URL + '/member.php?mod=logging&action=login', timeout=20)
    login_page.encoding = 'utf-8'
    fh = re.search(r'formhash["\x27]?\s*[:=]\s*["\x27]?([a-f0-9]{8})', login_page.text)
    if not fh:
        print('FAIL: 無法取得登入頁面的 formhash')
        sys.exit(1)
    login_formhash = fh.group(1)
    # 送出登入請求
    login_resp = session.post(
        BASE_URL + '/member.php?mod=logging&action=login&loginsubmit=yes&infloat=yes&lssubmit=yes&inajax=1',
        data={
            'formhash':   login_formhash,
            'referer':    BASE_URL + '/forum.php',
            'loginfield': 'username',
            'username':   APK_USERNAME,
            'password':   APK_PASSWORD,
            'questionid': '0',
            'answer':     '',
        },
        headers={**headers, 'X-Requested-With': 'XMLHttpRequest',
                 'Content-Type': 'application/x-www-form-urlencoded'},
        timeout=20
    )
    login_resp.encoding = 'utf-8'
    if 'succeedhandle' not in login_resp.text and 'window.location' not in login_resp.text:
        # 嘗試另一種登入成功判斷
        if 'succeed' in login_resp.text.lower() or session.cookies.get('auth'):
            print('OK: 登入成功（帳號密碼）')
        else:
            print('FAIL: 帳號密碼登入失敗，請確認帳號密碼是否正確')
            print('回應：' + login_resp.text[:200])
            sys.exit(1)
    else:
        print('OK: 登入成功（帳號密碼）')
else:
    print('使用 Cookie 登入...')
    session.cookies.update({
        'auth': APK_AUTH,
        'saltkey': APK_SALTKEY,
        '_ulastactivity': APK_ULASTACTIVITY,
    })

# ── Step 2：連線首頁確認登入狀態 ──────────────────────────────────
print('確認登入狀態...')
resp = session.get(BASE_URL + '/forum.php', timeout=20)
resp.encoding = 'utf-8'
html = resp.text

if ('mod=logging&action=login' in html and 'my_amupper' not in html
        and 'ppered' not in html and 'logout' not in html):
    print('FAIL: 登入失敗，請確認帳號密碼或 Cookie 是否正確')
    sys.exit(1)
print('OK: 登入狀態確認')

# ── Step 3：已簽到？ ───────────────────────────────────────────────
if already_signed(html):
    print('OK: 今日已簽到（首頁確認）')
    sys.exit(0)

# ── Step 4：找簽到按鈕 ─────────────────────────────────────────────
has_btn = 'id="my_amupper"' in html or "id='my_amupper'" in html
if not has_btn:
    print('INFO: 首頁未找到簽到按鈕，前往簽到頁面確認...')
    sp = session.get(BASE_URL + '/plugin.php?id=dsu_paulsign:sign', timeout=20)
    sp.encoding = 'utf-8'
    sp_html = sp.text
    if already_signed(sp_html):
        print('OK: 今日已簽到（簽到頁面確認）')
        sys.exit(0)
    if 'id="my_amupper"' in sp_html or "id='my_amupper'" in sp_html:
        print('OK: 在簽到頁面找到簽到按鈕')
        html = sp_html
    else:
        print('OK: 找不到簽到相關元素但已登入，視為今日已簽到')
        sys.exit(0)

# ── Step 5：取得 formhash 和簽到 URL ──────────────────────────────
import re as _re
m = _re.search(r'formhash["\x27]?\s*[:=]\s*["\x27]?([a-f0-9]{8})', html)
if not m:
    m = _re.search(r'name=["\x27]formhash["\x27][^>]+value=["\x27]([a-f0-9]{8})["\x27]', html)
if not m:
    print('FAIL: 無法取得 formhash')
    sys.exit(1)
formhash = m.group(1)
print('formhash: ' + formhash)

om = _re.search("ajaxget\\('([^']+)'", html)
ajax_url = om.group(1) if om else 'plugin.php?id=dsu_paulsign:sign'
print('簽到 URL: ' + ajax_url)

# ── Step 6：送出簽到 ──────────────────────────────────────────────
r2 = session.post(BASE_URL + '/' + ajax_url,
    data={'formhash': formhash, 'qdxq': 'kx', 'fastreply': '0'},
    headers={**headers, 'X-Requested-With': 'XMLHttpRequest',
             'Content-Type': 'application/x-www-form-urlencoded'},
    timeout=20)
r2.encoding = 'utf-8'
print('回應狀態: ' + str(r2.status_code))
print('回應內容: ' + r2.text[:300])

# ── Step 7：判斷結果 ──────────────────────────────────────────────
if any(kw in r2.text for kw in ['\u7b7e\u5230\u6210\u529f', '\u7c3d\u5230\u6210\u529f', 'success']):
    print('OK: 簽到成功！')
    sys.exit(0)
if any(kw in r2.text for kw in ['\u5df2\u7ecf\u7b7e\u5230', '\u5df2\u7d93\u7c3d\u5230', 'already']):
    print('OK: 今日已簽到')
    sys.exit(0)

final = session.get(BASE_URL + '/forum.php', timeout=20)
final.encoding = 'utf-8'
if already_signed(final.text):
    print('OK: 簽到成功（最終頁面驗證確認）')
    sys.exit(0)

print('FAIL: 簽到失敗，請人工確認')
sys.exit(1)