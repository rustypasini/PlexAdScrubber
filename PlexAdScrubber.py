#!/usr/bin/env python3
import os
import re
import sys
import subprocess

"""
PlexAdScrubber.py
Version: 0.1.0
Author: Rusty Pasini
Date: 2023-05-24
Description: This script is used to split and merge segments of a video file.
             It requires user input for file names and timestamps.
             The script is dependent on ffmpeg and mkvmerge tools.
"""

def print_help_message():
    help_message = """
    This script is used to split and merge video segments.

    Usage: PlexAdScrubber.py

    The script will prompt you for the following inputs:

    - The name of the input file
    - The number of segments
    - The start and end time for each segment

    The times should be entered in the format HH:MM:SS.s - HH:MM:SS.s.

    The output will be a file named <input_file_name>-edited.mkv.

    This script depends on ffmpeg and mkvmerge. Please ensure they are installed and in the system PATH.

    """
    print(help_message)

def run_command(command):
    """Runs a command and exits the script with an error if the command fails."""
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

def prompt_segments(num_segments):
    time_pattern = re.compile("^\\d{2}:\\d{2}:\\d{2}(\\.\\d)? *- *\\d{2}:\\d{2}:\\d{2}(\\.\\d)?$")
    segments = []
    for i in range(num_segments):
        while True:
            segment = input(f"Please enter the start and end time for segment {i+1} (HH:MM:SS.s - HH:MM:SS.s): ")
            if time_pattern.match(segment):
                segments.append(segment.replace(" ", ""))
                break
            else:
                print("Invalid time format. Please enter the times in the format HH:MM:SS.s - HH:MM:SS.s")
    return segments

def convert_to_mkv(file_name):
    run_command(f'ffmpeg -i "{file_name}" -c copy output.mkv > /dev/null 2>&1')
    if not os.path.isfile("output.mkv"):
        print(f"\nError: Failed to create output.mkv.")
        sys.exit(1)
    print(".", end="")
    sys.stdout.flush()

def split_file(segments):
    split_times = []
    for segment in segments:
        start_time, end_time = [time.strip() for time in segment.split("-")]
        split_times.append(start_time)
        split_times.append(end_time)
    split_times_str = ",".join(split_times)
    run_command(f'mkvmerge -o split.mkv --split timecodes:{split_times_str} output.mkv > /dev/null 2>&1')
    print(".", end="")
    sys.stdout.flush()

def merge_files(num_segments, new_file_name, split_times):
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
    for i in range(1, num_files):
        if os.path.exists(f'split-{i:03d}.mkv'):
            run_command(f'rm split-{i:03d}.mkv')

def remove_output_file():
    if os.path.isfile("output.mkv"):
        run_command('rm output.mkv')

def main():
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print_help_message()
        sys.exit(0)

    required_programs = ['ffmpeg', 'mkvmerge']
    check_dependencies(required_programs)
    file_name, new_file_name = prompt_file_name()

    while True:
        num_segments = input("Please enter the number of segments: ")
        if num_segments.isdigit() and int(num_segments) > 0:
            num_segments = int(num_segments)
            break
        else:
            print("Invalid input. Please enter a positive integer.")

    segments = prompt_segments(num_segments)
    print("Starting video processing...", end="")
    sys.stdout.flush()
    convert_to_mkv(file_name)
    split_file(segments)
    merge_files(num_segments, new_file_name, segments[0].split("-"))
    remove_output_file()
    print("\nVideo processing has completed.")

if __name__ == '__main__':
    main()

