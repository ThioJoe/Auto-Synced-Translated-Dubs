import tkinter as tk
from tkinter import filedialog, ttk
import subprocess
import configparser
from i18n import I18nAuto
i18n = I18nAuto()

# Função para abrir a caixa de diálogo de arquivo e preencher o campo de entrada
def open_file_dialog(file_entry, initial_path=""):
    file_path = filedialog.askopenfilename(initialdir=initial_path)
    if file_path:
        file_entry.delete(0, tk.END)
        file_entry.insert(0, file_path)

# Função para executar o código 'python main.py'
def run_main_code():
    # Implemente a lógica para executar o código 'python main.py'
    # Certifique-se de que os arquivos .ini estejam atualizados antes de executar o código.

    # Exemplo:
    subprocess.run(['python', 'main.py'])

    print(i18n("Código executado com sucesso."))

# Função para adicionar o conteúdo de idiomas.ini no final de batch.ini
def add_idiomas_to_batch():
    # Leia o conteúdo de idiomas.ini
    with open('idiomas.ini', 'r') as idiomas_file:
        idiomas_content = idiomas_file.read()
    
    # Abra o arquivo batch.ini e adicione o conteúdo de idiomas.ini no final
    with open('batch.ini', 'a') as batch_file:
        batch_file.write(idiomas_content)

def save_settings():
    # Salvar configurações em batch.ini
    config_batch = configparser.ConfigParser()
    config_batch['SETTINGS'] = {
        'enabled_languages': enabled_languages_var.get(),
        'original_video_file_path': original_video_file_path_var.get(),
        'srt_file_path': srt_file_path_var.get()
    }

    with open('batch.ini', 'w') as batch_file:
        config_batch.write(batch_file)
    
    add_idiomas_to_batch()

    # Salvar configurações em cloud_service_settings.ini
    config_cloud = configparser.ConfigParser()
    config_cloud['CLOUD'] = {
        'tts_service': tts_service_var.get(),
        'translate_service': translate_service_var.get(),
        'use_fallback_google_translate': use_fallback_google_translate_var.get(),
        'batch_tts_synthesize': batch_tts_synthesize_var.get(),
        'google_project_id': google_project_id_var.get(),
        'deepl_api_key': deepl_api_key_var.get(),
        'azure_api_key': azure_speech_key_var.get(),  # Corrigir a variável aqui
        'azure_speech_key': azure_speech_key_var.get(),
        'azure_speech_region': azure_speech_region_var.get()
    }

    with open('cloud_service_settings.ini', 'w') as cloud_file:
        config_cloud.write(cloud_file)

    # Salvar configurações em config.ini
    config_config = configparser.ConfigParser()
    config_config['SETTINGS'] = {
        'skip_translation': skip_translation_var.get(),
        'skip_synthesize': skip_synthesize_var.get(),
        'stop_after_translation': stop_after_translation_var.get(),
        'two_pass_voice_synth': two_pass_voice_synth_var.get(),
        'force_stretch_with_twopass': force_stretch_with_twopass_var.get(),
        'debug_mode': debug_mode_var.get(),
        'original_language': original_language_entry.get(),
        'formality_preference': formality_preference_var.get(),
        'output_format': output_format_var.get(),
        'synth_audio_encoding': synth_audio_encoding_var.get(),
        'azure_comma_pause': azure_comma_pause_var.get(),
        'synth_sample_rate': synth_sample_rate_var.get(),
        'combine_subtitles_max_chars': combine_subtitles_max_chars_var.get(),
        'add_line_buffer_milliseconds': add_line_buffer_milliseconds_var.get(),
        'azure_sentence_pause': azure_sentence_pause_var.get()
    }
    with open('config.ini', 'w') as config_file:
        config_config.write(config_file)

    print(i18n("Configurações salvas com sucesso."))

