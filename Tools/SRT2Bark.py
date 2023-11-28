import os
import re
from bark import SAMPLE_RATE, generate_audio, preload_models
from scipy.io.wavfile import write as write_wav

# Baixar e carregar todos os modelos
preload_models()

# Função para gerar áudio a partir do texto com o speaker especificado
def generate_and_save_audio(text, index, history_prompt="v2/pt_speaker_9"):
    audio_array = generate_audio(text, history_prompt=history_prompt)
    write_wav(f"TTS/{index}.wav", SAMPLE_RATE, audio_array)
    return audio_array

# Identificar o arquivo SRT na pasta atual
srt_files = [file for file in os.listdir() if file.endswith(".srt")]

# Verificar se a pasta TTS existe, se não, criá-la
if not os.path.exists('TTS'):
    os.makedirs('TTS')

# Iterar sobre os arquivos SRT encontrados
for srt_file in srt_files:
    # Abrir o arquivo SRT
    with open(srt_file, 'r', encoding='utf-8') as file:
        srt_content = file.read()

    # Dividir o conteúdo do arquivo SRT em legendas
    subtitles = re.split(r'\n(?=\d+\n)', srt_content)

    # Iterar sobre as legendas
    for subtitle in subtitles:
        lines = subtitle.strip().split('\n')
        index = lines[0]
        text = ' '.join(lines[2:])

        # Gerar o áudio para o texto da legenda com o speaker especificado e salvar
        generate_and_save_audio(text, index, history_prompt="v2/pt_speaker_9")

        print(f"Gerado áudio para índice {index} no arquivo {srt_file}: {text}")
