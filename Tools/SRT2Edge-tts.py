import asyncio
import edge_tts
import re
import os

version = '0.01.0'
print(f"\n------- SRT 2 Edge-tts script by Rafael Godoy Ebert Release version {version} -------\n")

VOICE_MAP = {
    'en': 'en-US-EricNeural',
    'es': 'es-ES-AlvaroNeural',
    'fr': 'fr-FR-HenriNeural',
    'pt': 'pt-BR-AntonioNeural'
}

OUTPUT_FOLDER = "TTS"

async def generate_tts(text, output_file, voice):
    communicate = edge_tts.Communicate(text, voice)
    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]
    with open(output_file, "wb") as audio_file:
        audio_file.write(audio_data)

def get_language(file_name):
    # Extract language code from the file name
    match = re.search(r'\b(fr|es|en|pt)\b', file_name, re.I)
    if match:
        return match.group().lower()
    if not match:
        print("----- Idioma não identificado. Coloque o código do idioma (en, es, fr, pt) no início do nome do arquivo .srt. -----\n")
        return
    return None
    

async def amain() -> None:
    for file_name in os.listdir("."):
        if file_name.lower().endswith(".srt"):
            lang_code = get_language(file_name)
            if lang_code and lang_code in VOICE_MAP:
                voice = VOICE_MAP[lang_code]
                
                output_folder = os.path.join(".", f"TTS-{file_name}")
                if not os.path.exists(output_folder):
                    os.makedirs(output_folder)

                srt_file_path = os.path.join(".", file_name)
                with open(srt_file_path, "r", encoding="utf-8") as subtitle_file:
                    subtitle_blocks = subtitle_file.read().split("\n\n")
                    total_blocks = len(subtitle_blocks)

                    for idx, block in enumerate(subtitle_blocks, start=1):
                        lines = block.split("\n")
                        if len(lines) >= 3:
                            subtitle_num = idx  # Usar o índice do bloco como número do áudio
                            timestamp = lines[1]
                            text = " ".join(lines[2:])
                            tts_output_file = os.path.join(output_folder, f"{subtitle_num}.mp3")
                            await generate_tts(text, tts_output_file, voice)

                            print(f"\rTranscrevendo áudio {subtitle_num} de {total_blocks} para o idioma {lang_code}", end="", flush=True)

                    print(f"\nIdioma {lang_code} finalizado.\n")

    print('Programa finalizado')  # Adicionar uma nova linha para evitar sobreposição com a próxima mensagem

def main():
    asyncio.run(amain())

if __name__ == "__main__":
    main()