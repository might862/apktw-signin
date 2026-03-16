import os
import re
import sys
import requests

# ── 從 GitHub Secrets 讀取 cookie ────────────────────────────────
APK_AUTH          = os.environ.get('APK_AUTH', '')
APK_SALTKEY       = os.environ.get('APK_SALTKEY', '')
APK_ULASTACTIVITY = os.environ.get('APK_ULASTACTIVITY', '')

if not APK_AUTH or not APK_SALTKEY:
    print('❌ 缺少必要的 cookie (APK_AUTH / APK_SALTKEY)，請確認 GitHub Secrets 設定正確')
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
}

session = requests.Session()
session.headers.update(headers)
session.cookies.update(cookies)

# ── Step 1：抓取首頁，確認登入狀態並取得 formhash ────────────────
print('📡 連線至 apk.tw ...')
resp = session.get(BASE_URL + '/forum.php', timeout=20)
resp.encoding = 'utf-8'
html = resp.text

# 確認是否登入
if 'member.php?mod=logging&action=login' in html and 'my_amupper' not in html and 'ppered' not in html:
    print('❌ Cookie 已失效，請重新登入 apk.tw 並更新 GitHub Secrets 中的 cookie 值')
    sys.exit(1)

# 確認今天是否已簽到
if 'id="ppered"' in html or "id='ppered'" in html:
    print('✅ 今日已簽到，無需重複操作')
    sys.exit(0)

# 確認簽到按鈕是否存在
if 'id="my_amupper"' not in html and "id='my_amupper'" not in html:
    print('⚠️  找不到簽到按鈕，可能已簽到或頁面結構變更')
    # 嘗試繼續送出請求
    
# 抓取 formhash
match = re.search(r'formhash["\']?\s*[:=]\s*["\']?([a-f0-9]{8})', html)
if not match:
    # 備援：從隱藏 input 找
    match = re.search(r'<input[^>]+name=["\']formhash["\'][^>]+value=["\']([a-f0-9]{8})["\']', html)
if not match:
    print('❌ 無法取得 formhash，請確認 cookie 是否有效')
    sys.exit(1)

formhash = match.group(1)
print(f'🔑 formhash: {formhash}')

# ── Step 2：抓取 onclick 裡的 ajaxget 參數 ───────────────────────
# 格式: ajaxget('plugin.php?id=dsu_paulsign:sign','signin','qiandao','', '')
onclick_match = re.search(r"ajaxget\('([^']+)','([^']+)','([^']+)','([^']*)','([^']*)'\)", html)

if onclick_match:
    ajax_url  = onclick_match.group(1)
    ajax_id   = onclick_match.group(2)
    ajax_code = onclick_match.group(3)
    ajax_p4   = onclick_match.group(4)
    ajax_p5   = onclick_match.group(5)
    print(f'📋 簽到 URL: {ajax_url}')
else:
    # 備援：用常見的 Discuz DSU 簽到外掛 URL
    ajax_url  = 'plugin.php?id=dsu_paulsign:sign'
    ajax_id   = 'signin'
    ajax_code = 'qiandao'
    ajax_p4   = ''
    ajax_p5   = ''
    print(f'⚠️  未找到 onclick 參數，使用預設 URL: {ajax_url}')

# ── Step 3：送出簽到 POST 請求 ────────────────────────────────────
sign_url = f'{BASE_URL}/{ajax_url}'
post_data = {
    'formhash':  formhash,
    'qdxq':      'kx',        # 心情：開心（kx=開心, ng=努力, sh=傷心 ...）
    'fastreply': '0',
}

print(f'📤 送出簽到請求 → {sign_url}')
sign_resp = session.post(
    sign_url,
    data=post_data,
    headers={**headers, 'X-Requested-With': 'XMLHttpRequest'},
    timeout=20
)
sign_resp.encoding = 'utf-8'
result_text = sign_resp.text
print(f'📥 回應狀態: {sign_resp.status_code}')

# ── Step 4：解析結果 ──────────────────────────────────────────────
if '簽到成功' in result_text or '签到成功' in result_text or 'success' in result_text.lower():
    print('✅ 簽到成功！')
elif '已經簽到' in result_text or '已经签到' in result_text or 'already' in result_text.lower():
    print('✅ 今日已簽到（重複確認）')
elif sign_resp.status_code == 200:
    # 再次讀取首頁確認
    verify_resp = session.get(BASE_URL + '/forum.php', timeout=20)
    verify_resp.encoding = 'utf-8'
    if 'id="ppered"' in verify_resp.text or "id='ppered'" in verify_resp.text:
        print('✅ 簽到成功（頁面驗證確認）')
    else:
        print(f'⚠️  簽到結果不明，回應內容（前200字）：{result_text[:200]}')
        sys.exit(1)
else:
    print(f'❌ 簽到失敗，HTTP {sign_resp.status_code}，回應：{result_text[:200]}')
    sys.exit(1)
