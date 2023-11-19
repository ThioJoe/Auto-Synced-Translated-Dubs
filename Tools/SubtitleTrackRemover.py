# This script prompts the user to input a video ID, and then it lists the caption tracks and their IDs. The user can then input one or more caption IDs separated by commas to delete the selected captions.

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

import Scripts.auth as auth

YOUTUBE_API = auth.youtube_authentication()

def get_video_info(videoID):
    response = YOUTUBE_API.videos().list(
        part = "snippet,localizations",
        id = videoID
    ).execute()
    #return response
    snippet = response["items"][0]["snippet"]
    localizations = response["items"][0]["localizations"]
    return snippet, localizations

def list_captions(videoID):
    results = auth.YOUTUBE_API.captions().list(
        part="snippet",
        videoId=videoID
    ).execute()
    return results
	
def delete_caption_track(videoID, captionID):
    delete_result = auth.YOUTUBE_API.captions().delete(
        id=captionID
    ).execute()
    return delete_result

def main():
    print("\nEnter a video ID to get a list of the subtitle tracks on the video. You will then have the option to delete any of the tracks.")

    videoID = input("\nEnter the Video ID: ")

    # Get video information
    snippet, localizations = get_video_info(videoID)

    # List captions
    captions = list_captions(videoID)
    print("\nCaption tracks:")
    for index, item in enumerate(captions["items"]):
        name = item["snippet"]["name"] if not item["snippet"]["name"]=="" else "[No Track Name]"
        print(f'{index + 1}. {name} ({item["snippet"]["language"]}): {item["id"]}')

    # Delete captions
    selected_indices = input("\nEnter the index numbers of the subtitles to delete (separated by commas): ")
    indices = [int(index.strip()) - 1 for index in selected_indices.split(',')]

    for index in indices:
        captionID = captions["items"][index]["id"]
        delete_result = delete_caption_track(videoID, captionID)
        print(f"Deleted caption {captionID}")

if __name__ == "__main__":
    main()