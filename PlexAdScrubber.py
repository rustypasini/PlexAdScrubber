#!/usr/bin/env python3
import os
import re
import sys
import subprocess
import cv2
import numpy as np

VERSION = "0.2.0-e"

def print_help_message():
    help_message = """
    This script is used to remove ads from recorded video files from Plex DVR.

    Usage: PlexAdScrubber.py

    The script will prompt you for the name of the input video file.
    
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

def detect_black_frames(video_file, threshold=1, tolerance=5):
    print(".", end="")
    sys.stdout.flush()
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
    non_black_counter = 0
    black_counter = 0

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
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        avg_value = np.average(frame[:, :, 2])
        is_black = avg_value < threshold

        if is_black:
            black_counter += 1
            non_black_counter = 0
        else:
            non_black_counter += 1
            black_counter = 0

        if black_counter == tolerance and not last_frame_was_black:
            # New block of black frames started.
            block_start_time = timestamp_sec - ((tolerance - 1) / fps)
            last_frame_was_black = True
        elif non_black_counter == tolerance and last_frame_was_black:
            # The block ended.
            block_duration = timestamp_sec - block_start_time
            if block_duration >= 0.2:
                block = (last_block_end_time, convert_timestamp((block_start_time + (block_duration / 2))))
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
    print("\nIdentifying video segments...", end="")
    sys.stdout.flush()
    segments = detect_black_frames(file_name)
    segments = [f"{start} - {end}" for start, end in segments]
    return segments

def convert_to_mkv(file_name):
    # Convert .ts file to .mkv
    print("\nConverting file to mkv...", end="")
    sys.stdout.flush()
    run_command(f'ffmpeg -i "{file_name}" -c copy output.mkv > /dev/null 2>&1')
    if not os.path.isfile("output.mkv"):
        print(f"\nError: Failed to create output.mkv.")
        sys.exit(1)
        
    print("done", end="")
    sys.stdout.flush()
    
def split_file(segments):
    # Create a list of split times
    split_times = []
    print("\nIdentifying ads...", end="")
    sys.stdout.flush()
    for segment in segments:
        start_time, end_time = [time.strip() for time in segment.split("-")]
        split_times.append(end_time)
    # Format split times as a comma-separated string
    split_times_str = ",".join(split_times)
    # Use mkvmerge to split the file at the end of each segment
    run_command(f'mkvmerge -o split.mkv --split timecodes:{split_times_str} output.mkv > /dev/null 2>&1')
    print("done", end="")
    sys.stdout.flush()
    
def detect_color(video_file, lower_color, upper_color, x, y, width, height):
    cap = cv2.VideoCapture(video_file)
    color_found = False
    consecutive_frames = 0
    print(".", end="")
    sys.stdout.flush()
    
    while cap.isOpened():
        ret, frame = cap.read()

        if not ret:
            break

        roi = frame[y:y+height, x:x+width]
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, lower_color, upper_color)

        if np.all(mask):
            consecutive_frames += 1
        else:
            consecutive_frames = 0

        if consecutive_frames >= 300:
            color_found = True
            break

    cap.release()
    return color_found

def merge_files(num_segments, new_file_name):
    # Define the color range in HSV.
    lower_color = np.array([165, 255, 226])
    upper_color = np.array([170, 255, 255])

    # Define the ROI location and size.
    x = 548
    y = 446
    width = 1
    height = 1

    print("\nReassembling video file...", end="")
    sys.stdout.flush()
    
    files_to_merge = []
    for i in range(2, 2*num_segments+1):  # Starting from 2 to disregard the first split file.
        file_name = f"split-{i:03d}.mkv"
        if detect_color(file_name, lower_color, upper_color, x, y, width, height):
            files_to_merge.append(file_name)
    
    run_command(f'mkvmerge -o "{new_file_name}" {" + ".join(files_to_merge)} > /dev/null 2>&1')
    print("done", end="")
    sys.stdout.flush()
    validate_and_cleanup(num_segments, new_file_name)

def validate_and_cleanup(num_segments, new_file_name):
    if not os.path.isfile(new_file_name):
        print(f"\nError: Failed to create {new_file_name}.")
        sys.exit(1)
    print("\nCleaning up temporary files...", end="")
    sys.stdout.flush()
    for i in range(1, num_segments+2):  # Adjusted to num_segments+2
        if os.path.exists(f'split-{i:03d}.mkv'):
            run_command(f'rm split-{i:03d}.mkv')
    remove_output_file()
    print("done", end="")
    sys.stdout.flush()
    
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
    convert_to_mkv(file_name)
    segments = prompt_segments('output.mkv')
    num_segments = len(segments)
    split_file(segments)
    merge_files(num_segments, new_file_name)
    print("\nVideo processing is complete.")

if __name__ == '__main__':
    main()
