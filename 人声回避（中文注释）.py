from pydub import AudioSegment

'''
基本说明：
程序会默认以 0.02 秒为间隔，扫描整个音频。（下采样模式）
扫描结果将被二值化——音强超过阈值的为 True, 音强低于阈值的为 False.
如果连续 2 秒内所有的扫描结果都是 False, 则视为静音片段。设置这样的门槛，是为了避免音量变化过于频繁。
静音片段内背景音乐将被暂时增强，增强时有淡入淡出效果。
默认情况下，程序运行结果是在根目录中生成一个叫做 "final.wav" 的混音文件。
'''

'''
操作提示：
1. 
以上提到的所有参数都可以设置，但默认值大多数情况下可以应付使用。
只有 loud_level 和 quiet_level 需要针对每首歌设置，因为不同歌曲的平均音量差别很大。详见下文。
2. 
以 "Debug:..." 开头的 print 都可以删除，不影响功能。
3. 
一定要注意输入输出的音频格式，默认 bgm 为 MP3, 原始口播语音和输出混音为 WAV. 
如有改动请务必设置好 AudioSegment 相关格式。
4. 
tspan 意为 time_span, 是为了避免和 AudioSegment 的 duration 冲突而设置的新造单词。
'''


##############################################################################
# 定义变量
##############################################################################

# 在原始语音文件的头尾插入静音片段，这些静音长度理论上会被 bgm 填满（单位：秒）
speech_audio_opening_silence = 4
speech_audio_closing_silence = 3
# 结尾 bgm 会自动淡出到零，这是淡出所经历的时长（单位：秒）
fade_out_tspan_at_the_end = 1.5  

# 人声回避的微观参数（时间单位：毫秒）
downsampling_interval_in_ms = 20  # 下采样周期间隔，默认 20 毫秒
loudness_threshold = -20  # 定义音强门槛，低于这个值会被视为静音
silent_interval_tspan_threshold_in_ms = 2000  # 执行淡入淡出的静音间隔门槛，长于这个毫秒数的间隔才会被执行 bgm 音量变换
loud_level = +3.5  # 静音片段内的 bgm 强度，未回避人声
quiet_level = -6.8  # 非静音片段内的 bgm 强度，已回避人声
fade_in_tspan_in_ms = 700  # 从 quiet_level 切换到 loud_level 所需的时长
fade_out_tspan_in_ms = 800  # 与上一条的定义相反

# 文件路径，请根据你的需要设置
speech_path = "speech.wav"  # 语音路径
bgm_path = "bgm.mp3"  # bgm 路径
final_path = "final.wav"  # 输出的人声 + bgm 混声路径（默认 .wav) 


##############################################################################
# 定义函数
##############################################################################

def create_adjust_speech_audio():
    '''
    创建前后有静音片段的完整口播语音
    否则假如 bgm 和原始口播语音一样长，将会显得没头没尾、异常生硬
    '''
    # 读取语音文件
    speech = AudioSegment.from_file(speech_path, format="wav")

    # 创建开头和结尾的静音部分
    opening_silence = AudioSegment.silent(duration=speech_audio_opening_silence * 1000)
    closing_silence = AudioSegment.silent(duration=speech_audio_closing_silence * 1000)

    # 组合开头的静音、语音和结尾的静音
    adjusted_speech = opening_silence + speech + closing_silence

    # 获取调整后的音频长度
    adjusted_tspan_in_ms = len(adjusted_speech)

    return adjusted_speech, adjusted_tspan_in_ms


def create_downsampling_dict(adjust_speech_audio):
    '''创建下采样字典，将每个下采样点的音强二值化'''
    # 初始化
    downsampling_dict = {}
    curr_time_in_ms = 0

    # 获取音频长度
    adjusted_tspan = len(adjust_speech_audio)

    # 遍历音频每20毫秒(默认值)进行采样
    while curr_time_in_ms <= adjusted_tspan:
        # 获取当前时间段的音频
        sample = adjust_speech_audio[curr_time_in_ms:curr_time_in_ms + downsampling_interval_in_ms]
        # 判断音量是否高于门槛值，将结果写入字典
        downsampling_dict[curr_time_in_ms] = sample.dBFS > loudness_threshold
        # 更新时间
        curr_time_in_ms += downsampling_interval_in_ms

    return downsampling_dict


