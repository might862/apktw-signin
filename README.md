# APK.TW 每日自動簽到

不需要開電腦、不需要開瀏覽器，GitHub 雲端每天凌晨 **00:10** 自動幫你在 apk.tw 簽到。

---

## 使用方法

### 步驟一：Fork 這個倉庫

點右上角 **Fork** → 建立自己的私人副本（建議選 Private）。

### 步驟二：取得 apk.tw 的 Cookie（只需做一次）

登入需要圖形驗證碼，所以我們用瀏覽器手動登入後，把登入狀態（cookie）存進 GitHub，之後 GitHub 就能直接用這組 cookie 幫你簽到，**不會觸發驗證碼**。

**操作步驟：**

1. 用 Chrome 或 Edge **登入 apk.tw**
2. 按鍵盤 `F12` 開啟開發者工具
3. 點上方 **Application**（應用程式）標籤
4. 左側展開 **Storage → Cookies → https://apk.tw**
5. 找到以下三個 cookie，分別複製 **Value** 欄位的值：

| Cookie 名稱 | 說明 |
|---|---|
| `auth` | 登入憑證（最重要）|
| `saltkey` | 加密鹽值 |
| `_ulastactivity` | 活動時間戳 |

### 步驟三：設定 GitHub Secrets

進入你 Fork 的倉庫 → **Settings → Secrets and variables → Actions → New repository secret**，新增以下三個：

| Secret 名稱 | 填入的值 |
|---|---|
| `APK_AUTH` | 上一步複製的 `auth` cookie 值 |
| `APK_SALTKEY` | 上一步複製的 `saltkey` cookie 值 |
| `APK_ULASTACTIVITY` | 上一步複製的 `_ulastactivity` cookie 值 |

> **安全說明：** Secrets 加密儲存，只有你看得到。Fork 別人倉庫時 Secrets **不會被複製**，完全安全。

### 步驟四：測試執行

進入倉庫 → **Actions** → 左側點 **APK.TW 每日自動簽到** → 右側 **Run workflow** 手動觸發一次，確認執行成功（綠色 ✅）。

---

## Cookie 失效了怎麼辦？

Cookie 通常可以用數個月，失效時 Actions 會顯示 `FAIL: Cookie expired`。

只需重新執行步驟二，到瀏覽器 F12 複製新的三個 cookie 值，更新 GitHub Secrets 即可。

---

## 修改簽到時間

預設為每天台灣時間 **00:10**。如需修改，編輯 `.github/workflows/signin.yml` 的 cron 設定：

```yaml
- cron: '10 16 * * *'  # 分 時(UTC) * * *，台灣時間 = UTC+8
```

| 台灣時間 | cron 設定 |
|---|---|
| 00:10 | `'10 16 * * *'` |
| 08:00 | `'0 0 * * *'` |
| 12:00 | `'0 4 * * *'` |
| 22:00 | `'0 14 * * *'` |