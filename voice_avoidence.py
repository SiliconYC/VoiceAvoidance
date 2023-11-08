from pydub import AudioSegment

'''
Basic explanation:
The program will scan the entire audio by default at intervals of 0.02 seconds. (Downsampling mode)
The scanning results will be binarized - True for loudness above the threshold, False for loudness below the threshold.
If all scanning results within a continuous 2-second interval are False, then it is considered a silent segment. Setting such a threshold is to avoid too frequent changes in volume.
Background music will be temporarily enhanced within the silent segment, with a fade-in and fade-out effect.
By default, the program generates a mixed audio file called "final.wav" in the root directory.
'''

'''
Operational tips:
1. 
All the parameters mentioned above can be set, but the default values can cope with most situations.
Only loud_level and quiet_level need to be set for each song, because the average volume of different songs varies greatly. See below for details.
2. 
The prints starting with "Debug:..." can be deleted without affecting the function.
3. 
Pay attention to the audio format of the input and output. By default, the bgm is MP3, and the original voice-over and the output mix are WAV. 
If there is any change, please be sure to set the corresponding format for AudioSegment.
4. 
tspan stands for time_span, which is a neologism created to avoid conflict with the duration property of AudioSegment.
'''


##############################################################################
# Define variables
##############################################################################

# Insert silent segments at the beginning and end of the original voice file, theoretically these silences should be filled with bgm (unit: seconds)
speech_audio_opening_silence = 4
speech_audio_closing_silence = 3
# The ending bgm will automatically fade out to zero, this is the duration of the fade-out (unit: seconds)
fade_out_tspan_at_the_end = 1.5  

# Micro parameters for voice avoidance (time unit: milliseconds)
downsampling_interval_in_ms = 20  # Downsample cycle interval, default 20 milliseconds
loudness_threshold = -20  # Define the loudness threshold, values below this will be considered as silence
silent_interval_tspan_threshold_in_ms = 2000  # Silent interval threshold for executing fade-in and fade-out, intervals longer than this millisecond number will trigger bgm volume changes
loud_level = +3.5  # bgm intensity within the silent segment, voice not avoided
quiet_level = -6.8  # bgm intensity within the non-silent segment, voice avoided
fade_in_tspan_in_ms = 700  # Duration required to switch from quiet_level to loud_level
fade_out_tspan_in_ms = 800  # Definition opposite to the above

# File paths, please set according to your needs
speech_path = "speech.wav"  # Voice path
bgm_path = "bgm.mp3"  # bgm path
final_path = "final.wav"  # Output path for the mixed voice + bgm audio (default .wav) 


##############################################################################
# Define functions
##############################################################################

def create_adjust_speech_audio():
    '''
    Create the complete voice-over audio with silent segments at the beginning and end
    Otherwise, if the bgm and the original voice-over are of the same length, it will appear abrupt and awkward
    '''
    # Load the voice file
    speech = AudioSegment.from_file(speech_path, format="wav")

    # Create the silent segments for the beginning and end
    opening_silence = AudioSegment.silent(duration=speech_audio_opening_silence * 1000)
    closing_silence = AudioSegment.silent(duration=speech_audio_closing_silence * 1000)

    # Combine the silence at the beginning, the speech, and the silence at the end
    adjusted_speech = opening_silence + speech + closing_silence

    # Get the length of the adjusted audio
    adjusted_tspan_in_ms = len(adjusted_speech)

    return adjusted_speech, adjusted_tspan_in_ms


def create_downsampling_dict(adjust_speech_audio):
    '''Create a downsampling dictionary, binarize the loudness at each downsampling point'''
    # Initialize
    downsampling_dict = {}
    curr_time_in_ms = 0

    # Get the audio length
    adjusted_tspan = len(adjust_speech_audio)

    # Traverse the audio for sampling every 20 milliseconds (default value)
    while curr_time_in_ms <= adjusted_tspan:
        # Get the audio segment for the current time period
        sample = adjust_speech_audio[curr_time_in_ms:curr_time_in_ms + downsampling_interval_in_ms]
        # Determine if the volume is above the threshold and write the result into the dictionary
        downsampling_dict[curr_time_in_ms] = sample.dBFS > loudness_threshold
        # Update the time
        curr_time_in_ms += downsampling_interval_in_ms

    return downsampling_dict