# Lê as configurações dos arquivos INI e define os valores iniciais nos campos
def read_ini_settings():
    # Lê as configurações de batch.ini
    config_batch = configparser.ConfigParser()
    config_batch.read('batch.ini')

    enabled_languages_entry.insert(0, config_batch['SETTINGS']['enabled_languages'])
    original_video_entry.insert(0, config_batch['SETTINGS']['original_video_file_path'])
    srt_entry.insert(0, config_batch['SETTINGS']['srt_file_path'])

    # Lê as configurações de cloud_service_settings.ini
    config_cloud = configparser.ConfigParser()
    config_cloud.read('cloud_service_settings.ini')
    tts_service_var.set(config_cloud['CLOUD']['tts_service'])
    translate_service_var.set(config_cloud['CLOUD']['translate_service'])
    use_fallback_google_translate_var.set(config_cloud['CLOUD'].getboolean('use_fallback_google_translate'))
    batch_tts_synthesize_var.set(config_cloud['CLOUD'].getboolean('batch_tts_synthesize'))
    google_project_id_var.set(config_cloud['CLOUD']['google_project_id'])
    deepl_api_key_var.set(config_cloud['CLOUD']['deepl_api_key'])
    azure_speech_key_var.set(config_cloud['CLOUD']['azure_speech_key'])
    azure_speech_region_var.set(config_cloud['CLOUD']['azure_speech_region'])

    # Lê as configurações de config.ini
    config_config = configparser.ConfigParser()
    config_config.read('config.ini')
    
    skip_translation_var.set(config_config['SETTINGS'].getboolean('skip_translation'))
    skip_synthesize_var.set(config_config['SETTINGS'].getboolean('skip_synthesize'))
    stop_after_translation_var.set(config_config['SETTINGS'].getboolean('stop_after_translation'))
    two_pass_voice_synth_var.set(config_config['SETTINGS'].getboolean('two_pass_voice_synth'))
    force_stretch_with_twopass_var.set(config_config['SETTINGS'].getboolean('force_stretch_with_twopass'))
    debug_mode_var.set(config_config['SETTINGS'].getboolean('debug_mode'))
    
    original_language_entry.delete(0, tk.END)  # Limpa o campo de entrada
    original_language_entry.insert(0, config_config['SETTINGS']['original_language'])
    
    formality_preference_var.set(config_config['SETTINGS']['formality_preference'])
    output_format_var.set(config_config['SETTINGS']['output_format'])

    # Corrija synth_audio_encoding_var para definir como StringVar
    synth_audio_encoding_var.set(config_config['SETTINGS']['synth_audio_encoding'])
    
    azure_comma_pause_var.set("")
    azure_comma_pause_var.set(config_config['SETTINGS']['azure_comma_pause'])

    
    synth_sample_rate_var.delete(0, tk.END)  # Limpa o campo de entrada
    synth_sample_rate_var.insert(0, config_config['SETTINGS']['synth_sample_rate'])
    
    combine_subtitles_max_chars_var.delete(0, tk.END)
    combine_subtitles_max_chars_var.insert(0, config_config['SETTINGS']['combine_subtitles_max_chars'])
    
    add_line_buffer_milliseconds_var.delete(0, tk.END)
    add_line_buffer_milliseconds_var.insert(0, config_config['SETTINGS']['add_line_buffer_milliseconds'])
    
    azure_sentence_pause_var.delete(0, tk.END)  # Limpa o campo de entrada
    azure_sentence_pause_var.insert(0, config_config['SETTINGS']['azure_sentence_pause'])

# Cria a janela principal
root = tk.Tk()
root.title(i18n("Configurar Auto Synced Translated Dubs || UI"))