def find_a_silent_interval(downsampling_dict, search_origin_in_ms, adjusted_tspan_in_ms):
    '''找到下一个合格的静音区间'''
    # 初始化静音区间的起始和结束时间
    silent_interval_start_time_in_ms = search_origin_in_ms
    silent_interval_end_time_in_ms = search_origin_in_ms

    # 遍历音频每20毫秒(默认值)进行采样
    for i in range(search_origin_in_ms, adjusted_tspan_in_ms, downsampling_interval_in_ms):
        # 如果当前时间点超出音频长度，返回 None
        if i >= adjusted_tspan_in_ms:
            return None
        
        # 如果当前点是静音
        if not downsampling_dict[i]:
            # 更新静音区间的结束时间
            silent_interval_end_time_in_ms = i
        else:
            # 如果当前点不是静音，并且静音区间已经足够长
            if silent_interval_end_time_in_ms + downsampling_interval_in_ms - silent_interval_start_time_in_ms >= silent_interval_tspan_threshold_in_ms:
                # 静音区间足够长，返回起始和结束时间
                return silent_interval_start_time_in_ms, silent_interval_end_time_in_ms
            else:
                # 重置起始时间，寻找下一个可能的静音区间
                silent_interval_start_time_in_ms = i + downsampling_interval_in_ms
                silent_interval_end_time_in_ms = i + downsampling_interval_in_ms
    
    # 检查在文件末尾是否有足够长的静音区间
    if silent_interval_end_time_in_ms - silent_interval_start_time_in_ms >= silent_interval_tspan_threshold_in_ms:
        return silent_interval_start_time_in_ms, min(silent_interval_end_time_in_ms, adjusted_tspan_in_ms)

    # 如果没有找到足够长的静音区间，返回 None
    return None


def record_silent_interval(downsampling_dict, adjusted_tspan_in_ms):
    '''记录有效的静音区间'''
    silent_interval_dict = {}
    silent_interval_id = 1
    search_origin_in_ms = 0

    # 从音频的开始扫描，查找所有的静音区间
    while search_origin_in_ms < adjusted_tspan_in_ms:
        # 查找从当前起点开始的静音区间
        result = find_a_silent_interval(downsampling_dict, search_origin_in_ms, adjusted_tspan_in_ms)
        
        # 如果找到了一个静音区间
        if result is not None:
            silent_interval_start_time_in_ms, silent_interval_end_time_in_ms = result

            # 记录静音区间
            silent_interval_dict[silent_interval_id] = {
                "s": silent_interval_start_time_in_ms,
                "e": silent_interval_end_time_in_ms,
            }
            silent_interval_id += 1  # 为下一个静音区间准备新的 ID

            # 更新搜索起点，为找到的静音区间之后的第一个时间点
            search_origin_in_ms = silent_interval_end_time_in_ms + downsampling_interval_in_ms
        else:
            # 如果没有找到静音区间，或已到音频末尾，结束循环
            break

    return silent_interval_dict


def get_fade_ins_and_outs(silent_interval_dict):
    '''建立淡入淡出时点列表'''
    fade_ins = []
    fade_outs = []

    # 遍历静音区间字典
    for interval_id, interval_times in silent_interval_dict.items():
        start_time = interval_times["s"]
        end_time = interval_times["e"]

        # 计算淡入和淡出时间点
        fade_in_time = start_time
        fade_out_time = end_time - fade_in_tspan_in_ms

        # 如果淡入时间点有效（大于0），则添加到列表中
        if fade_in_time > 0:
            fade_ins.append(fade_in_time)
        
        # 淡出时间点总是添加到列表中，因为它是静音区间的结束时间点
        fade_outs.append(fade_out_time)

    # 处理首个淡入淡出时间点
    if fade_ins and fade_ins[0] <= 0:
        fade_ins.pop(0)
    if fade_outs and fade_outs[0] <= 0:
        fade_outs.pop(0)

    return fade_ins, fade_outs


def determine_starting_volume(fade_ins, fade_outs):
    '''判断bgm进入时应该是强音还是弱音'''
    # 如果没有淡入和淡出点，音频可能是一个持续的人声，我们默认从quiet_level开始
    if not fade_ins and not fade_outs:
        return quiet_level

    # 如果有淡入点，但没有淡出点，说明一开始有人声，但之后人声一直持续到音频末尾
    if fade_ins and not fade_outs:
        return quiet_level

    # 如果有淡出点，但没有淡入点，说明一开始没有人声
    if not fade_ins and fade_outs:
        return loud_level

    # 如果第一个淡出点在第一个淡入点之前，说明一开始没有人声，bgm应该从loud_level开始
    if fade_outs[0] < fade_ins[0]:
        return loud_level

    # 否则，音频应该从loud_level开始
    return quiet_level


