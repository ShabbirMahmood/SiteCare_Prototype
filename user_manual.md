# SiteCare User Manual / 操作マニュアル

[Setup Instructions](setup_instruction.md) · [Project Overview](README.md)

## English

### 1. Open and sign in

Start SiteCare and open [http://127.0.0.1:8000](http://127.0.0.1:8000/). Sign in with your account. Use **日本語 / EN** to change the language. For a fresh installation, create an administrator account first.

### 2. Open a patient and prepare the photo

1. Choose **Patients → Create Patient**, or open an existing patient.
2. Choose **New Visit Photo** and upload a JPEG/PNG with the correct capture time. Include the navel and a measured ruler.
3. Use **Navel**, **Move Photo**, **Photo Size**, and **Photo Rotation** to align the photo.
4. Use **Ruler**: select two ruler marks and enter their actual distance in cm.
5. Complete **Verify & Save Alignment**. Each new photo needs calibration and verification.

For practice, an administrator can use **Load Demo** or **Settings & Data → Load / Open Demo**. Upload `samples/synthetic_abdomen.jpg` as a new visit photo to practice alignment; its ruler has a 10 cm reference.

### 3. Edit the numbered layout

Choose **Edit 14 Sites** and drag the circles before any puncture or skin observation has been recorded.

| Button | Action |
| --- | --- |
| **Save 14-Site Layout** — red | Save the dragged positions. |
| **Default Layout** — blue | Immediately restore and save all original positions; retain photo-alignment edits. |
| **Discard Changes** — yellow | Return to the last saved layout and alignment. It does not undo an already saved reset. |

Layout changes and photo alignment are saved separately. Once records reference the layout/photo, the relevant geometry is locked.

### 4. Review and record

- Select a numbered site, candidate, or **Site Status** row to see its details.
- **Green:** rule-eligible. **Blue:** resting. **Red:** blocked. **Gray:** photo verification needed.
- Use **Exact Point** to select the actual location, then **Record Completed Puncture** with its actual time and confirmations.
- Use **Add Historical Record** for an older completed procedure; provide an explanation.
- Use **Draw Alert** to mark a skin concern. In **Skin Alerts**, choose **Confirm Full Recovery**, enter the assessment, and save when recovery has been confirmed.

Recovery clears that alert immediately. No additional recurring-episode review is required. Other active alerts, rest, spacing, and photo checks can still exclude the site. Eligible sites rejoin the numbered candidate order immediately.

### 5. Dates, appointments, and administration

- **Appointments:** review suggested visits and use **Confirm / Change** to confirm a time. The usual suggestion is 72 hours after the latest applicable puncture.
- **Change Date** (administrator): choose a demonstration date or **Use System Date**, then **Apply Date**. The selected clock is shared across patients and windows and continues running. All workflow dates use JST.
- **Profile → Delete Patient…** (administrator): review the summary, type the exact patient ID, and choose **Delete Permanently**. There is no in-app undo; audit history and previous backups remain.
- **Settings & Data → Download Complete Backup** (administrator): save a database-and-photos backup. Patient **CSV** export is not a full backup.
- Finish saving, sign out if needed, and press **Ctrl+C** in the server terminal to stop. Closing the browser alone does not stop the server.

**If a control is unavailable:** use the latest photo, verify alignment, and resolve the stated restriction. A new-procedure photo must be within 24 hours of the application clock. Upload a new photo when a saved record has locked the old photo's alignment.

This is a demonstration prototype. Use synthetic/de-identified data; green markers and photo measurements do not establish clinical suitability.

---

## 日本語

### 1. 起動とログイン

SiteCare を起動し、[http://127.0.0.1:8000](http://127.0.0.1:8000/) を開いてログインします。**日本語 / EN** で表示言語を切り替えられます。新規インストールでは、最初に管理者アカウントを作成します。

### 2. 患者と写真の準備

1. **患者一覧 → 患者を登録**で登録するか、既存の患者を開きます。
2. **今回の写真を追加**で JPEG/PNG を選び、実際の撮影日時を入力します。臍と実測用の定規を写してください。
3. **臍・写真移動・写真サイズ・写真回転**で位置を合わせます。
4. **定規**で写真内の目盛りを2点選び、実際の距離を cm で入力します。
5. **確認して位置を保存**を選び、確認項目を完了して保存します。新しい写真は毎回、校正と位置確認が必要です。

練習用データは、管理者が **デモを読み込む**、または **設定・データ → デモを読み込む・開く** から追加できます。位置合わせの練習には `samples/synthetic_abdomen.jpg` を新しい写真として追加します。図内の定規には 10 cm の基準があります。

### 3. 14部位の配置変更

穿刺記録・皮膚所見を追加する前に、**14部位調整**を選び、番号の円をドラッグします。

| ボタン | 操作 |
| --- | --- |
| **14部位配置を保存** — 赤 | 調整した配置を保存します。 |
| **標準配置** — 青 | 元の14部位配置に戻して直ちに保存します。写真の位置合わせ編集は保持されます。 |
| **変更を破棄** — 黄 | 最後に保存した配置と位置合わせに戻します。保存済みのリセットは取り消しません。 |

部位配置と写真の位置合わせは別々に保存します。記録に使用した配置・写真の位置合わせは、該当する編集が固定されます。

### 4. 確認と記録

- 写真の番号、候補、または **部位状態**の行を選ぶと詳細を確認できます。
- **緑：条件適合／青：休止中／赤：使用不可／灰：写真確認待ち**です。
- **実際の点**で位置を選び、**実施済みの穿刺を記録**で実際の日時と確認事項を入力します。
- 古い実施記録には **過去の記録を追加**を使用し、説明を入力します。
- **注意領域**で皮膚所見を記録します。回復を確認したら、**皮膚所見 → 完全回復を確認**から評価を入力して保存します。

回復を保存すると、その注意領域による制限は直ちに解除されます。反復所見による追加の再評価待ちはありません。ただし、別の注意領域・休止期間・距離・写真の条件は引き続き適用されます。条件を満たした部位は番号順の候補に直ちに戻ります。

### 5. 日時・予約・管理

- **予約カレンダー：** 次回予定を確認し、**確認・変更**で予約を確定・変更します。通常の提案日時は、対象となる最後の穿刺から72時間後です。
- **日時を変更（管理者）：** デモ日時または **システム日時を使用**を選び、**日時を適用**します。日時は全患者・全画面で共通となり、選択後も時計は進みます。業務日時は日本時間で表示します。
- **プロフィール → 患者を削除…（管理者）：** 内容を確認し、患者IDを正確に入力して **完全に削除**します。アプリ内では元に戻せません。監査記録と既存のバックアップは残ります。
- **設定・データ → 完全バックアップを取得（管理者）：** データベースと写真をまとめて保存します。患者の **CSV** は完全なバックアップではありません。
- 保存を終え、必要に応じてログアウトした後、サーバーのターミナルで **Ctrl+C** を押します。ブラウザーを閉じるだけではサーバーは停止しません。

**操作できない場合：** 最新の写真を使用し、位置確認と表示された制限を確認してください。新しい穿刺の記録には、アプリの日時から24時間以内の写真が必要です。記録に使用して固定された写真は、新しい写真を追加して位置合わせします。

本アプリはデモ用の試作版です。架空・匿名化データを使用してください。緑色や写真の距離表示は、臨床上の適否を保証しません。
