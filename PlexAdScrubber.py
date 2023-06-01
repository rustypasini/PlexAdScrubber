#!/usr/bin/env python3
import os
import re
import sys
import subprocess
import cv2
import numpy as np

VERSION = "0.2.0-a"

def print_help_message():
    help_message = """
    This script is used to split and merge video segments.

    Usage: PlexAdScrubber.py

    The script will prompt you for the following inputs:

    - The name of the input file
    - The start and end time for each segment

    The times should be entered in the format HH:MM:SS.s - HH:MM:SS.s.

    The output will be a file named <input_file_name>-edited.mkv.

    This script depends on ffmpeg and mkvmerge. Please ensure they are installed and in the system PATH.

    """
    print(help_message)

def run_command(command):
    # Runs a command and exits the script with an error if the command fails.
    exit_status = os.system(command)
    if exit_status != 0:
        print(f"\nError: The following command exited with status {exit_status}:\n{command}")
        sys.exit(1)

def check_dependencies(required_programs):
    for program in required_programs:
        try:
            subprocess.check_output(f'command -v {program}', shell=True)
        except subprocess.CalledProcessError:
            print(f"\nError: {program} is not installed or not found in PATH.")
            sys.exit(1)

def prompt_file_name():
    while True:
        file_name = input("Please enter the name of the input file: ")
        if os.path.isfile(file_name):
            new_file_name = file_name.rsplit(".", 1)[0] + "-edited.mkv"
            return file_name, new_file_name
        else:
            print("Invalid file name. Please try again.")

#def prompt_segments():
#    # RegEx to validate time format
#    time_pattern = re.compile("^\\d{2}:\\d{2}:\\d{2}(\\.\\d)? *- *\\d{2}:\\d{2}:\\d{2}(\\.\\d)?$")
#    # List of start and end times for the segments to be kept
#    segments = []
#    i = 0
#    while True:
#        i += 1
#        segment = input(f"Enter the start & end time for segment {i}, or hit Enter to stop: ")
#        if not segment:
#            break
#        if time_pattern.match(segment):
#            segments.append(segment.replace(" ", ""))
#        else:
#            print("Invalid time format. Please enter the times in the format HH:MM:SS.s - HH:MM:SS.s")
#            i -= 1
#    return segments

def detect_black_frames(video_file, threshold=1):
    cap = cv2.VideoCapture(video_file)
    black_frame_blocks = []
    last_frame_was_black = False
    block_start_time = None
    last_block_end_time = "00:00:00.0"
    # Get the total number of frames and the frame rate.
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    fps = cap.get(cv2.CAP_PROP_FPS)
    # Calculate the duration of the video.
    video_duration = frame_count / fps

    while cap.isOpened():
        ret, frame = cap.read()

        # Get the timestamp of the current frame in milliseconds.
        timestamp_msec = cap.get(cv2.CAP_PROP_POS_MSEC)
        # Convert timestamp to seconds.
        timestamp_sec = timestamp_msec / 1000

        if not ret:
            # Video ended, add the last block to the list.
            block = (last_block_end_time, convert_timestamp(video_duration))
            black_frame_blocks.append(block)
            break

        # Calculate the average pixel brightness.
        avg_brightness = np.average(frame)
        is_black = avg_brightness < threshold

        if is_black and not last_frame_was_black:
            # New block of black frames started.
            block_start_time = timestamp_sec
            last_frame_was_black = True
        elif not is_black and last_frame_was_black:
            # The block ended.
            block_duration = timestamp_sec - block_start_time
            if block_duration >= 0.2:
                block = (last_block_end_time, convert_timestamp((block_start_time + timestamp_sec) / 2))
                black_frame_blocks.append(block)
                last_block_end_time = block[1]
            last_frame_was_black = False

    cap.release()

    return black_frame_blocks