# Defina todas as variáveis do Tkinter aqui
original_video_file_path_var = tk.StringVar()
srt_file_path_var = tk.StringVar()
azure_speech_region_var = tk.StringVar()
azure_speech_key_var = tk.StringVar()
projeto_id_var = tk.StringVar()
enabled_languages_var = tk.StringVar()
original_video_var = tk.StringVar()
srt_var = tk.StringVar()
tts_service_var = tk.StringVar()
translate_service_var = tk.StringVar()
use_fallback_google_translate_var = tk.BooleanVar()
batch_tts_synthesize_var = tk.BooleanVar()
skip_translation_var = tk.BooleanVar()
skip_synthesize_var = tk.BooleanVar()
stop_after_translation_var = tk.BooleanVar()
two_pass_voice_synth_var = tk.BooleanVar()
force_stretch_with_twopass_var = tk.BooleanVar()
debug_mode_var = tk.BooleanVar()
original_language_var = tk.StringVar()
formality_preference_var = tk.StringVar()
output_format_var = tk.StringVar()
synth_audio_encoding_var = tk.StringVar()
azure_comma_pause_var = tk.StringVar()
synth_sample_rate_var = tk.StringVar()
combine_subtitles_max_chars_var = tk.StringVar()
add_line_buffer_milliseconds_var = tk.StringVar()
azure_sentence_pause_var = tk.StringVar()

# Frame para batch.ini
from tkinter import ttk
frame_batch = tk.LabelFrame(root, text=i18n("Configurações em batch.ini"))
frame_batch.pack(pady=10, padx=10, fill='both')

enabled_languages_label = tk.Label(frame_batch, text=i18n("Número de idiomas habilitados:"))
enabled_languages_label.grid(row=0, column=0)
enabled_languages_entry = tk.Entry(frame_batch, textvariable=enabled_languages_var)
enabled_languages_entry.grid(row=0, column=1)
enabled_languages_label.config(anchor='w')

original_video_label = tk.Label(frame_batch, text=i18n("Caminho do vídeo original:"), anchor='w')
original_video_label.grid(row=1, column=0)
original_video_entry = tk.Entry(frame_batch, textvariable=original_video_file_path_var)
original_video_entry.grid(row=1, column=1)


original_video_button = tk.Button(frame_batch, text=i18n("Procurar"), command=lambda: open_file_dialog(original_video_entry))
original_video_button.grid(row=1, column=2)  # Adicione um botão "Procurar" ao lado do campo de entrada

srt_label = tk.Label(frame_batch, text=i18n("Caminho do arquivo SRT:"), anchor='w')
srt_label.grid(row=2, column=0)
srt_entry = tk.Entry(frame_batch, textvariable=srt_file_path_var)
srt_entry.grid(row=2, column=1)

srt_button = tk.Button(frame_batch, text=i18n("Procurar"), command=lambda: open_file_dialog(srt_entry))
srt_button.grid(row=2, column=2)  # Adicione um botão "Procurar" ao lado do campo de entrada

# Frame para cloud_service_settings.ini
frame_cloud = tk.LabelFrame(root, text=i18n("Configurações em cloud_service_settings.ini"))
frame_cloud.pack(pady=10, padx=10, fill='both')

tts_service_label = tk.Label(frame_cloud, text=i18n("Serviço de TTS:"))
tts_service_label.grid(row=0, column=0)
tts_service_var = tk.StringVar()
tts_service_combo = ttk.Combobox(frame_cloud, textvariable=tts_service_var, values=["Azure", "Google"])
tts_service_combo.grid(row=0, column=1)

translate_service_label = tk.Label(frame_cloud, text=i18n("Serviço de Tradução:"))
translate_service_label.grid(row=1, column=0)
translate_service_var = tk.StringVar()
translate_service_combo = ttk.Combobox(frame_cloud, textvariable=translate_service_var, values=["Google", "DeepL"])
translate_service_combo.grid(row=1, column=1)

use_fallback_label = tk.Label(frame_cloud, text=i18n("Usar Google Translate como fallback:"))
use_fallback_label.grid(row=2, column=0)
use_fallback_google_translate_var = tk.BooleanVar()
use_fallback_check = tk.Checkbutton(frame_cloud, variable=use_fallback_google_translate_var)
use_fallback_check.grid(row=2, column=1)

