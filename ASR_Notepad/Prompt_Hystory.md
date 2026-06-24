# PROMPT HISTORY

## Prompt 1: Main controls on the layout
You are working on a project to develop a smart notepad based on Automatic Speech Recognition (ASR). The framework to be used for developing the front-end is Flet 0.28.2. The interface should be simple, minimal, and modern. 
The page theme should be: ```page.theme = Theme(color_scheme_seed=ft.Colors.TEAL_300)```, and the theme_mode should be ```page.theme_mode = ft.ThemeMode.LIGHT```.

The layout should have the following controls (ordered from top to bottom):
- A container with the following icon buttons:
    - a new note icon button to create a new note (clear the note).
    - a copy to clipboard button to copy the note to the clipboard.
    - a download button to download the note as a text file.    
- A container with a text field to show the note.
- A microphone icon button to start the ASR with centered alignment partially placed on the lower border of the textfield.

## Prompt 2: Create app logic
Your goal is to create the app logic for the ASR Notepad. In the @main.py file you should only work in the ```start_asr``` function. The app will work according two different states: recording and not recording. When the app is in the recording state (first press of the microphone button) the app should start recording and when the app is in the not recording state (second press of the microphone button) the app should stop recording and start the ASR. Once the text is recognized it should be added to the note field (```note_container.content```). The app logic should consider a new note event: so when the user presses the microphone button again, a new recording should start and when the microphone is pressed again the app should stop recording and start the ASR. 
The methods are completely defined in the @HugginFace_SpeechToText.ipynb file. Use this file, both for managing audio and ASR operations. You have to create two classes: one for audio operations and another for ASR operations. 
The audio class should set default values (FORMAT, CHANNELS, RATE, CHUNK) within the __init__ method and contain the three basic methods: ```start_recording```, ```stop_recording```, ```_recording_thread_logic```.
The ASR class, ```named asr_client```, should initialize a HuggingFace InferenceClient exposing its main paramenters (model, provider, token) but leaving default values as in the @HugginFace_SpeechToText.ipynb file. Moreover, it should contain the method for ASR. Do not modify the @HugginFace_SpeechToText.ipynb file and the already written code in this project.