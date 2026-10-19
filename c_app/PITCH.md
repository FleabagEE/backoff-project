# One-minute pitch

Target: about 60 s spoken (about 150 words). Current v2 definitions: knock is a
knuckle knock, and rub is a **fingernail scratch on a paper pad**. Do not add
accuracy numbers until the 20 trials in TEST_PROTOCOL.md have been run.

## English

Hi everyone. We turned an ordinary board into a slide clicker, using a single
piezo contact microphone.

The piezo is taped to the board and plugged into a USB audio interface. Every
fifty milliseconds the laptop computes a 1,200-bin spectrum. A linear SVM, behind
an energy gate and label smoothing, decides between three labels: neutral, knock,
and rub.

Knock with a knuckle on the knock pad, and the slides go forward. "Rub" means
scratching back and forth with a fingernail on a small paper pad, and that goes
back one slide. We switched from fingertip rubbing to nail scratching because the
scratch gives a much more consistent vibration signal.

Everything else, like talking, typing or slapping the table, should stay neutral.
The slide app turns exactly one page per action: it waits for neutral again and
adds a short cooldown, so a long scratch never skips pages.

Let us show you.

## 中文翻译

大家好。我们只用一个压电接触式麦克风，就把一块普通的木板变成了翻页器。

压电片贴在木板上，接到 USB 声卡。笔记本每 50 毫秒算一次 1200 个频点的频谱，
再由线性 SVM 加上能量门限和标签平滑，从三个标签里选一个：neutral（无动作）、
knock（敲击）、rub（刮擦）。

用指关节敲一下敲击垫，幻灯片就往前翻一页。“rub” 指的是用指甲在一小块纸片上
来回刮，这样会往回翻一页。我们把原来的“指腹摩擦”换成了“指甲刮纸”，因为
刮纸产生的振动信号稳定得多。

其他动作，比如说话、打字、拍桌子，都应该识别为 neutral。翻页程序保证一次
动作只翻一页：必须先回到 neutral 才能再触发，并且有一个短暂的冷却时间，所以
长时间刮擦也不会连续跳页。

下面请看演示。

## Speaker notes

- Only say "much more consistent" about the scratch signal. It comes from the
  feasibility run in `docs/scratch_v2.md`: 98.5–100 % of windows were above the
  quiet P95, compared with 73 % for fingertip rubbing. That is a signal-level
  result, not classifier accuracy.
- During the demo, keep your hand away from the red pickup and its cable.
- If a page turn fails live, say "neutral re-arm": pause for a second, then
  repeat the action once. Do not knock repeatedly.
