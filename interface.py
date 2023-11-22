import tkinter as tk
from tkinter import ttk
from tkinter import filedialog, ttk
import subprocess
import configparser
from i18n import I18nAuto
from version import version
import os
i18n = I18nAuto()

#version = 1

# Função para abrir a caixa de diálogo de arquivo e preencher o campo de entrada
def open_file_dialog(file_entry, initial_path=""):
    file_path = filedialog.askopenfilename(initialdir=initial_path)
    if file_path:
        file_entry.delete(0, tk.END)
        file_entry.insert(0, file_path)

# Função para executar o código 'python main.py'
def run_main_code():
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

# Obtendo o caminho do diretório do script
diretorio_script = os.path.dirname(os.path.abspath(__file__))

# Construindo o caminho para a imagem na mesma pasta
caminho_information = os.path.join(diretorio_script, "information.png")

# Função para criar um tooltip
def criar_tooltip(widget, texto):
    def mostrar_tooltip(_):
        tooltip = tk.Toplevel(widget)
        tooltip.wm_overrideredirect(True)
        tooltip.wm_geometry(f"+{widget.winfo_rootx() + 25}+{widget.winfo_rooty() + 25}")

        label = tk.Label(tooltip, text=texto, justify='left', background='#ffffe0', relief='solid', borderwidth=1)
        label.pack(ipadx=1)

        def fechar_tooltip(_=None):
            tooltip.destroy()

        tooltip.bind("<Enter>", fechar_tooltip)
        widget.bind("<Leave>", fechar_tooltip)

    widget.bind("<Enter>", mostrar_tooltip)

# Função para criar uma PhotoImage redimensionada
def criar_imagem(caminho, largura=None, altura=None):
    imagem = tk.PhotoImage(file=caminho)
    
    # Redimensionar apenas se largura e altura forem especificadas
    if largura is not None and altura is not None:
        imagem = imagem.subsample(int(imagem.width() / largura), int(imagem.height() / altura))
    
    return imagem

from tkinter import Menu
# Função para exibir os créditos
def show_credits():
    credits_window = tk.Toplevel(root)
    credits_window.title('Créditos')

    # Defina o tamanho da janela de créditos
    credits_window.geometry('400x200')  # Ajuste os valores conforme necessário

    # Adicione informações de créditos aqui
    credits_label = tk.Label(credits_window, text=f'{i18n("script by")} ThioJoe\ngithub.com/ThioJoe/Auto-Synced-Translated-Dubs\n\nUI {i18n("e adaptações por")} Rafael Godoy Ebert\nGitHub: RafaelGodoyEbert\nTwitter/X: GodoyEbert\nInstagram: rafael.godoy.ebert\n\n{i18n("Release version")} {version}\nCopyright © 2023')
    credits_label.pack(padx=20, pady=10)

# Cria a janela principal
root = tk.Tk()
root.title(i18n("Configurar Auto Synced Translated Dubs || UI"))

# Crie uma barra de menus
menubar = tk.Menu(root)
root.config(menu=menubar)

# Crie um notebook (aba) para o conteúdo principal
notebook = ttk.Notebook(root)
notebook.pack(fill='both', expand=True)

# Crie um menu "File"
file_menu = tk.Menu(menubar)

# Adicione o menu "File" à barra de menus
menubar.add_cascade(label="File", menu=file_menu)

# # Adicione um submenu
# sub_menu = tk.Menu(file_menu, tearoff=0)
# sub_menu.add_command(label='One Page', command=lambda: change_page_preference('One Page'))
# sub_menu.add_command(label='With Tabs', command=lambda: change_page_preference('With Tabs'))

# # Adicione o submenu "Preferences" ao menu "File"
# file_menu.add_cascade(label="Preferences", menu=sub_menu)

# Adicione um item de menu para sair
file_menu.add_command(label=i18n('Exit'), command=root.destroy)

# Adicione um item de menu para créditos diretamente na barra de menus
menubar.add_command(label=i18n('Créditos'), command=show_credits)

# Frame para batch.ini
frame_batch = ttk.Frame(notebook)
notebook.add(frame_batch, text=i18n("batch.ini"))

# Frame para cloud_service_settings.ini
frame_cloud = ttk.Frame(notebook)
notebook.add(frame_cloud, text=i18n("cloud_service_settings.ini"))

# Frame para config.ini
frame_config = ttk.Frame(notebook)
notebook.add(frame_config, text=i18n("config.ini"))

# # Frame para config.ini
# frame_TrackAdder = ttk.Frame(notebook)
# notebook.add(frame_TrackAdder, text=i18n("TrackAdder.py"))

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

