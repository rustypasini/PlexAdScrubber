# PlexAdScrubber

PlexAdScrubber is a Python script that removes specified segments from a .ts video file, then converts the results to an .mkv file. This is particularly useful for removing commercials or unwanted parts from TV shows or movies recorded on the Plex DVR.

## Dependencies

This script depends on `ffmpeg` and `mkvmerge`. Please ensure they are installed and in the system PATH.

### Install dependencies on Ubuntu

```bash
apt update
apt install ffmpeg mkvmerge
```

## Usage

Run the script from the command line with:

```bash
python3 PlexAdScrubber.py
```

The script will prompt you for the following inputs:

* The name of the source video file.  You can include a path to the file.
* The number of segments to be retained.
* The start and end time for each segment to be removed.
* Note: times should be entered in the format HH:MM:SS.s - HH:MM:SS.s. 

The output will be a file named <input_file_name>-edited.mkv, and will be saved in the same directory as the source video file.

## License
This project is licensed under the MIT License - see the LICENSE.md file for details.

## Contribution
I am not a programmer, and this code is not pretty. I had a need, so I did some research, as well as some consulting with ChatGPT. This is the result, and it does what I need. With that in mind, contributions, issues, and feature requests are certainly welcome.
