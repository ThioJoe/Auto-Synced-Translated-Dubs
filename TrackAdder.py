import subprocess as sp
import os
import pathlib
import sys
# Note: Require ffmpepg to be installed and in the PATH environment variable
from pydub import AudioSegment
import langcodes

#--------------------------------------------------------------------------------------------------------------
# Settings
tracksFolder = "output" # Relative to this script file

videoToProcess = r"whatever\path\here"

defaultLanguage = "eng" # The three letter language code for the default track. English = eng, Spanish = spa, etc

# tracksToAddDict = {
#     'spa': "Shortened Video - Spanish Track aac.aac",
# }

# Auto fetch tracks from tracksFolder
tracksToAddDict = {}
for file in os.listdir(tracksFolder):
    if file.endswith(".mp3") or file.endswith(".aac") or file.endswith(".wav"):
        nameNoExt = os.path.splitext(file)[0]
        # Get the language code from the end of the filename. Assumes the code will be separated by ' - '
        if ' - ' in nameNoExt:
            parsedLanguageCode = nameNoExt.split(' - ')[-1].strip()
        else:
            # Print error and ask whether to continue
            print(f"\nWARNING: Could not find language code in filename: {file}")
            print("\nTo read the language code, separate the language code from the rest of the filename with: ")
            print("     ' - ' (a dash surrounded by spaces)")
            print("For example:   'Whatever Video - en-us.wav'")
            print("Enter 'y' to skip that track and conitnue, or enter anything else to exit.")

            userInput = input("Continue Anyway? (y/n): ")
            if userInput.lower() != 'y':
                sys.exit()

        # Check if the language code is valid
        try:
            langObject = langcodes.get(parsedLanguageCode)
            threeLetterCode = langObject.to_alpha3()
            languageDisplayName = langcodes.get(threeLetterCode).display_name()

            if threeLetterCode in tracksToAddDict.keys():
                print(f"\ERROR while checking {file}: Language '{languageDisplayName}' is already in use by file: {tracksToAddDict[threeLetterCode]}")
                userInput = input("\nPress Enter to exit... ")
                sys.exit()

            tracksToAddDict[threeLetterCode] = file

        except:
            print(f"\nWARNING: Language code '{parsedLanguageCode}' is not valid for file: {file}")
            print("Enter 'y' to skip that track and conitnue, or enter anything else to exit.")
            userInput = input("\nContinue Anyway and Skip File? (y/n): ")
            if userInput.lower() != 'y':
                sys.exit()

print("")

#--------------------------------------------------------------------------------------------------------------

outputFile = f"{pathlib.Path(videoToProcess).stem} - MultiTrack.mp4"

# Convert each entry in tracksToAddDict to an absolute path and combine with tracksFolder
tracksFolder = os.path.normpath(tracksFolder)
tracksToAddDict = {key: os.path.join(tracksFolder, value) for key, value in tracksToAddDict.items()}
videoToProcess = os.path.join(tracksFolder, videoToProcess)
outputFile = os.path.join(tracksFolder, outputFile)

# Get number of tracks to add
numTracks = len(tracksToAddDict)

# Check if tracks are stereo, if not it will convert them to stereo before adding
tempFilesToDelete = []
for key, value in tracksToAddDict.items():
    audio = AudioSegment.from_file(value)
    # Check the number of channels in the audio file
    num_channels = audio.channels
    if num_channels == 1:
        # Get the file extension of the file without the period
        fileExtension = os.path.splitext(value)[1][1:]
        # convert to stereo
        stereo_file = audio.set_channels(2)
        # save the stereo file
        tempFileName = f"{value}_stereo_temp.{fileExtension}" # Change this before publishing, needs to adapt to filetype

        # Determine the format needed for pydub to export
        if fileExtension == "aac":
            formatString = "adts"
        else:
            formatString = fileExtension

        # Export the file with appropriate format
        stereo_file.export(tempFileName, format=formatString, bitrate="128k") # Change this before publishing, needs to adapt to filetype
        tracksToAddDict[key] = tempFileName
        # Add to list of files to delete later when done
        tempFilesToDelete.append(tempFileName)


# Create string for ffmpeg command for each string
#Example:    sp.run(f'ffmpeg -i "video.mp4" -i "audioTrack.mp3" -map 0 -map 1 -metadata:s:a:0 language=eng -metadata:s:a:1 language=spa -codec copy output.mp4')
# In metadata, a=audio, s=stream, 0=first stream, 1=second stream, etc  -  Also: g=global container, c=chapter, p=program
trackStringsCombined = ""
mapList = "-map 0"
metadataCombined = f'-metadata:s:a:0 language={defaultLanguage} -metadata:s:a:0 title="{defaultLanguage}" -metadata:s:a:0 handler_name="{defaultLanguage}"'
count = 1
for key, value in tracksToAddDict.items():
    trackStringsCombined += f' -i "{value}"'
    metadataCombined += f' -metadata:s:a:{count} language={key}'
    metadataCombined += f' -metadata:s:a:{count} handler_name={key}' # Handler shows as the track title in MPC-HC
    metadataCombined += f' -metadata:s:a:{count} title="{key}"' # This is the title that will show up in the audio track selection menu
    mapList += f' -map {count}'
    count+=1

finalCommand = f'ffmpeg -i "{videoToProcess}" {trackStringsCombined} {mapList} {metadataCombined} -codec copy "{outputFile}"'

sp.run(finalCommand)

# Delete temp files
for file in tempFilesToDelete:
    os.remove(file)