# Adaptações para o frame de batch.ini
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

# Adaptações para o frame de cloud_service_settings.ini
tts_service_label = tk.Label(frame_cloud, text=i18n("Serviço de TTS:"))
tts_service_label.grid(row=0, column=0)
tts_service_var = tk.StringVar()
tts_service_combo = ttk.Combobox(frame_cloud, textvariable=tts_service_var, values=["Azure", "Google", "edge", "bark"])
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

# Adaptações para o frame de config.ini
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

#===========================TOOLTIPS===========================
#batch.ini
# Adicionando ícone e tooltip para o campo "Número de idiomas habilitados"
info_icon_languages = criar_imagem(caminho_information, 20, 20)
info_label_languages = ttk.Label(frame_batch, image=info_icon_languages)
info_label_languages.grid(row=0, column=3, padx=(5, 0))  # Ajuste o valor de padx conforme necessário
criar_tooltip(info_label_languages, f"{i18n('Número de idiomas habilitados: Informe o número de idiomas que serão processados.')}\n{i18n('Definido pelo arquivo')} idiomas.py\n\n en-US(0)\n es-MX(1)\n hi-IN(2)\n ar-EG(3)\n ru-RU(4)\n pt-BR(5)\n it-IT(6)\n id-ID(7)\n ja-JP(8)\n ko-KR(9)\n de-DE(10)\n zh-CN(11)\n tr-TR(12)\n fr-FR(13)\n\n {i18n('Se você quiser, você pode adicionar mais no arquivo')} idioma.py")

# Adicionando ícone e tooltip para o campo "Caminho do vídeo original"
info_icon_video = criar_imagem(caminho_information, 20, 20)
info_label_video = ttk.Label(frame_batch, image=info_icon_video)
info_label_video.grid(row=1, column=3, padx=(5, 0))  # Ajuste o valor de padx conforme necessário
criar_tooltip(info_label_video, i18n("Caminho do vídeo original: Informe o caminho para o arquivo de vídeo de origem que esteja em MP4."))

# Adicionando ícone e tooltip para o campo "Caminho do arquivo SRT"
info_icon_srt = criar_imagem(caminho_information, 20, 20)
info_label_srt = ttk.Label(frame_batch, image=info_icon_srt)
info_label_srt.grid(row=2, column=3, padx=(5, 0))  # Ajuste o valor de padx conforme necessário
criar_tooltip(info_label_srt, i18n("Caminho do arquivo SRT: Informe o caminho para o arquivo de legenda no formato SRT."))

#clound.ini
# Adicionando ícone e tooltip para o campo "Serviço de TTS"
info_tts_service = criar_imagem(caminho_information, 20, 20)
info_label_tts_service = ttk.Label(frame_cloud, image=info_icon_srt)
info_label_tts_service.grid(row=0, column=4, padx=(5, 0))  # Ajuste o valor de padx conforme necessário
criar_tooltip(info_label_tts_service, f"{i18n('Escolha o Serviço de TTS que deseja utilizar, Google e Azure é obrigatório por a API')}\n\n{i18n('Bark Utiliza 100% de VRAM de uma 3060 e demora em média 1 minuto pra gerar cada linha de áudio')}\n\n{i18n('Bark e Edge não há necessidade de API')}")

# Adicionando ícone e tooltip para o campo "Serviço de Tradução"
info_translate_service = criar_imagem(caminho_information, 20, 20)
info_label_translate_service = ttk.Label(frame_cloud, image=info_translate_service)
info_label_translate_service.grid(row=1, column=4, padx=(5, 0))  
criar_tooltip(info_label_translate_service, f"{i18n('Qual serviço de tradução você usará? DeepL é mais lento, mas mais preciso')}\n\n{i18n('Nota: Se você pular a tradução, não é necessário')}")

# Adicionando ícone e tooltip para o campo "Usar Fallback"
info_use_fallback = criar_imagem(caminho_information, 20, 20)
info_label_use_fallback = ttk.Label(frame_cloud, image=info_use_fallback)
info_label_use_fallback.grid(row=2, column=4, padx=(5, 0))  
criar_tooltip(info_label_use_fallback, i18n("Caso o idioma de tradução não seja suportado pelo DeepL, use o Google Translate como alternativa. Ignorado se o translate_service estiver definido como google."))

# Adicionando ícone e tooltip para o campo "ID do Projeto Google"
info_google_project_id = criar_imagem(caminho_information, 20, 20)
info_label_google_project_id = ttk.Label(frame_cloud, image=info_google_project_id)
info_label_google_project_id.grid(row=3, column=4, padx=(5, 0))  
criar_tooltip(info_label_google_project_id, i18n("O nome/ID do projeto no console do Google Cloud. Necessário para traduzir"))