def convert_timestamp(timestamp):
    hours = int(timestamp // 3600)
    timestamp %= 3600
    minutes = int(timestamp // 60)
    timestamp %= 60
    seconds = int(timestamp)
    tenths_of_second = round(10 * (timestamp - seconds))
    return f"{hours:02}:{minutes:02}:{seconds:02}.{tenths_of_second}"

def prompt_segments(file_name):
    # List of start and end times for the segments to be kept
    segments = detect_black_frames(file_name)
    # Format segments for compatibility with the rest of the script
    segments = [f"{start} - {end}" for start, end in segments]
    return segments

def convert_to_mkv(file_name):
    # Convert .ts file to .mkv
    run_command(f'ffmpeg -i "{file_name}" -c copy output.mkv > /dev/null 2>&1')
    if not os.path.isfile("output.mkv"):
        print(f"\nError: Failed to create output.mkv.")
        sys.exit(1)
    print(".", end="")
    sys.stdout.flush()

def split_file(segments):
    # Create a list of split times
    split_times = []
    for segment in segments:
        start_time, end_time = [time.strip() for time in segment.split("-")]
        split_times.append(start_time)
        split_times.append(end_time)
    # Format split times as a comma-separated string
    split_times_str = ",".join(split_times)
    # Use mkvmerge to split the file at the start and end of each segment
    run_command(f'mkvmerge -o split.mkv --split timecodes:{split_times_str} output.mkv > /dev/null 2>&1')
    print(".", end="")
    sys.stdout.flush()

def merge_files(num_segments, new_file_name, split_times):
    # Check if the first segment starts at 00:00:00
    starts_at_zero = split_times[0] == "00:00:00.0"
    if starts_at_zero:
        merge_files_starting_zero(num_segments, new_file_name)
    else:
        merge_files_not_starting_zero(num_segments, new_file_name)

def merge_files_starting_zero(num_segments, new_file_name):
    files_to_merge = ["split-001.mkv"]
    for i in range(3, 2*num_segments, 2):
        files_to_merge.append(f"split-{i:03d}.mkv")
    run_command(f'mkvmerge -o "{new_file_name}" {" + ".join(files_to_merge)} > /dev/null 2>&1')
    validate_and_cleanup(num_segments, new_file_name, starts_at_zero=True)

def merge_files_not_starting_zero(num_segments, new_file_name):
    files_to_merge = ["split-002.mkv"]
    for i in range(4, 2*num_segments+1, 2):
        files_to_merge.append(f"split-{i:03d}.mkv")
    run_command(f'mkvmerge -o "{new_file_name}" {" + ".join(files_to_merge)} > /dev/null 2>&1')
    validate_and_cleanup(num_segments, new_file_name, starts_at_zero=False)

def validate_and_cleanup(num_segments, new_file_name, starts_at_zero):
    if not os.path.isfile(new_file_name):
        print(f"\nError: Failed to create {new_file_name}.")
        sys.exit(1)
    print(".", end="")
    sys.stdout.flush()
    num_files = 2*num_segments+2 if starts_at_zero else 2*num_segments+3
#    for i in range(1, num_files):
#        if os.path.exists(f'split-{i:03d}.mkv'):
#            run_command(f'rm split-{i:03d}.mkv')

def remove_output_file():
    if os.path.isfile("output.mkv"):
        run_command('rm output.mkv')
    
def main():
    if len(sys.argv) > 1:
        if sys.argv[1] in ['-h', '--help']:
            print_help_message()
            sys.exit(0)
        elif sys.argv[1] in ['-v', '--version']:
            print(f"PlexAdScrubber.py version {VERSION}")
            sys.exit(0)

    required_programs = ['ffmpeg', 'mkvmerge']
    check_dependencies(required_programs)
    file_name, new_file_name = prompt_file_name()
    segments = prompt_segments(file_name)
    num_segments = len(segments)

    print("Starting video processing...", end="")
    sys.stdout.flush()
    convert_to_mkv(file_name)
    split_file(segments)
    merge_files(num_segments, new_file_name, segments[0].split("-") if segments else None)
    remove_output_file()
    print("\nVideo processing has completed.")

if __name__ == '__main__':
    main()
