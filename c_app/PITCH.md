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
That app turns at most one page per action. It waits for neutral again and adds a
short cooldown, so one long scratch never skips several pages. That rule only
controls the slides; it doesn't change what the model recognizes.

Let us show you.

## 中文翻译

大家好。我们只用一个压电接触式麦克风，就把一块普通的木板变成了翻页器。

压电片贴在一块 30 厘米的木板上，接到 USB 声卡。笔记本每 50 毫秒算一次频谱。
能量门限会忽略安静的时刻，再由线性 SVM 从三个标签里选一个：neutral（无动作）、
knock（敲击）、rub（刮擦）。

用指关节敲一下，幻灯片就往前翻一页。“rub” 指的是用指甲边缘在裸木板上来回刮，
这样会往回翻一页。

其他动作都应该识别为 neutral。模型的标签会发送给我们的翻页程序。这个程序每次
动作最多翻一页：必须先回到 neutral 才能再触发，还有一个短暂的冷却时间，所以
一次长时间的刮擦不会连跳好几页。这条规则只控制翻页，不会改变模型识别的结果。

下面请看演示。

## Speaker notes

- Do not quote the 96% (72/75) figure as live accuracy. It is a model-selection
  cross-validation result on whole two-second takes, and those takes were
  classified with offline event averaging. The live GUI uses per-window
  predictions instead (see `MODEL_NOTES.md`).
- During the demo, scratch the bare wood with a fingernail edge. Keep your hand
  away from the pickup, its tape and the cable.
- If a page turn does not happen live, pause for a second so the label returns
  to neutral, then repeat the action once. Do not knock repeatedly.
