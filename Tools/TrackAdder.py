
#========================================= USER SETTINGS ===============================================

# REMEMBER: Unlike the .ini config files, the variable values here must be surrounded by "quotation" marks

    # The folder (or path relative to this script file) containing the audio track files to add to the video
    # Note: ALL audio tracks in the folder will be added, so ensure only the tracks you want are in there
    # A resulting copy of the original video, now with all tracks added, will also be placed in this folder
tracksFolder = r"output" 

    # The video can be anywhere as long as you use the full absolute filepath. Or you can use a relative path.
    # The original will remain the same, and a copy with "MultiTrack" added to the name will be created in the output folder
    # This script assumes the video is an mp4 file. I'm not sure if it will work with other formats/containers.
videoToProcess = r"whatever\path\here"

    # Whether to merge a sound effect track into each audio track before adding to the video
    # The original audio track files will remain unchanged
useSoundEffectsTrack = False

    # If applicable, the filename of the sound effects or music track to add to each audio track before adding to the video
    # If "useSoundEffectsTrack" is set to False, this will be ignored
    # Must be in the same folder as the audio tracks!
effectsTrackFileName = r"your_sound_effects_file.mp3"

    # Whether to save a copy of each audio track with the sound effects track merged into it
    # They will go into a folder called "Merged Effects Tracks"
    # Note: The original audio track files will always remain unchanged no matter this setting
saveMergedTracks = True

    # The three letter language code for the default track. English = eng, Spanish = spa, etc
defaultLanguage = "eng" 

#========================================================================================================

# Set working diretory to one level up, so that the scripts folder is in the path
import os
import sys
# Check if current folder is named "Tools"
if os.path.basename(os.getcwd()) == 'Tools':
    os.chdir('..')
# Check if current folder contains a folder named "Tools"
elif 'Tools' in os.listdir():
    pass
else:
    print("Warning: Not currently in the 'Tools' folder. The script may not work properly.")

# Set the path to include the project root folder, so Scripts imports are valid
sys.path.insert(1, os.getcwd())
# ---------------------------------------------------------------------------------------

import subprocess as sp
import pathlib
import shutil
# Note: Require ffmpepg to be installed and in the PATH environment variable
from pydub import AudioSegment
import langcodes

from Scripts.utils import parseBool
from Scripts.shared_imports import *

# Auto fetch tracks from tracksFolder
tracksToAddDict = {}
for file in os.listdir(tracksFolder):
    if (file.endswith(".mp3") or file.endswith(".aac") or file.endswith(".wav")) and file != effectsTrackFileName:
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
soundEffectsDict = {'effects':effectsTrackFileName}
videoToProcess = os.path.join(tracksFolder, videoToProcess)
outputFile = os.path.join(tracksFolder, outputFile)
tempdir = os.path.join(tracksFolder, "temp")
mergedTracksDir = os.path.join(tracksFolder, "Merged Effects Tracks")

# Get number of tracks to add
numTracks = len(tracksToAddDict)

tempFilesToDelete = []

# Check if tracks are stereo, if not it will convert them to stereo before adding
def convert_to_stereo(tracksDict):
    # Key is the language code, value is the relative file path to audio track
    for langcode, fileName in tracksDict.items():
        filePath = os.path.join(tracksFolder, fileName)

        audio = AudioSegment.from_file(filePath)
        # Check the number of channels in the audio file
        num_channels = audio.channels
        if num_channels == 1:
            # Check if temp directory exists, if not create it
            if not os.path.exists(tempdir):
                os.makedirs(tempdir)
            # Get the file extension of the file without the period
            fileExtension = os.path.splitext(filePath)[1][1:]
            # convert to stereo
            stereo_file = audio.set_channels(2)
            # save the stereo file
            tempFilePath = f"{os.path.join(tempdir, fileName)}_stereo_temp.{fileExtension}" # Change this before publishing, needs to adapt to filetype

            # Determine the format needed for pydub to export
            if fileExtension == "aac":
                formatString = "adts"
            else:
                formatString = fileExtension

            # Export the file with appropriate format
            stereo_file.export(tempFilePath, format=formatString, bitrate="128k") # Change this before publishing, needs to adapt to filetype
            tracksDict[langcode] = tempFilePath

            # Add to list of files to delete later when done, unless need to save merged tracks
            if parseBool(useSoundEffectsTrack) and parseBool(saveMergedTracks) and langcode != "effects":
                pass
            else:
                tempFilesToDelete.append(tempFilePath)

        else:
            # File is already stereo, so just use the original file
            tracksDict[langcode] = filePath
    return tracksDict

print("\nChecking if tracks are stereo...")
tracksToAddDict = convert_to_stereo(tracksToAddDict)

