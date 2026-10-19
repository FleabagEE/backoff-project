# C 同學：木板 v3 模型與即時推論交接

更新：2026-10-19（America/Los_Angeles）。工作分支是 **a-tuning**；
B 的 `model-training` 分支沒有修改。請先閱讀本文件，再看根目錄
[`MODEL_NOTES.md`](../MODEL_NOTES.md) 的完整結果與限制。

## 取得與執行

在自己的 clone 執行；若目前有未提交工作，先保留工作再切換分支：

```powershell
git fetch origin
git switch a-tuning
git pull --ff-only origin a-tuning
uv sync
uv run visualizer.py --setup-id A_wood30x30x6_v3_candidate2 --scratch-surface wood --trained-model a_models/wood_v3_20261019_135608_v1/model.joblib --decision-params a_models/wood_v3_20261019_135608_v1/decision_params.json
```

需要 A 的相同硬體設定與 USB Audio CODEC 輸入；啟動後自動進入 Infer，
顯示 `Prediction: neutral / knock / rub`，不會自動錄音。
不要另外套用舊的 RMS/peak gate 或重做一次 log1p/scaler。

## 檔案放置

| 用途 | 路徑 |
|---|---|
| 配對模型與參數、訓練報告 | `a_models/wood_v3_20261019_135608_v1/` |
| 模型載入與能量 gate | `wood_v3_model.py` |
| 即時 GUI | `visualizer.py` |
| 訓練與交叉驗證程式 | `train_wood_v3.py` |
| 最新實測證據與限制 | `docs/WOOD_V3_REALTIME_CHECK.md` |
| A 的交接狀態 | `docs/STATUS_FOR_CLAUDE.md` |

模型與 JSON 必須一起更換，載入器會核對 SHA256。輸入是原流程的 1200 維
特徵；class order 為 neutral=0、knock=1、rub=2。`rub` 是指甲邊緣刮裸木板。
`predict_windows(X)` 執行逐視窗預測與 gate；`predict_take(X, elapsed_s)`
執行離線事件彙整。GUI 目前用前者，尚無經試驗調整的平滑／冷卻層。

## 已完成與待驗證

75 筆兩秒錄音，每類 25 筆；neutral 全是安靜。舊資料全部排除。
五折 take 分組模型選擇得到 72/75（96%）事件彙整分類；不是現場成功率。
A 已回報敲擊、刮擦及手掌干擾的基本即時辨識成功，另有一筆保存的手掌
測試回放全部 42 視窗為 neutral。完整獨立 holdout、多種干擾與延遲測試、
平滑／冷卻調整仍待完成。不要把少量人工觀察當成正式驗收通過。

41 項單元測試通過。C 可以直接整合現成模型，無須先重新訓練。
原始 NPZ 與資料 ZIP 不進 Git。A 本機有
`packages/A_wood_final_v3_20261019_135608_v1.zip`（約 14.2 MB），含訓練資料
與模型；如需重訓資料，須由 A 另外傳檔，尚無雲端下載連結。
