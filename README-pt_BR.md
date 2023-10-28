[English](https://github.com/RafaelGodoyEbert/Auto-Synced-Translated-Dubs-with-UI/blob/main/README.md) | [Português](https://github.com/RafaelGodoyEbert/Auto-Synced-Translated-Dubs-with-UI/blob/main/README-pt_BR.md)
# Dublagens Automáticas Sincronizadas e Traduzidas
Traduz automaticamente o texto de um vídeo com base em um arquivo de legenda e utiliza a voz de IA para dublar o vídeo, sincronizando-o com os tempos das legendas. Agora com um UI para facilitar a configuração e um tutorial mais detalhado.

![UI](https://cdn.discordapp.com/attachments/1124221552779612282/1167690635566907412/image.png)


## Google Colab
### Colab Auto-Synced-Translated-Dubs [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/1MNHeuTBe48kKV4Sfk7yM3CDR8LnEy_He?usp=sharing)
- Sim, eu tentei criar uma versão pro Google Colab, mas só depois percebi que o Ruberband não tem pro Linux.
- Se você tiver as APIs, provavelmente o programa vai funcionar muito bem, já que ele gera o TTS acelerado diretamente do azure. (Não tenho certeza pois não paguei as APIs)
- Então no colab pode fazer todo o resto, menos a função do rubberband, que é a aceleração e desaceleração do áudio.

### Outros Colabs recomendados
**WHISPER - Gerar legenda automática para facilitar na edição** [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/1XWig4fk9BN0gwcj9kp3n6yXevAcDLM8j?usp=sharing)
- Gerar legenda automática 
 - Ele gera a partir de um áudio, então converta o seu vídeo para mp3 e faça upload (fazer upload de video no google colab é muito ruim)
 - Depois de gerado e baixado, utilize o [Aegisub](https://github.com/Aegisub/Aegisub) (Só abrir o site deles e baixar) para organizar as legendas, lembre-se quanto melhor e mais sincronizado as legendas estiverem, melhor o seu resultado final

**EDGE-TTS - TTS sem API** [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/1Em_fn0QmN5Bln9uXr4mlnQZLOiG4tO2L?usp=sharing)
- Recomendo fazer o TTS pelo **EDGE-TTS** pois você não precisa de API 
   - Nesse colab ele você envia o arquivo .SRT, ele fazer o TTS
   - Ele baixa o ZIP
   - Você vai ter que extrair na pasta ``workingFolder```
   - Vai ter que deixar a opção ``Pular tradução``, ``Pular Síntese`` e ``Forçar esticamento na segunda etapa`` ativado ✅

### Como Funciona
Se você já possui um arquivo de legendas SRT feito por humanos para um vídeo, este programa fará o seguinte:
1. Utilizará o Google Cloud/DeepL para traduzir automaticamente o texto e criar novos arquivos SRT traduzidos.
   - Opcional: Utilizar [EDGE-TTS](https://github.com/rany2/edge-tts), sem necessidade de API
2. Criará clipes de áudio de texto para fala do texto traduzido (usando vozes neurais mais realistas).
3. Utilizará os tempos das legendas para calcular a duração correta de cada clipe de áudio falado.
4. Esticará ou encurtará o clipe de áudio traduzido para que ele tenha exatamente o mesmo comprimento que o discurso original e o inserirá no mesmo ponto no áudio. Portanto, o discurso traduzido permanecerá perfeitamente sincronizado com o vídeo original.
    - Opcional (Ativado por padrão): Em vez de esticar os clipes de áudio, você pode fazer uma segunda passagem para sintetizar cada clipe através da API usando a velocidade de fala adequada calculada durante a primeira passagem. Isso melhora drasticamente a qualidade do áudio.

### Principais Recursos Adicionais
- Cria versões traduzidas do arquivo de legendas SRT
- Processamento em lote de vários idiomas em sequência
- Arquivos de configuração para salvar configurações de tradução, síntese e idioma para reutilização
- Script incluído para adicionar todas as faixas de áudio de idioma a um arquivo de vídeo
   - Com a capacidade de mesclar uma faixa de efeitos sonoros em cada faixa de idioma
- Script incluído para traduzir o Título e a Descrição de um vídeo do YouTube para vários idiomas

----

# Instruções

### Requisitos Externos:
- O ffmpeg deve estar instalado (https://ffmpeg.org/download.html)
   - Instale pro PATH para garantir. [GUIA ALEATÓRIO DA INTERNET](https://academy.streamholics.live/guias/guia-ffmpeg/)
- Você precisará dos binários de um programa chamado 'rubberband' (https://breakfastquay.com/rubberband/). Não precisa ser instalado, basta colocar os arquivos .exe e o arquivo .dll no mesmo diretório/pasta que se encontra a pasta dos scripts.

## Configuração e Configuração
1. Faça o download ou clone o repositório e instale os requisitos usando `pip install -r requirements.txt`
   - Foi escrito usando o Python 3.9, mas provavelmente funcionará com versões anteriores também.
2. Instale os programas mencionados nos 'Requisitos Externos' acima.
3. Execute run_interface.bat ou simplesmente `python interface.py`
   1. Configure seu acesso à API do Google Cloud (consulte o Wiki), Microsoft Azure e/ou token da API DeepL e defina as variáveis em `cloud_service_settings.ini`. 
      - Recomendo o Azure para a síntese de voz TTS porque, em minha opinião, eles têm vozes mais novas e melhores e de alta qualidade (o Azure suporta uma taxa de amostragem de até 48KHz, em comparação com 24KHz com o Google). 
      - O Google Cloud é mais rápido, mais barato e suporta mais idiomas para tradução de texto, mas você também pode usar o DeepL.
      - Eu recomendo usar o [EDGE-TTS](https://colab.research.google.com/drive/1Em_fn0QmN5Bln9uXr4mlnQZLOiG4tO2L) e depois usar um [RVC](https://br.aihub.wtf/) para clone de voz, assim não tem necessidade de API
   2. Configure suas configurações no arquivo `config.ini`. As configurações padrão devem funcionar na maioria dos casos, mas leia-as especialmente se estiver usando o Azure para TTS, pois existem mais opções aplicáveis que você pode querer personalizar.
   - Esta configuração inclui opções como a capacidade de pular a tradução de texto, definir formatos e taxa de amostragem e usar a síntese de voz em duas etapas.
   3. Finalmente, abra `batch.ini` para definir as configurações de idioma e voz que serão usadas em cada execução. 
      - Na seção superior `[SETTINGS]`, você deve inserir o caminho para o arquivo de vídeo original (usado para obter o comprimento correto do áudio) e o caminho do arquivo de legenda original
      - Além disso, você pode usar a variável `enabled_languages` para listar todos os idiomas que serão traduzidos e sintetizados de uma vez. Os números corresponderão às seções `[LANGUAGE-#]` no mesmo arquivo de configuração. O programa processará apenas os idiomas listados nesta variável.
      - Isso permite que você adicione quantos idiomas predefinidos desejar (como a voz preferida por idioma) e escolha quais idiomas deseja usar (ou não usar) em qualquer execução.
      - Certifique-se de verificar os idiomas e vozes suportados para cada serviço em sua documentação respectiva.

## Instruções de Uso
- **Como Executar:** Após configurar os arquivos de configuração, basta executar o script main.py usando `python main.py` e deixe-o rodar até a conclusão.
   - Os arquivos de legendas traduzidos resultantes e as faixas de áudio dubladas serão colocados em uma pasta chamada 'output'.
- **Opcional:** Você pode usar o script separado `TrackAdder.py` para adicionar automaticamente as faixas de idioma resultantes a um arquivo de vídeo mp4. É necessário ter o ffmpeg instalado.
   - Abra o arquivo de script com um editor de texto e altere os valores na seção "User Settings" no topo.
   - Isso rotulará as faixas para que o arquivo de vídeo esteja pronto para ser enviado ao YouTube. No entanto, o recurso de várias faixas de áudio está disponível apenas para um número limitado de canais. Você provavelmente precisará entrar em contato com o suporte ao criador do YouTube para solicitar acesso, mas não há garantia de que eles concederão.
   - Não tenho certeza, mas a ferramenta de vários idiomas tem que ter assinatura premium do youtube e ter mais de 100k de inscritos no canal, então assim você pode fazer o pedido.
- **Opcional:** Você pode usar o script separado `TitleTranslator.py` ao enviar para o YouTube, o que permite inserir o Título e a Descrição de um vídeo, e o texto será traduzido para todos os idiomas habilitados em `batch.ini`. Eles serão colocados juntos em um único arquivo de texto na pasta "output".

----


## Notas Adicionais:
- Isso funciona melhor com legendas que não removem os espaços entre frases e linhas.
- Por enquanto, o processo assume apenas um locutor. No entanto, se você puder criar arquivos SRT separados para cada locutor, você pode gerar cada faixa TTS separadamente usando vozes diferentes e depois combiná-las posteriormente.
- Ele suporta tanto o Google Translate API quanto o DeepL para tradução de texto e tanto o Google quanto o Azure para Text-To-Speech com vozes neurais.
- Este script foi escrito com meu próprio fluxo de trabalho pessoal em mente. Isso significa:
    - Eu uso [**OpenAI Whisper**](https://github.com/openai/whisper) para transcrever os vídeos localmente e, em seguida, uso o [**Descript**](https://www.descript.com/) para sincronizar essa transcrição e aprimorá-la com correções.
    - Em seguida, exporto o arquivo SRT com o Descript, o que é ideal porque ele não apenas coloca os horários de início e término de cada linha de legenda lado a lado. Isso significa que a dublagem resultante preservará as pausas entre as frases do discurso original. Se você usar legendas de outro programa, pode encontrar pausas entre as linhas muito curtas.
    - As configurações de exportação de SRT no Descript que parecem funcionar razoavelmente bem para dublagem são *máximo de 150 caracteres por linha* e *máximo de 1 linha por cartão*.
- O recurso de "Duas Passagens" na síntese (ativado no arquivo de configuração) melhorará drasticamente a qualidade do resultado final, mas exigirá a síntese de cada clipe duas vezes, dobrando assim os custos da API.

## Para obter mais informações sobre os idiomas suportados por serviço:
- [Idiomas Suportados pela Tradução do Google Cloud](https://cloud.google.com/translate/docs/languages)
- [Idiomas Suportados pelo Text-to-Speech do Google Cloud](https://cloud.google.com/text-to-speech/docs/voices)
- [Idiomas Suportados pelo Text-to-Speech do Azure](https://docs.microsoft.com/pt-br/azure/cognitive-services/speech-service/language-support#text-to-speech)
- [Idiomas Suportados pelo DeepL](https://www.deepl.com/docs-api/translating-text/request)