def find_a_silent_interval(downsampling_dict, search_origin_in_ms, adjusted_tspan_in_ms):
    '''Find the next qualifying silent interval'''
    # Initialize the start and end times of the silent interval
    silent_interval_start_time_in_ms = search_origin_in_ms
    silent_interval_end_time_in_ms = search_origin_in_ms

    # Traverse the audio for sampling every 20 milliseconds (default value)
    for i in range(search_origin_in_ms, adjusted_tspan_in_ms, downsampling_interval_in_ms):
        # If the current time point exceeds the length of the audio, return None
        if i >= adjusted_tspan_in_ms:
            return None
        
        # If the current point is silent
        if not downsampling_dict[i]:
            # Update the end time of the silent interval
            silent_interval_end_time_in_ms = i
        else:
            # If the current point is not silent, and the silent interval is already long enough
            if silent_interval_end_time_in_ms + downsampling_interval_in_ms - silent_interval_start_time_in_ms >= silent_interval_tspan_threshold_in_ms:
                # The silent interval is long enough, return the start and end times
                return silent_interval_start_time_in_ms, silent_interval_end_time_in_ms
            else:
                # Reset the start time, looking for the next possible silent interval
                silent_interval_start_time_in_ms = i + downsampling_interval_in_ms
                silent_interval_end_time_in_ms = i + downsampling_interval_in_ms
    
    # Check if there is a long enough silent interval at the end of the file
    if silent_interval_end_time_in_ms - silent_interval_start_time_in_ms >= silent_interval_tspan_threshold_in_ms:
        return silent_interval_start_time_in_ms, min(silent_interval_end_time_in_ms, adjusted_tspan_in_ms)

    # If a long enough silent interval is not found, return None
    return None


def record_silent_interval(downsampling_dict, adjusted_tspan_in_ms):
    '''Record the valid silent intervals'''
    silent_interval_dict = {}
    silent_interval_id = 1
    search_origin_in_ms = 0

    # Start scanning from the beginning of the audio, looking for all silent intervals
    while search_origin_in_ms < adjusted_tspan_in_ms:
        # Find the silent interval starting from the current point
        result = find_a_silent_interval(downsampling_dict, search_origin_in_ms, adjusted_tspan_in_ms)
        
        # If a silent interval is found
        if result is not None:
            silent_interval_start_time_in_ms, silent_interval_end_time_in_ms = result

            # Record the silent interval
            silent_interval_dict[silent_interval_id] = {
                "s": silent_interval_start_time_in_ms,
                "e": silent_interval_end_time_in_ms,
            }
            silent_interval_id += 1  # Prepare a new ID for the next silent interval

            # Update the search origin to the first time point after the found silent interval
            search_origin_in_ms = silent_interval_end_time_in_ms + downsampling_interval_in_ms
        else:
            # If no silent interval is found, or the end of the audio is reached, end the loop
            break

    return silent_interval_dict


def get_fade_ins_and_outs(silent_interval_dict):
    '''Establish a list of fade-in and fade-out points'''
    fade_ins = []
    fade_outs = []

    # Traverse the silent interval dictionary
    for interval_id, interval_times in silent_interval_dict.items():
        start_time = interval_times["s"]
        end_time = interval_times["e"]

        # Calculate the fade-in and fade-out points
        fade_in_time = start_time
        fade_out_time = end_time - fade_in_tspan_in_ms

        # If the fade-in point is valid (greater than 0), add it to the list
        if fade_in_time > 0:
            fade_ins.append(fade_in_time)
        
        # Always add the fade-out point to the list because it is the end time of the silent interval
        fade_outs.append(fade_out_time)

    # Process the first fade-in and fade-out points
    if fade_ins and fade_ins[0] <= 0:
        fade_ins.pop(0)
    if fade_outs and fade_outs[0] <= 0:
        fade_outs.pop(0)

    return fade_ins, fade_outs


def determine_starting_volume(fade_ins, fade_outs):
    '''Determine if the BGM should enter with a loud or soft volume'''
    # If there are no fade-in and fade-out points, the audio might be a continuous voice-over, so we default to starting from quiet_level
    if not fade_ins and not fade_outs:
        return quiet_level

    # If there are fade-in points but no fade-out points, it implies there is a voice-over at the beginning that continues until the end of the audio
    if fade_ins and not fade_outs:
        return quiet_level

    # If there are fade-out points but no fade-in points, it implies there is no voice-over at the beginning
    if not fade_ins and fade_outs:
        return loud_level

    # If the first fade-out point is before the first fade-in point, it implies there is no voice-over at the beginning, and the BGM should start from loud_level
    if fade_outs[0] < fade_ins[0]:
        return loud_level

    # Otherwise, the audio should start from quiet_level
    return quiet_level


