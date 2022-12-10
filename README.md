# Auto Synced & Translated Dubs
 Automatically translates the text of a video based on a subtitle file, and also uses AI voice to dub the video, while keeping it properly synced to the original video using the subtitle's timings.
 
### Purpose
If you already have a human-made SRT subtitles file for a video, this will:
1. Use Google Cloud to automatically translate the text, and create a new translated SRT file
2. Create text-to-speech audio clips of the translated text (using more realistic neural voices)
3. Use the timings of the subtitle lines to calculate the correct duration of each spoken audio clip
4. Stretch or shrink the translated audio clip to be exactly the same length as the original speech, and inserted at the same point in the audio. Therefore the translated speech will remain perfectly in sync with the original video.

### External Requirements:
- ffmpeg must be installed (https://ffmpeg.org/download.html)
- You'll need the binaries for a program called 'rubberband' ( https://breakfastquay.com/rubberband/ ) . Doesn't need to be installed, just put both exe's and the dll file in the same directory as the scripts.

### Notes:
- This works best with subtitles that do not remove gaps between sentences and lines.
- It only supports Google Translate API for text translation, but it supports both Google and Azure for Text-To-Speech with neural voices.
- This script was written with my own personal workflow in mind. That is:
    - I use [**OpenAI Whisper**](https://github.com/openai/whisper) to transcribe the videos locally, then use [**Descript**](https://www.descript.com/) to sync that transcription and touch it up with corrections.
    - Then I export the SRT file with Descript, which is ideal because it does not just butt the start and end times of each subtitle line next to each other. This means the resulting dub will preserve the pauses between sentences from the original speech. If you use subtitles from another program, you might find the pauses between lines are too short.
    - The SRT export settings in Descript that seem to work decently for dubbing are *150 max characters per line*, and *1 max line per card*.
- The "Two Pass" synthesizing feature (can be enabled in the config) will drastically improve the quality of the final result, but will require synthesizing each clip twice, therefore doubling any API costs.

----

### For Planned Features See: [Planned Features Wiki Page](https://github.com/ThioJoe/Auto-Synced-Translated-Dubs/wiki/Planned-Features)
### For Google Cloud Project Setup Instructions See: [Instructions Wiki Page](https://github.com/ThioJoe/Auto-Synced-Translated-Dubs/wiki/Instructions:-Obtaining-an-API-Key)
### For Result Examples See: [Examples Wiki Page](https://github.com/ThioJoe/Auto-Synced-Translated-Dubs/wiki/Examples)