def mix_speech_with_bgm(adjusted_speech, bgm_path, fade_ins, fade_outs):
    '''执行人声回避并混音'''
    # 从路径加载BGM音频
    bgm = AudioSegment.from_file(bgm_path)

    # 确定BGM的初始音量
    starting_volume = determine_starting_volume(fade_ins, fade_outs)
    print(f'Debug: starting_volume = {starting_volume}')
    
    # 调整BGM音频的初始音量
    bgm = bgm + starting_volume

    # 应用淡入和淡出效果
    for fade_in in fade_ins:
        # 在静音结束后，淡入BGM（BGM从quiet变loud）
        bgm = bgm.fade(from_gain=quiet_level, to_gain=loud_level, start=fade_in, duration=fade_in_tspan_in_ms)

    for fade_out in fade_outs:
        # 在语音开始前，淡出BGM（BGM从loud变quiet）
        bgm = bgm.fade(from_gain=loud_level, to_gain=quiet_level, start=fade_out, duration=fade_out_tspan_in_ms)

    # 将语音音频与调整音量后的BGM合并
    speech_bgm_mix = adjusted_speech.overlay(bgm)

    # 输出最终音频
    return speech_bgm_mix


def fade_out_at_the_end(speech_bgm_mix):
    '''在音频的末尾添加淡出效果'''
    # 将淡出时间从秒转换为毫秒，并确保是整数类型
    fade_out_duration_ms = int(fade_out_tspan_at_the_end * 1000)

    # 计算淡出开始的时间点
    fade_out_start = len(speech_bgm_mix) - fade_out_duration_ms

    # 切分音频：淡出部分和其余部分
    pre_fade_out, fade_out_part = speech_bgm_mix[:fade_out_start], speech_bgm_mix[fade_out_start:]

    # 只对淡出部分应用淡出效果
    fade_out_part = fade_out_part.fade_out(duration=fade_out_duration_ms)

    # 将未淡出部分和淡出后的部分重新组合
    speech_bgm_mix = pre_fade_out + fade_out_part

    return speech_bgm_mix


def final_mix(bgm_path):
    '''整合所有步骤，生成最终的混音文件'''
    # 第1步：创建带有开头和结尾静音的调整后的语音音频
    adjusted_speech, adjusted_tspan_in_ms = create_adjust_speech_audio()

    # 第2步：生成下采样字典以识别静音区间
    downsampling_dict = create_downsampling_dict(adjusted_speech)
    print(f'Debug: downsampling_dict = {str(downsampling_dict)[:1500]}...')

    # 第3步：记录语音音频中找到的所有静音区间
    silent_interval_dict = record_silent_interval(downsampling_dict, adjusted_tspan_in_ms)
    print(f'Debug: silent_interval_dict = {str(silent_interval_dict)}')

    # 第4步：确定淡入和淡出点
    fade_ins, fade_outs = get_fade_ins_and_outs(silent_interval_dict)
    print(f'Debug: fade_ins: {fade_ins}, fade_outs = {fade_outs}')

    # 第5步：将语音音频与背景音乐混合，同时应用淡入和淡出效果
    speech_bgm_mix = mix_speech_with_bgm(adjusted_speech, bgm_path, fade_ins, fade_outs)

    # 第6步：在混音音频的结尾添加淡出效果
    final_audio = fade_out_at_the_end(speech_bgm_mix)

    # 将最终混音音频保存到指定的输出路径
    final_audio.export(final_path, format='wav')


##############################################################################
# 执行函数
##############################################################################


def main():
    final_mix(bgm_path)


if __name__ == "__main__":
    main()


'''
程序升级方向建议：
目前下采样的探测是极为简单的。它的原理是扫描所有的点，只要出现一个 True 那么静音片段就会被重置。
这样的设计源于极为纯净的录音环境。因为本程序原来是一个庞大的 AI 语音生成系统的一部分，
但对于普通的人声录制来说，这样的设计可能会受到环境噪音的影响。
为了解决这个问题，你可以考虑这样简单升级程序：
1. 不再对下采样结果二值化。所有音强都用 float 表达，这样方便对未来的片段音强进行定积分。
2. 更简单的处理是，对于过于短促的杂音进行过滤。比如说，对前后静音时长超过 0.8 秒、自身长度短于 0.1 秒的声音进行屏蔽。
更复杂的深度学习方式料可提供更好的结果，但违背了设计这个简单程序的初衷。
'''
