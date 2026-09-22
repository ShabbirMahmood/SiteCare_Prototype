# Patient Options And Records

Updated: 23 September 2026. All dates in the interface use Japan Standard Time and the application clock.

## Draw Alert / 注意領域

1. Open a patient’s latest verified photo and choose **Draw Alert**. Click the centre of the spot.
   最新の確認済み写真で **注意領域** を選び、部位の中心をクリックします。
2. Enter **Width: Horizontal X Axis (cm)** and **Height: Vertical Y Axis (cm)**. Both start at **0.30 cm**. These are full diameters, not radii.
   **幅：水平X軸（cm）** と **高さ：垂直Y軸（cm）** を入力します。初期値は各 **0.30 cm** です。半径ではなく直径全体です。
3. Changing width also changes height until you explicitly edit height. Equal dimensions draw a circle; different dimensions draw an ellipse. The preview shows the result.
   高さを個別に編集するまでは幅の変更に高さも連動します。同じ値なら円、異なる値なら楕円になります。プレビューで確認できます。
4. Alternatively, choose the blue **Draw Spot** button. Drag from one corner of the area to the opposite corner on the photo. SiteCare measures the enclosing width and height and returns to the form. Selected observations and notes are retained.
   青い **マウスで描画** を選ぶと、写真上で領域を囲む角から反対の角までドラッグできます。幅・高さを自動計算してフォームに戻ります。選択した所見とメモは保持されます。
5. Select the observations, severity and actual observation time, then **Save Alert**. **Pain** and **Tenderness** are separate options.
   所見・程度・実際の観察日時を入力し、**注意領域を保存** を選びます。**痛み** と **圧痛** は別々に選択できます。

Measurements use the saved calibration and the patient coordinate plane. The ellipse is aligned with the map’s X/Y axes. An alert blocks points inside the actual ellipse; it is not screened as a larger enclosing circle. **Confirm Full Recovery** removes that alert’s restriction immediately. Rest and other alerts can still apply.

測定は保存された校正と患者座標を使用します。楕円の向きはマップのX/Y軸に一致します。制限判定は楕円の内側を使用し、外接円では判定しません。**完全回復を確認** を保存すると、その領域の制限を直ちに解除します。休止期間や他の所見による制限は残る場合があります。

## Drug Dosage / 投与速度

The toolbar order is **Calibrate → Drug Dosage → Appointment → Exact Point**.

ツールバーの順序は **校正 → 投与速度 → 予約 → 実際の点** です。

1. Choose **Drug Dosage**. Select exactly one category: **Higher**, **Standard**, or **Lower**.
   **投与速度** を開き、**高用量・標準・低用量** のいずれか1つを選択します。
2. The initial rate is **0.15 mL/h**, and the initial step is **0.01 mL/h**. Type values directly or use **− / +** with the selected step.
   初期速度は **0.15 mL/h**、初期増減幅は **0.01 mL/h** です。直接入力、または **− / +** で変更できます。
3. The comparison is **Increased** (bold blue), **Decreased** (bold yellow), or **Unchanged** (bold green). A reason is required for an increase or decrease.
   前回との比較を **増量（青）・減量（黄）・変更なし（緑）** の太字で表示します。増減時は理由が必要です。
4. **Save Dosage Preset** saves the patient’s next-entry setting. This alone does not create a dosage record or chart point.
   **投与速度設定を保存** は患者の次回入力設定を保存します。この操作だけでは穿刺記録やグラフの点は作成しません。
5. **Record Completed Puncture** displays the preset category, rate, comparison and reason. Confirm patient identity with the single checkbox and save the completed puncture.
   **実施済みの穿刺を記録** に設定した区分・速度・増減・理由を表示します。本人確認のチェック1項目を確認して保存します。
6. The saved rate and category become the next default for that patient. Other patients’ settings are independent. A historical entry older than the latest record does not replace the current default.
   保存した速度・区分がその患者の次回初期値になります。他の患者の設定は変わりません。最新記録より古い過去記録を追加しても、現在の初期値は置き換わりません。

The category is a user-entered label; it does not automatically determine a rate. No medication concentration or infusion duration is stored, so mL/h is a **flow rate**, not delivered volume or drug mass.

区分は利用者が選ぶラベルで、投与速度を自動決定するものではありません。薬剤濃度や投与継続時間は保存していないため、mL/hは **流量・投与速度** であり、投与済み液量や薬剤重量ではありません。

## Appointment / 予約

- **Count Days:** enter a whole number of days, initially **3**. The next appointment is that many days after the latest applicable puncture, at the same time of day.
  **日数で指定：** 初期値 **3日** を変更できます。最後の対象穿刺から指定日数後の同時刻を次回予定にします。
- **Assign Days From Week:** select one or more weekdays. The next appointment is the nearest selected weekday **after** the puncture’s calendar day, at the same Japan time.
  **曜日で指定：** 曜日を複数選択できます。穿刺日の翌日以降で最も近い選択曜日の同時刻を次回予定にします。