# Adicione as opções ausentes
google_project_id_label = tk.Label(frame_cloud, text=i18n("Projeto ID da Google Cloud:"))
google_project_id_label.grid(row=3, column=0)
google_project_id_var = tk.StringVar()  # Adicione a variável correspondente
google_project_id_entry = tk.Entry(frame_cloud, textvariable=google_project_id_var)  # Defina a variável no Entry
google_project_id_entry.grid(row=3, column=1)

deepl_api_key_label = tk.Label(frame_cloud, text=i18n("Chave da API da DeepL:"))
deepl_api_key_label.grid(row=4, column=0)
deepl_api_key_var = tk.StringVar()  # Adicione a variável correspondente
deepl_api_key_entry = tk.Entry(frame_cloud, textvariable=deepl_api_key_var)  # Defina a variável no Entry
deepl_api_key_entry.grid(row=4, column=1)

azure_speech_key_label = tk.Label(frame_cloud, text=i18n("Chave da API do Azure Speech:"))
azure_speech_key_label.grid(row=5, column=0)
azure_speech_key_entry = tk.Entry(frame_cloud, textvariable=azure_speech_key_var)
azure_speech_key_entry.grid(row=5, column=1)

azure_speech_region_label = tk.Label(frame_cloud, text=i18n("Região do Azure Speech:"))
azure_speech_region_label.grid(row=6, column=0)
azure_speech_region_var = tk.StringVar()  # Adicione a variável correspondente
azure_speech_region_entry = tk.Entry(frame_cloud, textvariable=azure_speech_region_var)  # Defina a variável no Entry
azure_speech_region_entry.grid(row=6, column=1)

# Frame para config.ini
frame_config = tk.LabelFrame(root, text=i18n("Configurações em config.ini"))
frame_config.pack(pady=10, padx=10, fill='both')

skip_translation_label = tk.Label(frame_config, text=i18n("Pular Tradução:"))
skip_translation_label.grid(row=0, column=0)
skip_translation_var = tk.BooleanVar()
skip_translation_check = tk.Checkbutton(frame_config, variable=skip_translation_var)
skip_translation_check.grid(row=0, column=1)

skip_synthesize_label = tk.Label(frame_config, text=i18n("Pular Síntese:"))
skip_synthesize_label.grid(row=1, column=0)
skip_synthesize_var = tk.BooleanVar()
skip_synthesize_check = tk.Checkbutton(frame_config, variable=skip_synthesize_var)
skip_synthesize_check.grid(row=1, column=1)

stop_after_translation_label = tk.Label(frame_config, text=i18n("Parar após Tradução:"))
stop_after_translation_label.grid(row=2, column=0)
stop_after_translation_var = tk.BooleanVar()
stop_after_translation_check = tk.Checkbutton(frame_config, variable=stop_after_translation_var)
stop_after_translation_check.grid(row=2, column=1)

two_pass_voice_synth_label = tk.Label(frame_config, text=i18n("Síntese de Voz em Duas Etapas:"))
two_pass_voice_synth_label.grid(row=3, column=0)
two_pass_voice_synth_var = tk.BooleanVar()
two_pass_voice_synth_check = tk.Checkbutton(frame_config, variable=two_pass_voice_synth_var)
two_pass_voice_synth_check.grid(row=3, column=1)

force_stretch_with_twopass_label = tk.Label(frame_config, text=i18n("Forçar esticamento na segunda etapa:"))
force_stretch_with_twopass_label.grid(row=4, column=0)
force_stretch_with_twopass_var = tk.BooleanVar()
force_stretch_with_twopass_check = tk.Checkbutton(frame_config, variable=force_stretch_with_twopass_var)
force_stretch_with_twopass_check.grid(row=4, column=1)

