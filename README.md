# Video-Synced-Translated-Dubs
 Automatically translates the text of a video based on a subtitle file, and also uses AI voice to dub the video, and synced using the subtitle's timings

### Purpose
If you already have a human-made SRT subtitles file for a video, this will:
1. Use Google Cloud to automatically translate the text
2. Create text-to-speech audio clips of the translated text (using more realistic neural voices)
3. Use the timings of the subtitle lines to calculate the correct duration of each spoken audio clip
4. Stretch or shrink the translated audio clip to be exactly the same length as the original speech, and inserted at the same point in the audio. Therefore the translated speech will remain perfectly in sync with the original video.

### External Requirements:
- ffmpeg must be installed (https://ffmpeg.org/download.html)
- You'll need the binaries for a program called 'rubberband' ( https://breakfastquay.com/rubberband/ ) . Doesn't need to be installed, just put both exe's and the dll file in the same directory as the scripts.

### Notes:
- This works best with subtitles that do not remove gaps between sentences and lines. 
