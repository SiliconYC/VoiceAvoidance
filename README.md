# VoiceAvoidance/ 人声回避
Take a piece of vocal audio and a piece of background music (BGM), it can temporarily reduce the volume of the BGM while the person is speaking. 
任取一段人声+一段 bgm，它可以让 bgm 音量在人说话的时候暂时变小。

## Basic explanation:
The program will scan the entire audio by default at intervals of 0.02 seconds. (Downsampling mode)
The scanning results will be binarized - True for loudness above the threshold, False for loudness below the threshold.
If all scanning results within a continuous 2-second interval are False, then it is considered a silent segment. Setting such a threshold is to avoid too frequent changes in volume.
Background music will be temporarily enhanced within the silent segment, with a fade-in and fade-out effect.
By default, the program generates a mixed audio file called "final.wav" in the root directory.

## 基本说明：
程序会默认以 0.02 秒为间隔，扫描整个音频。（下采样模式）
扫描结果将被二值化——音强超过阈值的为 True, 音强低于阈值的为 False.
如果连续 2 秒内所有的扫描结果都是 False, 则视为静音片段。设置这样的门槛，是为了避免音量变化过于频繁。
静音片段内背景音乐将被暂时增强，增强时有淡入淡出效果。
默认情况下，程序运行结果是在根目录中生成一个叫做 "final.wav" 的混音文件。

## Copyright Notice
All code within this repository has been written by me. You are free to use, modify, and distribute it, including for commercial purposes.
Regarding giving credit, let's cut the bullshit. I seriously doubt you would adhere to such a practice, so let's just not require it at all.
As for the contribution, I've only open-sourced three hundred lines of code, which is a minuscule contribution indeed. I did it for my amusement; there's no need for you to take it to heart.

## 版权说明
本仓库内的所有代码均由本人撰写，你可以自由地使用、修改和分发，包括商用。
至于分发和使用时是否要署名？我知道我要求了你也做不到，所以干脆不要求。才开源了三百行代码，实在是太过微小的贡献。我就图一乐，你没必要往心里去。
