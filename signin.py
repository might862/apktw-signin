import os
import re
import sys
import requests

# ── 從 GitHub Secrets 讀取 cookie ────────────────────────────────
APK_AUTH          = os.environ.get('APK_AUTH', '')
APK_SALTKEY       = os.environ.get('APK_SALTKEY', '')
APK_ULASTACTIVITY = os.environ.get('APK_ULASTACTIVITY', '')

if not APK_AUTH or not APK_SALTKEY:
    print('❌ 缺少必要的 cookie，請確認 GitHub Secrets 設定正確')
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

# ── Step 1：抓取首頁，確認登入狀態 ───────────────────────────────
print('📡 連線至 apk.tw ...')
resp = session.get(BASE_URL + '/forum.php', timeout=20)
resp.encoding = 'utf-8'
html = resp.text

# 偵測登入狀態（登入後首頁有 logout 連結或 uid 資訊）
is_logged_in = ('member.php?mod=logging&action=logout' in html or
                'my_info' in html or
                'uid=' in html and 'my_amupper' in html or
                'uid=' in html and 'ppered' in html)

# 也檢查是否被導向登入頁
is_login_page = ('mod=logging&action=login' in html and
                 'my_amupper' not in html and
                 'ppered' not in html and
                 'logout' not in html)

if is_login_page:
    print('❌ Cookie 已失效，請重新登入 apk.tw 並更新 GitHub Secrets 中的 cookie 值')
    sys.exit(1)

print('✅ 登入狀態確認')

# ── Step 2：確認今天是否已簽到 ────────────────────────────────────
if 'id="ppered"' in html or "id='ppered'" in html:
    print('✅ 今日已簽到，無需重複操作')
    sys.exit(0)

# ── Step 3：確認簽到按鈕存在 ─────────────────────────────────────
if 'id="my_amupper"' not in html and "id='my_amupper'" not in html:
    # 嘗試直接存取簽到外掛頁面
    print('⚠️ 首頁未找到簽到按鈕，嘗試直接存取簽到頁面...')
    sign_page = session.get(BASE_URL + '/plugin.php?id=dsu_paulsign:sign', timeout=20)
    sign_page.encoding = 'utf-8'
    if 'id="ppered"' in sign_page.text or "id='ppered'" in sign_page.text:
        print('✅ 今日已簽到（簽到頁面確認）')
        sys.exit(0)
    html = sign_page.text  # 用簽到頁面繼續

# ── Step 4：取澗 formhash ─────────────────────────────────────────
match = re.search(r'formhash["\']?\s*[:=]\s*["\']?([a-f0-9]{8})', html)
if not match:
    match = re.search(r'<input[^>]+name=["\']formhash["\'][^>]+value=["\']([a-f0-9]{8})["\']', html)
if not match:
    print('❌ 無法取得 formhash，請確認 cookie 是否有效')
    print(f'   頁面前300字元: {html[:300]}')
    sys.exit(1)

formhash = match.group(1)
print(f'🔑 formhash: {formhash}')

# ── Step 5：取得簽到 onclick 參數 ────────────────────────────────
onclick_match = re.search(r"ajaxget\('([^']+)','([^']+)','([^']+)','([^']*)','([^']*)'", html)
if onclick_match:
    ajax_url = onclick_match.group(1)
    print(f'📋 簽到 URL: {ajax_url}')
else:
    ajax_url = 'plugin.php?id=dsu_paulsign:sign'
    print(f'⚠️ 使用預設簽到 URL: {ajax_url}')

# ── Step 6：送出 POST 簽到請求 ───────────────────────────────────
sign_url = f'{BASE_URL}/{ajax_url}'
post_data = {
    'formhash': formhash,
    'qdxq':     'kx',
    'fastreply': '0',
}

print(f'📤 送出簽到請求 → {sign_url}')
sign_resp = session.post(
    sign_url,
    data=post_data,
    headers={**headers,
             'X-Requested-With': 'XMLHttpRequest',
             'Content-Type': 'application/x-www-form-urlencoded',
             'Referer': BASE_URL + '/forum.php'},
    timeout=20
)
sign_resp.encoding = 'utf-8'
result_text = sign_resp.text
print(f'📥 回應狀態: {sign_resp.status_code}')
print(f'📄 回應內容（前200字）: {result_text[:200]}')

# ── Step 7：驗證簽到結果 ─────────────────────────────────────────
success_keywords = ['簽到成功', '签到成功', 'sign_in_success', 'success']
already_keywords = ['已經簽到', '已签到', '今天已经', 'already']

if any(kw in result_text.lower() for kw in success_keywords):
    print('✅ 簽到成功！')
    sys.exit(0)
elif any(kw in result_text for kw in already_keywords):
    print('✅ 今日已簽到（重複確認）')
    sys.exit(0)

# 再次讀取首頁確認
print('🔄 再次確認簽到狀態...')
verify_resp = session.get(BASE_URL + '/forum.php', timeout=20)
verify_resp.encoding = 'utf-8'
if 'id="ppered"' in verify_resp.text or "id='ppered'" in verify_resp.text:
    print('✅ 簽到成功（頁面驗證確認）')
    sys.exit(0)

print(f'❌ 簽到失敗，請人工確認')
sys.exit(1)