# Adicionando ícone e tooltip para o campo "Chave da API DeepL"
info_deepl_api_key = criar_imagem(caminho_information, 20, 20)
info_label_deepl_api_key = ttk.Label(frame_cloud, image=info_deepl_api_key)
info_label_deepl_api_key.grid(row=4, column=4, padx=(5, 0))  
criar_tooltip(info_label_deepl_api_key, i18n("Chave da API DeepL: Informe a chave da API para o serviço de tradução DeepL. Obrigatório para tradução 'deepl' estiver selecionado"))

# Adicionando ícone e tooltip para o campo "Chave da API do Azure Speech"
info_azure_speech_key = criar_imagem(caminho_information, 20, 20)
info_label_azure_speech_key = ttk.Label(frame_cloud, image=info_azure_speech_key)
info_label_azure_speech_key.grid(row=5, column=4, padx=(5, 0))  
criar_tooltip(info_label_azure_speech_key, i18n("Chave de API para seu recurso de fala no Azure (fala cognitiva)"))

# Adicionando ícone e tooltip para o campo "Região do Azure Speech"
info_azure_speech_region = criar_imagem(caminho_information, 20, 20)
info_label_azure_speech_region = ttk.Label(frame_cloud, image=info_azure_speech_region)
info_label_azure_speech_region.grid(row=6, column=4, padx=(5, 0))  
criar_tooltip(info_label_azure_speech_region, f"{i18n('O local/região do recurso de fala. Isso deve estar listado na mesma página que as chaves de API.')}\n\n {i18n('Exemplo:')} brazilsouth")

#config.ini
# Adicionando ícone e tooltip para o campo "Pular Tradução:"
info_skip_translation = criar_imagem(caminho_information, 20, 20)
info_label_skip_translation = ttk.Label(frame_config, image=info_skip_translation)
info_label_skip_translation.grid(row=0, column=4, padx=(5, 0))  
criar_tooltip(info_label_skip_translation, i18n("Maque se não quiser traduzir as legendas."))

# Adicionando ícone e tooltip para o campo "Pular Síntese:"
info_skip_synthesize = criar_imagem(caminho_information, 20, 20)
info_label_skip_synthesize = ttk.Label(frame_config, image=info_skip_synthesize)
info_label_skip_synthesize.grid(row=1, column=4, padx=(5, 0))
criar_tooltip(info_label_skip_synthesize, i18n("Maque se não quiser sintetizar o áudio. Por exemplo, se você já fez isso e está testando"))

# Adicionando ícone e tooltip para o campo "Parar Após Tradução:"
info_stop_after_translation = criar_imagem(caminho_information, 20, 20)
info_label_stop_after_translation = ttk.Label(frame_config, image=info_stop_after_translation)
info_label_stop_after_translation.grid(row=2, column=4, padx=(5, 0))
criar_tooltip(info_label_stop_after_translation, f"{i18n('Maque se desejar interromper o programa após traduzir as legendas.')} \n{i18n('Por exemplo, se você quiser revisar manualmente as legendas resultantes antes de sintetizar o áudio.')} \n{i18n('Observe que para retomar o processo, você deve definir novamente como False e definir skip_translation como True')}")

# Adicionando ícone e tooltip para o campo "Síntese de Voz em Duas Etapas:"
info_two_pass_voice_synth = criar_imagem(caminho_information, 20, 20)
info_label_two_pass_voice_synth = ttk.Label(frame_config, image=info_two_pass_voice_synth)
info_label_two_pass_voice_synth.grid(row=3, column=4, padx=(5, 0))
criar_tooltip(info_label_two_pass_voice_synth, f"{i18n('Isso melhorará drasticamente a qualidade do resultado final, MAS veja a nota abaixo.')} \n{i18n('Nota! Definir isso como verdadeiro fará com que, em vez de apenas esticar os clipes de áudio, a API gere novos clipes de áudio com taxas de fala ajustadas.')} \n{i18n('Isso não pode ser feito na primeira passagem porque não sabemos quanto tempo os clipes de áudio terão até que os geremos.')}\n\n {i18n('Funciona apenas no Google e Azure')}")