- Only one method is enabled at a time. Before the first puncture, the initial appointment entered when creating the patient is the anchor; weekday mode moves it forward to an allowed weekday if necessary.
  方法は同時に1つだけ有効です。初回穿刺前は患者登録時の初回予定日が基準となり、曜日指定では必要に応じて次の選択曜日に進めます。
- Saving a rule recalculates the next suggestion and replaces its previous confirmation. **Appointments** shows one next visit per active patient, plus completed punctures. It does not create recurring forecasts.
  設定を保存すると次回提案を再計算し、以前の確定予約を置き換えます。カレンダーには管理中患者の次回1件と実施済み穿刺を表示し、繰り返し予測は作成しません。

## Patient Record / 患者記録

Open **Patient Record** in the left navigation, search by patient ID or name, and choose **Open Record**.

左の **患者記録** で患者ID・名前を検索し、**記録を開く** を選びます。

| View | X Axis | Y Axis |
| --- | --- | --- |
| **Month View** (default) / 月表示（初期設定） | Each puncture date / 各穿刺日 | That puncture’s recorded rate, mL/h / その穿刺の記録速度 |
| **Year View** / 年表示 | Months with records / 記録のある月 | Arithmetic mean of recorded rates in each month / 月内記録速度の算術平均 |
| **Total View** / 全期間 | Years with records / 記録のある年 | Arithmetic mean of recorded rates in each year / 年内記録速度の算術平均 |

Values are printed above graph points, with numerical tables below. Choose a site from 1–14 to filter its trend; the site summary lists all 14 sites. Missing older dosage values are shown as **Not Recorded** and excluded from averages. Zero, if explicitly entered, is a recorded value. These averages are not time-weighted and do not estimate delivered volume.

点の上に数値を表示し、下に表も表示します。部位1～14を選ぶと、その部位の推移を確認できます。部位別集計には全14部位を表示します。過去の投与速度が不明な記録は **未記録** と表示して平均から除外します。明示的に入力したゼロは記録値として扱います。時間加重平均や投与済み液量の推定ではありません。

### Trouble Locations / 皮膚の問題部位

The histogram uses the selected month, year or total period and always displays sites 1–14. Each saved skin episode counts once at its nearest numbered site. Recovered episodes remain counted; deleted entries are excluded. This counts observations, not blocked days, rest periods, or every neighbouring site touched by an ellipse.

選択した月・年・全期間について、全14部位の件数を表示します。各所見は最も近い番号の部位で1件と数えます。回復済みも含み、削除済みは除外します。所見の記録件数であり、使用制限日数、休止期間、楕円に接するすべての隣接部位の件数ではありません。

### Photo History / 写真履歴

Select a historical date/time and a photo, then choose **Show Historical Photo**. The default photo is the latest upload captured by that time. Red regions represent alerts observed by the selected time and not yet recovered/deleted then. The image uses its own saved alignment and site layout. Current corrected facts are used; correction history retains original values. The gallery keeps all retained uploads available. **Source Photo** links each puncture or alert to its photograph.

日時と写真を選び、**履歴写真を表示** を押します。初期選択はその日時までに撮影された最新のアップロード写真です。赤い領域はその日時に観察済みで、回復・削除前の所見です。各写真の保存済み位置合わせと配置を使用します。修正後の記録に基づいて表示し、修正前の値は修正履歴に残します。保持されている全写真をギャラリーで確認でき、**記録写真** から個別記録の元画像を開けます。

### Manage Records / 記録管理

Administrators can **Edit** a puncture or skin observation and enter a correction reason. Before/after values, actor and time are saved. **Delete** removes an individual record from active screening/reports while preserving it under **Include Deleted Entries**. To add records, open the patient workspace and use completed or historical record entry. Referenced photos remain protected; an administrator may delete an unused photo. Permanent patient deletion remains in **Profile**.

管理者は穿刺・皮膚所見を **編集** し、修正理由を入力できます。変更前後の値・変更者・日時を保存します。個別記録の **削除** は現在の判定・集計から除外し、**削除済みを含める** で確認できます。新規・過去記録の追加は患者画面で行います。記録に紐づく写真は保護し、未使用写真は管理者が削除できます。患者全体の完全削除は **プロフィール** にあります。

### Calibration And Nurse Accounts / 校正と看護師アカウント

**Keep Calibration** is enabled by default and available to nurses and administrators. It is shared across the installation. Turning it off immediately restores the 24-hour photo limit. New photos always require their own calibration. **Settings & Data → Nurse Accounts → Delete Nurse** lets administrators remove a nurse’s login and active sessions; the nurse’s existing signed records remain.

**校正を保持** は初期設定でオンとなり、看護師と管理者が操作できます。設定はこの環境全体で共有します。オフにすると24時間の有効期限が直ちに適用されます。新しい写真は必ず個別に校正します。管理者は **設定・データ → 記録者アカウント → 看護師を削除** からログインとセッションを削除できます。既存の記録者名付き記録は残ります。

See [Data Storage And Retention Policy](DATA_POLICY.md) for backups, access, corrections and permanent deletion.
