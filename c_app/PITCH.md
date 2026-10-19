# One-minute pitch

Target: about 60 s spoken (about 150 words). Current wood v3 definitions: knock
is a knuckle knock on the board; rub is a **fingernail edge scratched back and
forth on bare wood**. Do not quote accuracy numbers until the 20 trials in
TEST_PROTOCOL.md have been run.

## English

Hi everyone. We turned a plain wooden board into a slide clicker, using a single
piezo contact microphone.

The piezo is taped to a thirty-centimetre board and plugged into a USB audio
interface. Every fifty milliseconds, the laptop computes a frequency spectrum.
An energy gate ignores quiet moments, and a linear SVM decides between three
labels: neutral, knock, and rub.

Knock once with a knuckle, and the slides go forward. "Rub" means scratching the
bare wood back and forth with the edge of a fingernail, and that goes back one
slide.

Everything else should stay neutral. The model's label is sent to our slide app.
To reduce repeated page turns, the app only re-triggers after it has seen a
steady neutral, and it adds a short cooldown. That rule only controls the
slides; it doesn't change what the model recognizes.

Let us show you.

## 中文翻译

大家好。我们只用一个压电接触式麦克风，就把一块普通的木板变成了翻页器。

压电片贴在一块 30 厘米的木板上，接到 USB 声卡。笔记本每 50 毫秒算一次频谱。
能量门限会忽略安静的时刻，再由线性 SVM 从三个标签里选一个：neutral（无动作）、
knock（敲击）、rub（刮擦）。

用指关节敲一下，幻灯片就往前翻一页。“rub” 指的是用指甲边缘在裸木板上来回刮，
这样会往回翻一页。

其他动作都应该识别为 neutral。模型的标签会发送给我们的翻页程序。为了减少重复
翻页，程序要先确认稳定的 neutral 才会重新触发，并加了一个短暂的冷却时间。这条
规则只控制翻页，不会改变模型识别的结果。

下面请看演示。

## Speaker notes

- Do not quote the 96% (72/75) figure as live accuracy. It is a model-selection
  cross-validation result on whole two-second takes, and those takes were
  classified with offline event averaging. The live GUI uses per-window
  predictions instead (see `MODEL_NOTES.md`).
- During the demo, scratch the bare wood with a fingernail edge. Keep your hand
  away from the pickup, its tape and the cable.
- Do not promise "one action never turns two pages". The re-arm and cooldown
  rule reduces repeats; it cannot fix a wrong or late label from the model.
- If a page turn does not happen live, hold still for about a second so the slide
  app sees a confirmed neutral, then repeat the action once. Do not knock repeatedly.