# Adicionando ícone e tooltip para o campo "Forçar Estiramento com Duas Etapas:"
info_force_stretch_with_twopass = criar_imagem(caminho_information, 20, 20)
info_label_force_stretch_with_twopass = ttk.Label(frame_config, image=info_force_stretch_with_twopass)
info_label_force_stretch_with_twopass.grid(row=4, column=4, padx=(5, 0))
criar_tooltip(info_label_force_stretch_with_twopass, f"{i18n('Obrigatório para')} EDGE {i18n('e')} BARK \n\n{i18n('Na segunda passagem, cada clipe de áudio ficará extremamente próximo da duração desejada, mas um pouco diferente.')}\n{i18n('Defina como True se quiser esticar o clipe da segunda passagem de qualquer maneira para ser exato, até o milissegundo.')}\n{i18n('No entanto, isso degradará a voz e fará com que soe semelhante a se fosse apenas 1-Pass')}")

# Adicionando ícone e tooltip para o campo "Modo de Depuração:"
info_debug_mode = criar_imagem(caminho_information, 20, 20)
info_label_debug_mode = ttk.Label(frame_config, image=info_debug_mode)
info_label_debug_mode.grid(row=5, column=4, padx=(5, 0))
criar_tooltip(info_label_debug_mode, i18n("Principalmente evita que o programa exclua arquivos no diretório de trabalho e também gera arquivos para cada etapa de áudio."))

# Adicionando ícone e tooltip para o campo "Idioma Original:"
info_original_language = criar_imagem(caminho_information, 20, 20)
info_label_original_language = ttk.Label(frame_config, image=info_original_language)
info_label_original_language.grid(row=6, column=4, padx=(5, 0))
criar_tooltip(info_label_original_language, i18n("O código de idioma BCP-47 para o idioma do texto original."))

# Adicionando ícone e tooltip para o campo "Preferência de Formalidade:"
info_formality_preference = criar_imagem(caminho_information, 20, 20)
info_label_formality_preference = ttk.Label(frame_config, image=info_formality_preference)
info_label_formality_preference.grid(row=7, column=4, padx=(5, 0))
criar_tooltip(info_label_formality_preference, i18n("Aplica-se apenas a traduções do DeepL - se deve usar uma linguagem mais ou menos formal."))

# Adicionando ícone e tooltip para o campo "Formato de Saída:"
info_output_format = criar_imagem(caminho_information, 20, 20)
info_label_output_format = ttk.Label(frame_config, image=info_output_format)
info_label_output_format.grid(row=8, column=4, padx=(5, 0))
criar_tooltip(info_label_output_format, i18n("O formato/codec do arquivo de áudio final."))

# Adicionando ícone e tooltip para o campo "Codificação de Áudio da Síntese:"
info_synth_audio_encoding = criar_imagem(caminho_information, 20, 20)
info_label_synth_audio_encoding = ttk.Label(frame_config, image=info_synth_audio_encoding)
info_label_synth_audio_encoding.grid(row=9, column=4, padx=(5, 0))
criar_tooltip(info_label_synth_audio_encoding, f"{i18n('Deve ser um codec da seção (Codificações de áudio compatíveis) aqui:')} https://cloud.google.com/speech-to-text/docs/encoding#audio-encodings.\n{i18n('Isso determina o codec retornado pela API, não aquele produzido pelo programa! Você provavelmente não deveria mudar isso, caso contrário, pode não funcionar')}")

# Adicionando ícone e tooltip para o campo "Pausa da Sentença Azure:"
info_azure_sentence_pause = criar_imagem(caminho_information, 20, 20)
info_label_azure_sentence_pause = ttk.Label(frame_config, image=info_azure_sentence_pause)
info_label_azure_sentence_pause.grid(row=10, column=4, padx=(5, 0))
criar_tooltip(info_label_azure_sentence_pause, f"{i18n('Somente Azure: define a pausa exata em milissegundos que a voz TTS fará após um período entre as frases.')}\n{i18n('Defina-a como (padrão) para mantê-la padrão, o que é bastante lento. Acho que 80 ms é muito bom.')}\n{i18n('Observação: alterar isso do padrão adiciona cerca de 60 caracteres por linha à contagem total de uso de caracteres do Azure')}")

# Adicionando ícone e tooltip para o campo "Taxa de Amostragem da Síntese:"
info_synth_sample_rate = criar_imagem(caminho_information, 20, 20)
info_label_synth_sample_rate = ttk.Label(frame_config, image=info_synth_sample_rate)
info_label_synth_sample_rate.grid(row=11, column=4, padx=(5, 0))
criar_tooltip(info_label_synth_sample_rate, f"{i18n('Insira a taxa de amostragem nativa para o áudio de voz fornecido pelo serviço TTS')}\n{i18n('Isso geralmente é 24KHz (24.000), mas alguns serviços como o Azure oferecem áudio de qualidade superior a 48KHz (48.000)')}\n{i18n('Insira apenas dígitos numéricos, sem vírgulas ou qualquer coisa')}")