def mix_speech_with_bgm(adjusted_speech, bgm_path, fade_ins, fade_outs):
    '''Execute voice-over avoidance and mix the audio'''
    # Load the BGM audio from the path
    bgm = AudioSegment.from_file(bgm_path)

    # Determine the initial volume of the BGM
    starting_volume = determine_starting_volume(fade_ins, fade_outs)
    print(f'Debug: starting_volume = {starting_volume}')
    
    # Adjust the initial volume of the BGM audio
    bgm = bgm + starting_volume

    # Apply fade-in and fade-out effects
    for fade_in in fade_ins:
        # Fade in the BGM after the silence (BGM transitions from quiet to loud)
        bgm = bgm.fade(from_gain=quiet_level, to_gain=loud_level, start=fade_in, duration=fade_in_tspan_in_ms)

    for fade_out in fade_outs:
        # Fade out the BGM before the voice-over starts (BGM transitions from loud to quiet)
        bgm = bgm.fade(from_gain=loud_level, to_gain=quiet_level, start=fade_out, duration=fade_out_tspan_in_ms)

    # Combine the voice-over audio with the volume-adjusted BGM
    speech_bgm_mix = adjusted_speech.overlay(bgm)

    # Output the final audio
    return speech_bgm_mix


def fade_out_at_the_end(speech_bgm_mix):
    '''Add a fade-out effect at the end of the audio'''
    # Convert the fade-out time from seconds to milliseconds, ensuring it is an integer
    fade_out_duration_ms = int(fade_out_tspan_at_the_end * 1000)

    # Calculate the start time for the fade-out
    fade_out_start = len(speech_bgm_mix) - fade_out_duration_ms

    # Split the audio: fade-out part and the rest
    pre_fade_out, fade_out_part = speech_bgm_mix[:fade_out_start], speech_bgm_mix[fade_out_start:]

    # Apply the fade-out effect only to the fade-out part
    fade_out_part = fade_out_part.fade_out(duration=fade_out_duration_ms)

    # Reassemble the non-fade-out part and the part after fade-out
    speech_bgm_mix = pre_fade_out + fade_out_part

    return speech_bgm_mix


def final_mix(bgm_path):
    '''Integrate all steps to generate the final mixed audio file'''
    # Step 1: Create the adjusted voice-over audio with silence at the beginning and the end
    adjusted_speech, adjusted_tspan_in_ms = create_adjust_speech_audio()

    # Step 2: Generate a downsampling dictionary to identify silent intervals
    downsampling_dict = create_downsampling_dict(adjusted_speech)
    print(f'Debug: downsampling_dict = {str(downsampling_dict)[:1500]}...')

    # Step 3: Record all the silent intervals found in the voice-over audio
    silent_interval_dict = record_silent_interval(downsampling_dict, adjusted_tspan_in_ms)
    print(f'Debug: silent_interval_dict = {str(silent_interval_dict)}')

    # Step 4: Determine the fade-in and fade-out points
    fade_ins, fade_outs = get_fade_ins_and_outs(silent_interval_dict)
    print(f'Debug: fade_ins: {fade_ins}, fade_outs = {fade_outs}')

    # Step 5: Mix the voice-over audio with the background music, applying fade-in and fade-out effects
    speech_bgm_mix = mix_speech_with_bgm(adjusted_speech, bgm_path, fade_ins, fade_outs)

    # Step 6: Add a fade-out effect at the end of the mixed audio
    final_audio = fade_out_at_the_end(speech_bgm_mix)

    # Save the final mixed audio to the specified output path
    final_audio.export(final_path, format='wav')


##############################################################################
# Execute the function
##############################################################################


def main():
    final_mix(bgm_path)


if __name__ == "__main__":
    main()


'''
Suggestions for program upgrades:
The current downsampling detection is extremely simple. It works by scanning all points and resetting the silence segment whenever a True is encountered.
Such design is based on a very pure recording environment because the program was originally part of a large AI voice generation system.
However, for ordinary voice recordings, this design might be affected by ambient noise.
To address this issue, you can consider a simple upgrade to the program:
1. Do not binarize the results of the downsampling. All loudness levels are expressed in float, which facilitates the definite integration of future segment loudness.
2. A simpler treatment is to filter out overly brief noises. For example, ignore any sound that is shorter than 0.1 seconds and surrounded by silence of more than 0.8 seconds.
More complex deep learning methods may provide better results, but that would defeat the purpose of designing this simple program.
'''