debug_mode_label = tk.Label(frame_config, text=i18n("Modo de Depuração:"))
debug_mode_label.grid(row=5, column=0)
debug_mode_var = tk.BooleanVar()
debug_mode_check = tk.Checkbutton(frame_config, variable=debug_mode_var)
debug_mode_check.grid(row=5, column=1)

original_language_label = tk.Label(frame_config, text=i18n("Idioma Original:"))
original_language_label.grid(row=6, column=0)
original_language_entry = tk.Entry(frame_config)
original_language_entry.grid(row=6, column=1)

formality_preference_label = tk.Label(frame_config, text=i18n("Preferência de Formalidade:"))
formality_preference_label.grid(row=7, column=0)
formality_preference_var = tk.StringVar()
formality_preference_combo = ttk.Combobox(frame_config, textvariable=formality_preference_var, values=["default", "more", "less"])
formality_preference_combo.grid(row=7, column=1)

output_format_label = tk.Label(frame_config, text=i18n("Formato de Saída:"))
output_format_label.grid(row=8, column=0)
output_format_var = tk.StringVar()
output_format_combo = ttk.Combobox(frame_config, textvariable=output_format_var, values=["mp3", "aac", "wav"])
output_format_combo.grid(row=8, column=1)

audio_encoding_options = ["mp3", "wav", "aac"]
synth_audio_encoding_label = tk.Label(frame_config, text=i18n("Codificação de Áudio de Síntese:"))
synth_audio_encoding_label.grid(row=9, column=0)
synth_audio_encoding_var = tk.StringVar()
synth_audio_encoding_combo = ttk.Combobox(frame_config, textvariable=synth_audio_encoding_var, values=audio_encoding_options)
synth_audio_encoding_combo.grid(row=9, column=1)

azure_sentence_pause_label = tk.Label(frame_config, text=i18n("Pausa após período (Azure):"))
azure_sentence_pause_label.grid(row=13, column=0)
azure_sentence_pause_var = tk.Entry(frame_config)
azure_sentence_pause_var.grid(row=13, column=1)

synth_sample_rate_label = tk.Label(frame_config, text=i18n("Taxa de Amostragem de Síntese:"))
synth_sample_rate_label.grid(row=15, column=0)
synth_sample_rate_var = tk.Entry(frame_config)
synth_sample_rate_var.grid(row=15, column=1)

combine_subtitles_max_chars_label = tk.Label(frame_config, text=i18n("Máximo de caracteres para combinar legendas:"))
combine_subtitles_max_chars_label.grid(row=12, column=0)
combine_subtitles_max_chars_var = tk.Entry(frame_config)
combine_subtitles_max_chars_var.grid(row=12, column=1)

add_line_buffer_milliseconds_label = tk.Label(frame_config, text=i18n("Buffer de Linha em Milissegundos:"))
add_line_buffer_milliseconds_label.grid(row=13, column=0)
add_line_buffer_milliseconds_var = tk.Entry(frame_config)
add_line_buffer_milliseconds_var.grid(row=13, column=1)

azure_sentence_pause_label = tk.Label(frame_config, text=i18n("Pausa após período (Azure):"))
azure_sentence_pause_label.grid(row=14, column=0)
azure_sentence_pause_var = tk.Entry(frame_config)
azure_sentence_pause_var.grid(row=14, column=1)

# Botões
save_button = tk.Button(root, text=i18n("Salvar Configurações"), command=save_settings)
save_button.pack(pady=10)

run_button = tk.Button(root, text=i18n("Executar"), command=run_main_code)
run_button.pack(pady=10)

# Rótulo para exibir os créditos
credits_label = tk.Label(root, text="Auto-Synced Translated Dubs 14.1\nDesenvolvido por ThioJoe\nUI Rafael Godoy Ebert\nCopyright © 2023")
credits_label.pack(side="bottom")

# Chame a função para ler as configurações dos arquivos INI e definir os valores iniciais nos campos
read_ini_settings()

root.mainloop()