# Adicionando ícone e tooltip para o campo "Máximo de Caracteres para Combinar Legendas:"
info_combine_subtitles_max_chars = criar_imagem(caminho_information, 20, 20)
info_label_combine_subtitles_max_chars = ttk.Label(frame_config, image=info_combine_subtitles_max_chars)
info_label_combine_subtitles_max_chars.grid(row=12, column=4, padx=(5, 0))
criar_tooltip(info_label_combine_subtitles_max_chars, f"{i18n('Se a combinação de duas linhas de legenda adjacentes estiver abaixo desse valor, e uma começar ao mesmo tempo que a outra termina, as linhas serão combinadas.')}\n{i18n('Isso deve melhorar a síntese de fala, reduzindo divisões não naturais em frases faladas.')}\n{i18n('Definir como zero ou um número baixo irá efetivamente desativá-lo')}")

# Adicionando ícone e tooltip para o campo "Adicionar Buffer de Linha em Milissegundos:"
info_add_line_buffer_milliseconds = criar_imagem(caminho_information, 20, 20)
info_label_add_line_buffer_milliseconds = ttk.Label(frame_config, image=info_add_line_buffer_milliseconds)
info_label_add_line_buffer_milliseconds.grid(row=13, column=4, padx=(5, 0))
criar_tooltip(info_label_add_line_buffer_milliseconds, f"{i18n('Adiciona um buffer de silêncio entre cada clipe falado, mas mantém a fala 9centralizada) no local certo para que ainda esteja sincronizada')}\n> {i18n('Para deixar claro, a duração total do arquivo de áudio permanecerá a mesma, cada clipe falado será reduzido dentro dele')}\n> {i18n('Útil se o seu arquivo de legendas colocar todos os tempos de início e fim um contra o outro')}\n{i18n('Observe que isso se aplica antes e depois, então o total extra entre os clipes será 2x isso')}\n{i18n('Aviso, definir um valor muito alto pode fazer com que o TTS fale extremamente rápido para caber na duração restante do clipe')}\n> {i18n('Cerca de 25 a 50 milissegundos é um bom ponto de partida')}")

# Adicionando ícone e tooltip para o campo "Pausa da Sentença Azure:"
info_azure_sentence_pause = criar_imagem(caminho_information, 20, 20)
info_label_azure_sentence_pause = ttk.Label(frame_config, image=info_azure_sentence_pause)
info_label_azure_sentence_pause.grid(row=14, column=4, padx=(5, 0))
criar_tooltip(info_label_azure_sentence_pause, f"{i18n('Somente Azure: define a pausa exata em milissegundos que a voz TTS fará após uma vírgula.')}\n{i18n('Defina-a como (padrão) para mantê-la padrão, o que é bastante lento.')}\n{i18n('Parece que esse número não segue exatamente e parece seguir tem um mínimo de cerca de 50 ms')}\n{i18n('Observação: alterar o padrão adiciona cerca de 60 caracteres por linha à contagem total de uso de caracteres do Azure')}")

# Adicionando ícone e tooltip para o campo "Taxa de Amostragem da Síntese:"
info_synth_sample_rate = criar_imagem(caminho_information, 20, 20)
info_label_synth_sample_rate = ttk.Label(frame_config, image=info_synth_sample_rate)
info_label_synth_sample_rate.grid(row=15, column=4, padx=(5, 0))
criar_tooltip(info_label_synth_sample_rate, f"{i18n('Insira a taxa de amostragem nativa para o áudio de voz fornecido pelo serviço TTS')}\n{i18n('Isso geralmente é 24KHz (24.000), mas alguns serviços como o Azure oferecem áudio de qualidade superior a 48KHz (48.000)')}\n{i18n('Insira apenas dígitos numéricos, sem vírgulas ou qualquer coisa')}")


# Botões
save_button = tk.Button(root, text=i18n("Salvar Configurações"), command=save_settings)
save_button.pack(pady=10)

run_button = tk.Button(root, text=i18n("Executar"), command=run_main_code)
run_button.pack(pady=10)

# Rótulo para exibir os créditos
credits_label = tk.Label(root, text=f"Auto-Synced Translated Dubs {version}\n{i18n('script by')} ThioJoe\nUI Rafael Godoy Ebert\nCopyright © 2023")
credits_label.pack(side="bottom")

# Chame a função para ler as configurações dos arquivos INI e definir os valores iniciais nos campos
read_ini_settings()

root.mainloop()
