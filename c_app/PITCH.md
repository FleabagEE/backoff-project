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

Everything else should stay neutral. The backend confirms each action once and
sends it to our slide app, which turns exactly one page per message. The slide
app makes no decisions of its own; it only executes what the model side decided.

Let us show you.

## 中文翻译

大家好。我们只用一个压电接触式麦克风，就把一块普通的木板变成了翻页器。

压电片贴在一块 30 厘米的木板上，接到 USB 声卡。笔记本每 50 毫秒算一次频谱。
能量门限会忽略安静的时刻，再由线性 SVM 从三个标签里选一个：neutral（无动作）、
knock（敲击）、rub（刮擦）。

用指关节敲一下，幻灯片就往前翻一页。“rub” 指的是用指甲边缘在裸木板上来回刮，
这样会往回翻一页。

其他动作都应该识别为 neutral。后端确认一次动作后，只发送一条消息给我们的翻页
程序，程序收到一条就翻一页。翻页程序自己不做判断，只执行模型侧的最终结果。

下面请看演示。

## Speaker notes

- Do not quote the 96% (72/75) figure as live accuracy. It is a model-selection
  cross-validation result on whole two-second takes, and those takes were
  classified with offline event averaging. The live GUI uses per-window
  predictions instead (see `MODEL_NOTES.md`).
- During the demo, scratch the bare wood with a fingernail edge. Keep your hand
  away from the pickup, its tape and the cable.
- Do not promise "one action never turns two pages". The slide app executes
  every action message it receives; whether one physical action becomes exactly
  one message is decided on the model side, not in the slide app.
- The live demo relies on the GUI's default event decision (`--decision event`,
  B's `EventDecoder`): one message per decided action. Never start the GUI with
  `--decision window` or load a model through the Load Model dialog for the demo;
  in that per-window mode every label change turns a page.
- If a page turn does not happen live, wait a moment and repeat the action once.
  Do not knock repeatedly: every confirmed knock is one more page.
