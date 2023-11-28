import os
import asyncio
from bark import SAMPLE_RATE, generate_audio, preload_models
from scipy.io.wavfile import write as write_wav
from pydub import AudioSegment
import sys

# Carrega os modelos uma única vez
preload_models()

# Função para gerar áudio a partir do texto com o speaker especificado
def generate_and_save_audio(text, subtitle_num, output_folder, hide_progress=True, history_prompt="v2/pt_speaker_9"):
    audio_array = generate_audio(text, history_prompt=history_prompt, silent=hide_progress)
    
    wav_file = f"{output_folder}/{subtitle_num}.wav"
    mp3_file = f"{output_folder}/{subtitle_num}.mp3"
    
    write_wav(wav_file, SAMPLE_RATE, audio_array)
    
    # Converte o arquivo WAV para MP3
    audio_segment = AudioSegment.from_wav(wav_file)
    audio_segment.export(mp3_file, format="mp3")
    
    # Remove o arquivo WAV
    os.remove(wav_file)
    
    return audio_array

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
    
    for _ in range(2):  # Modificar para o número desejado de iterações
        generate_and_save_audio(text, subtitle_num, output_folder)

if __name__ == "__main__":
    main()