# Use pydub to combine the sound effects track with each audio track
if parseBool(useSoundEffectsTrack):
    # Ensure the sound effects track is stereo, if not make it stereo
    soundEffectsDict = convert_to_stereo(soundEffectsDict)

    # Check if temp directory exists, if not create it
    if not os.path.exists(tempdir):
        os.makedirs(tempdir)

    # Check if temporary files for tracks already exist and use those, if not create them
    for langcode, filePath in tracksToAddDict.items():
        if "_stereo_temp" not in filePath:
            # Create the new filename and path for the temporary file
            fileExtension = os.path.splitext(filePath)[1][1:]
            fileName = os.path.basename(filePath)
            appendString = "_temp."+fileExtension
            tempFilePath = os.path.join(tempdir, fileName+appendString)
            shutil.copy(filePath, tempFilePath)
            tracksToAddDict[langcode] = tempFilePath
            # Add to list of files to delete later when done, unless set to save merged tracks
            if not parseBool(saveMergedTracks):
                tempFilesToDelete.append(tempFilePath)

    # Merge the sound effects into temporary track files
    print("\nMerging sound effects...")
    for langcode, trackFilePath in tracksToAddDict.items():
        soundEffects = AudioSegment.from_file(soundEffectsDict['effects'])
        audio = AudioSegment.from_file(trackFilePath)
        combined = audio.overlay(soundEffects)
        # Double check it is a temporary file
        if "_temp" in trackFilePath:
            # Get file extension
            fileExtension = os.path.splitext(trackFilePath)[1][1:]
            # Determine the format needed for pydub to export
            if fileExtension == "aac":
                formatString = "adts"
            else:
                formatString = fileExtension
            combined.export(trackFilePath, format=formatString, bitrate="128k")
        else:
            print("\n\nERROR: The script did not create a temporary file - cannot overwrite original file.")
            print("This should not happen and is a bug. Please report it here: https://github.com/ThioJoe/Auto-Synced-Translated-Dubs/issues")
            userInput = input("\nPress Enter to exit... ")
            sys.exit()
        
        # If set to save merged tracks, move the temporary file to the tracks folder
        if parseBool(saveMergedTracks):
            # If the merged tracks directory does not exist, create it
            if not os.path.exists(mergedTracksDir):
                os.makedirs(mergedTracksDir)
            # Get the filename from the temporary file path
            tempFileName = os.path.basename(trackFilePath)
            ext = os.path.splitext(trackFilePath)[1][1:]
            # Remove the _temp from the filename, also remove double extensions
            fileName = fileName.replace("_stereo_temp", "")
            fileName = tempFileName.replace("_temp", "")
            fileName = fileName.replace(f".{ext}.{ext}", f".{ext}")

            # Insert effects to the filename before the last " - "
            nameNoExt = os.path.splitext(fileName)[0]
            parsedLanguageCode = nameNoExt.split(' - ')[-1].strip()
            fileName = fileName.replace(parsedLanguageCode, f"With Effects - {parsedLanguageCode}")

            # Create the new file path
            newFilePath = os.path.join(mergedTracksDir, fileName)
            # Move the file
            shutil.move(trackFilePath, newFilePath)
            # Add the new file path to the tracksToAddDict
            tracksToAddDict[langcode] = newFilePath
        

# Create string for ffmpeg command for each string
#Example:    sp.run(f'ffmpeg -i "video.mp4" -i "audioTrack.mp3" -map 0 -map 1 -metadata:s:a:0 language=eng -metadata:s:a:1 language=spa -codec copy output.mp4')
# In metadata, a=audio, s=stream, 0=first stream, 1=second stream, etc  -  Also: g=global container, c=chapter, p=program
trackStringsCombined = ""
mapList = "-map 0"
metadataCombined = f'-metadata:s:a:0 language={defaultLanguage} -metadata:s:a:0 title="{defaultLanguage}" -metadata:s:a:0 handler_name="{defaultLanguage}"'
count = 1
for langcode, filePath in tracksToAddDict.items():
    languageDisplayName = langcodes.get(langcode).display_name()
    trackStringsCombined += f' -i "{filePath}"'
    metadataCombined += f' -metadata:s:a:{count} language={langcode}'
    metadataCombined += f' -metadata:s:a:{count} handler_name={languageDisplayName}' # Handler shows as the track title in MPC-HC
    metadataCombined += f' -metadata:s:a:{count} title="{languageDisplayName}"' # This is the title that will show up in the audio track selection menu
    mapList += f' -map {count}'
    count+=1

finalCommand = f'ffmpeg -i "{videoToProcess}" {trackStringsCombined} {mapList} {metadataCombined} -codec copy "{outputFile}"'

print("\n Adding audio tracks to video...")
sp.run(finalCommand)

# Delete temp files
print("\nDeleting temporary files...")
for file in tempFilesToDelete:
    os.remove(file)
# Delete temp directory
try:
    if os.path.exists(tempdir):
        os.rmdir(tempdir)
except OSError as e:
    print("Could not delete temp directory. It may not be empty.")

print("\nDone!")
