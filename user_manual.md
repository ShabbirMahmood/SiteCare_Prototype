# SiteCare User Manual / 操作マニュアル

[Setup Instructions](setup_instruction.md) · [Project Overview](README.md) · [Detailed Bilingual Patient Options Guide](docs/PATIENT_RECORDS.md) · [Storage Policy](docs/DATA_POLICY.md)

Updated: 23 September 2026 / 更新日：2026年9月23日

## English

### 1. Open and sign in

Start SiteCare and open [http://127.0.0.1:8000](http://127.0.0.1:8000/). Sign in with your account. Use **日本語 / EN** to change the language. For a fresh installation, create an administrator account first.

### 2. Open a patient and prepare the photo

1. Choose **Patients → Create Patient**, or open an existing patient.
2. Choose **New Visit Photo** and upload a JPEG/PNG with the correct capture time. Include the navel and a measured ruler.
3. Use **Navel**, **Move Photo**, **Photo Size**, and **Photo Rotation** to align the photo.
4. Use **Calibrate**: select two ruler marks and enter their actual distance in cm.
5. Complete **Verify & Save Alignment**. Each new photo needs calibration and verification.

The photo selector counts uploads separately for each patient: **#1 → #2 → #3**. Switching photos displays the saved layout of that image. A high number previously shown by the application was its shared database ID, not the patient’s visit count.

For practice, an administrator can use **Load Demo** or **Settings & Data → Load / Open Demo**. Upload `samples/synthetic_abdomen.jpg` as a new visit photo to practice alignment; its ruler has a 10 cm reference.

### 3. Edit the numbered layout

For **each new photo**, choose **Edit Sites** and drag the circles before recording a puncture or skin observation on that photo. Earlier records for the same patient do not prevent editing the new image. Keep centres at least 5 cm from the navel and 2.5 cm apart.

| Button | Action |
| --- | --- |
| **Verify & Save Alignment** — green | Save the ruler calibration and verified photo alignment. |
| **Save Site Layout** — red | Save the dragged positions. |
| **Default Layout** — blue | Immediately restore and save all original positions; retain photo-alignment edits. |
| **Discard Changes** — yellow | Return to the last saved layout and alignment. It does not undo an already saved reset. |

Layout changes and photo alignment are saved separately. All four controls remain visible when a photo is selected. A photo used in a saved record becomes read-only, preserving its layout and alignment. Uploading another photo enables editing again; it starts with the applicable saved layout. Use **Default Layout** if you want the original template instead. **Discard Changes** clears unsaved edits on the selected image.

### 4. Review and record

- Select a numbered site, candidate, or **Site Status** row to see its details.
- **Green:** eligible. **Blue:** resting. **Red:** blocked. **Gray:** photo verification needed.
- Use **Exact Point** to select the actual location, then **Record Completed Puncture** with its actual time, preset dosage and the patient-identity confirmation.
- Use **Add Historical Record** for an older completed procedure; provide an explanation.
- Use **Draw Alert** to mark a skin concern. In **Skin Alerts**, choose **Confirm Full Recovery**, enter the assessment, and save when recovery has been confirmed.

Recovery clears that alert immediately. No additional recurring-episode review is required. Other active alerts, rest, spacing, and photo checks can still exclude the site. Eligible sites rejoin the numbered candidate order immediately.

### 5. Keep Calibration — nurses and administrators

Nurses and administrators can use **Keep Calibration** at the top of the page. It is enabled by default. The setting is shared by all patients and users and is remembered after restarting SiteCare.

- **Unchecked:** a photo older than 24 hours at the application date cannot be used for new screening/records. Upload a new photo, calibrate with the ruler, and verify alignment. A photo already used for a non-voided procedure also requires a new visit photo in this mode.
- **Checked (default):** continue using the latest calibrated and verified photo after 24 hours, including for later procedures. You do not need to upload or recalibrate just because time has passed.
- **Unchecked again:** the 24-hour limit applies immediately, measured from the original capture time. This does not give the old photo another 24 hours, erase its calibration, or delete records.
- **Whenever you upload another photo:** calibrate and verify that new image. This option does not transfer calibration from one image to another or unlock an image already used by records.

Example: verify a photo on 20 September, then change the demonstration date to 23 September. With the checkbox off, prepare a new photo. With it on, the saved photo remains available, while rest periods and skin alerts still determine candidate sites. A photo captured after the chosen demonstration time cannot be used as the current photo.

Other open windows pick up the setting automatically. If you have an open form or unsaved edits, finish or discard them and use **Refresh View** before continuing.

### 6. Dates, appointments, and administration

- **Appointments:** review suggested visits and use **Confirm / Change** to confirm a time. Use the workspace **Appointment** button to choose Count Days (default 3) or selected weekdays. Only the next appointment is suggested; the two methods are exclusive.
- **Change Date** (administrator): choose a demonstration date or **Use System Date**, then **Apply Date**. The selected clock is shared across patients and windows and continues running. All workflow dates use JST.
- **Profile → Delete Patient…** (administrator): review the summary, type the exact patient ID, and choose **Delete Permanently**. There is no in-app undo; audit history and previous backups remain.
- **Settings & Data → Download Complete Backup** (administrator): save a database-and-photos backup. Patient **CSV** export is not a full backup.
- Finish saving, sign out if needed, and press **Ctrl+C** in the server terminal to stop. Closing the browser alone does not stop the server.

**If a control is unavailable:** use the latest photo, verify alignment, and resolve the stated restriction. When Keep Calibration is off, a new-procedure photo must be within 24 hours of the application clock. Upload a new photo when a saved record has locked the old photo's alignment.

### 7. Dosage, Alert Dimensions And Patient Record

- **Drug Dosage:** select Higher, Standard or Lower; set the rate (initially 0.15 mL/h) and +/- step (initially 0.01 mL/h). Changes require a reason. Blue means Increased, yellow Decreased, green Unchanged. A saved puncture records the preset and makes it the next patient default.
- **Draw Alert:** click the centre. Width and height start at 0.30 cm; height follows width until explicitly edited. Blue **Draw Spot** measures an ellipse from a dragged bounding box. Pain and Tenderness are separate.
- **Patient Record:** search and open a patient. Month View shows each recorded flow rate; Year/Total views show monthly/yearly averages in mL/h. Choose any of the 14 sites, review tables and trouble counts, or select a photo date in Photo History.
- **Manage Records:** administrators can edit or delete individual records with a reason. Deleted entries remain available with Include Deleted Entries, and corrections retain before/after values. Only unused photos can be separately removed. Add new/historical records from the patient workspace.
- **Settings & Data → Nurse Accounts → Delete Nurse:** administrators can delete a nurse's login and sessions while keeping their signed records.

See the [bilingual step-by-step guide](docs/PATIENT_RECORDS.md) and [storage policy](docs/DATA_POLICY.md) for report meanings, retention and backups. Flow rates are not delivered liquid volumes.

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

写真履歴の番号は患者ごとに **#1 → #2 → #3** と追加順に表示されます。写真を切り替えると、その写真に保存された配置が表示されます。以前の大きな番号は全患者共通のデータベースIDで、患者の訪問回数ではありません。

練習用データは、管理者が **デモを読み込む**、または **設定・データ → デモを読み込む・開く** から追加できます。位置合わせの練習には `samples/synthetic_abdomen.jpg` を新しい写真として追加します。図内の定規には 10 cm の基準があります。

### 3. 14部位の配置変更

**新しい写真ごとに**、その写真で穿刺記録・皮膚所見を追加する前なら、**14部位調整**で番号の円をドラッグできます。同じ患者に以前の記録があっても、新しい写真は編集できます。臍から5cm以上、部位の中心間は2.5cm以上を確保します。

| ボタン | 操作 |
| --- | --- |
| **確認して位置を保存** — 緑 | 定規の校正と写真の位置確認を保存します。 |
| **14部位配置を保存** — 赤 | 調整した配置を保存します。 |
| **標準配置** — 青 | 元の14部位配置に戻して直ちに保存します。写真の位置合わせ編集は保持されます。 |
| **変更を破棄** — 黄 | 最後に保存した配置と位置合わせに戻します。保存済みのリセットは取り消しません。 |

部位配置と写真の位置合わせは別々に保存します。写真を選択中は4つのボタンが表示されます。記録に使用した写真の配置と位置合わせは固定されますが、新しい写真を追加すると再び編集できます。新しい写真は対象となる保存済み配置を引き継ぎます。元の配置から始めたい場合は **標準配置** を使用します。**変更を破棄** は選択中の写真の未保存編集を破棄します。

### 4. 確認と記録

- 写真の番号、候補、または **部位状態**の行を選ぶと詳細を確認できます。
- **緑：条件適合／青：休止中／赤：使用不可／灰：写真確認待ち**です。
- **実際の点**で位置を選び、**実施済みの穿刺を記録**で実際の日時と確認事項を入力します。
- 古い実施記録には **過去の記録を追加**を使用し、説明を入力します。
- **注意領域**で皮膚所見を記録します。回復を確認したら、**皮膚所見 → 完全回復を確認**から評価を入力して保存します。

回復を保存すると、その注意領域による制限は直ちに解除されます。反復所見による追加の再評価待ちはありません。ただし、別の注意領域・休止期間・距離・写真の条件は引き続き適用されます。条件を満たした部位は番号順の候補に直ちに戻ります。

### 5. 校正を保持 — 看護師・管理者

看護師と管理者は画面上部の **校正を保持** を使用できます。初期設定はオンです。設定は全患者・全ユーザーで共通となり、再起動後も保存されます。

- **オフ：** アプリ日時から撮影後24時間を超えた写真は、新しい確認・記録に使用できません。新しい写真を追加し、定規で校正して位置確認を保存します。取消されていない実施記録に使用済みの写真にも、新しい訪問写真が必要です。
- **オン（初期設定）：** 最新の校正・位置確認済み写真を、24時間後や次回の実施記録にも使用できます。時間が経過したことだけを理由に再撮影・再校正する必要はありません。
- **再びオフ：** 元の撮影日時から計算する24時間の制限が直ちに適用されます。有効期限が24時間延長されるわけではありません。校正や過去の記録は削除されません。
- **新しい写真を追加した場合：** オン・オフにかかわらず、その写真の校正と位置確認が必要です。別の画像に校正をコピーしたり、記録済み写真の固定を解除したりする機能ではありません。

例：9月20日に写真を確認し、デモ日時を9月23日に進めます。オフなら新しい写真を準備し、オンなら保存済み写真を再利用できます。部位の休止期間・皮膚所見などの確認は引き続き適用されます。選択したデモ日時より未来の写真は現在の写真として使用できません。

他の画面にも設定が反映されます。入力中のフォームや未保存の編集がある場合は、保存または破棄した後、**表示を更新**して続けてください。

### 6. 日時・予約・管理

- **予約カレンダー：** 次回予定を確認し、**確認・変更**で予約を確定・変更します。患者画面の **予約** で日数（初期値3日）または曜日を選びます。方法は1つだけ有効で、次回1件のみを提案します。
- **日時を変更（管理者）：** デモ日時または **システム日時を使用**を選び、**日時を適用**します。日時は全患者・全画面で共通となり、選択後も時計は進みます。業務日時は日本時間で表示します。
- **プロフィール → 患者を削除…（管理者）：** 内容を確認し、患者IDを正確に入力して **完全に削除**します。アプリ内では元に戻せません。監査記録と既存のバックアップは残ります。
- **設定・データ → 完全バックアップを取得（管理者）：** データベースと写真をまとめて保存します。患者の **CSV** は完全なバックアップではありません。
- 保存を終え、必要に応じてログアウトした後、サーバーのターミナルで **Ctrl+C** を押します。ブラウザーを閉じるだけではサーバーは停止しません。

**操作できない場合：** 最新の写真を使用し、位置確認と表示された制限を確認してください。「校正を保持」がオフの場合、新しい穿刺の記録にはアプリの日時から24時間以内の写真が必要です。記録に使用して固定された写真は、新しい写真を追加して位置合わせします。

本アプリはデモ用の試作版です。架空・匿名化データを使用してください。緑色や写真の距離表示は、臨床上の適否を保証しません。


### 7. 投与速度・領域寸法・患者記録

- **投与速度：** 高用量・標準・低用量から1つを選び、速度（初期値0.15 mL/h）と増減幅（初期値0.01 mL/h）を設定します。増減には理由が必要です。青は増量、黄は減量、緑は変更なしです。穿刺を保存すると患者の次回初期値になります。
- **注意領域：** 中心をクリックして幅・高さ（初期値各0.30 cm）を入力します。高さを個別編集するまでは幅に連動します。青い **マウスで描画** で範囲をドラッグして楕円を測定できます。痛み・圧痛は別々に選択できます。
- **患者記録：** 患者を検索して開きます。月表示は各穿刺の速度、年・全期間表示は月・年の平均（mL/h）です。全14部位から選択し、表・所見件数・日時別写真も確認できます。投与済み液量ではありません。
- **記録管理：** 管理者は理由付きで個別記録を編集・削除できます。削除済みを含めると元の記録も確認できます。修正前後の値は保持します。写真を個別削除できるのは未使用の場合です。新規・過去の記録は患者画面で追加します。
- **設定・データ → 記録者アカウント → 看護師を削除：** 管理者がログインとセッションを削除できます。既存の記録者名付き記録は残ります。

詳しい操作は [日英の機能ガイド](docs/PATIENT_RECORDS.md)、保存と削除は [データ管理方針](docs/DATA_POLICY.md) を参照してください。
