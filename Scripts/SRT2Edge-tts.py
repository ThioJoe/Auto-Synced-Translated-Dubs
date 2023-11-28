import asyncio
import edge_tts
import re
import os
import sys
from voice_map import SUPPORTED_VOICES

async def generate_tts(text, output_file, voice, subtitle_num):
    communicate = edge_tts.Communicate(text, voice)
    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]
    with open(output_file, "wb") as audio_file:
        audio_file.write(audio_data)

async def amain(text, languageCode, output_folder, subtitle_num) -> None:
    try:
        voice = SUPPORTED_VOICES[languageCode]
    except Exception as e:
        print(f"Exceção: {e}")

    if voice:
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        tts_output_file = os.path.join(output_folder, f"{subtitle_num}.mp3")

        await generate_tts(text, tts_output_file, voice, subtitle_num)

    else:
        print(f"Idioma {languageCode} não suportado.")
        print(f"Lang Code: '{languageCode}'")
        print(f"Voice: {voice}")

def main():
    if len(sys.argv) != 5:
        print("Uso: python srt2edge-tts.py <texto> <lang_code> <output_folder> <subtitle_num>")
        sys.exit(1)

    text = sys.argv[1]
    lang_code = sys.argv[2]
    output_folder = sys.argv[3]
    subtitle_num = sys.argv[4]

    # Define output_folder para a pasta "workingFolder" um nível acima do diretório atual
    output_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'workingFolder'))

    asyncio.run(amain(text, lang_code, output_folder, subtitle_num))

if __name__ == "__main__":
    main()
