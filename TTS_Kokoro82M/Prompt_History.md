# PROMPT HISTORY

## Prompt 1: Main controls on the layout
You are working on a project to develop a software application for Text-To-Speech. The framework to be used for developing the front-end is Flet 0.28.2. The interface should be simple, minimal, and modern. 
The page theme should be: ```page.theme = Theme(color_scheme_seed=ft.Colors.DEEP_ORANGE)```.
User controls should be arranged on the page from  top to bottom. The page should have centered alignment both horizontally and vertically.
The UI should include the following controls:
- A row containing two chips aligned at the start (START): the first chip should have the ```leading_icon=TextFields```, and the second one should have the ```leading_icon=UploadFile```.
- A row containing a FilledButton with the text “Cancel Text” to clear the text in the TextField below.
- A TextField to hold the text input.
- A row with END alignment, containing a DropDown control for language selection and a DropDown control for voice selection.
- An elevated button to perform the text-to-speech conversion: the button should be disabled by default and enabled when text is entered in the TextField, and then disabled again when the TextField is emptied.
Generate code into the ```main.py``` file.


## Prompt 2: Chips behaviour
Modify the two chips so that when one is selected, the other is deselected, and vice versa. Upon starting the app, the "Insert Text" chip should be selected by default.

When the "Insert Text" chip is selected, the text field for text input should appear. If the user enters text, the "Cancel text" and "Convert text to speech" buttons should be enabled. When the "Convert text to speech" button is clicked, the text entered in the text field should be printed to the console. When the "Cancel text" button is clicked, the textfield should be empty and both the "Cancel text" and "Convert to speech" buttons should be disabled.

When the "Upload Text File" chip is selected, the "Cancel text" button and the text field should disappear. In place of the text field, the "UPLOAD FILE" icon should appear in the center (```horizontal_alignment="center", vertical_alignment="center"```). Additionally, a file dialog should open for selecting a file with the extension exclusively ".txt". The file picker should behave as in the following example:

```
def pick_files_result(e: ft.FilePickerResultEvent):
        if e.files:
            selected_file = "\\\\".join(map(lambda f: f.path if f.path is not None else f.name, e.files)) #DESKTOP AND WEB
            text.value = selected_file
            text.update()


    pick_files_dialog = ft.FilePicker(on_result=pick_files_result)
    page.overlay.append(pick_files_dialog)

    text = ft.Text("")   

    page.add(
        ft.SafeArea(
            ft.Column(
                [
                    ft.ElevatedButton(
                        "Select a file", 
                        on_click=lambda _: pick_files_dialog.pick_files(dialog_title="Select a file")
                    ),
                    text,
                ],
            ),
            expand=True,
        )
    )
```

Once the file is opened, the "Convert to text" button should be enabled, and if clicked, it should print the full content of the text file into the console.


## Prompt 3: Language Detector
Consider the file ```VOICES.md```. This file contains languages and the corresponding voices that will be used by the text-to-speech engine. Create a separate file where you define a class ```LanguageDetector``` with appropriate members and methods to be used in the main program for automatic language detection. In this new file, you should open the file containing languages and their corresponding voices, and map them into a data structure so that each voice corresponds to its language.

Additionally, the ```LanguageDetector``` class should contain a method to detect the language, as shown in the following snippet:
```
from langdetect import detect
lang = detect(text)
```
Update the main.py file so that the two dropdowns, "Language" and "Voice", contain the corresponding languages and voices. Specifically, the two dropdowns must always be disabled. Only when the user enters text into the text field or uploads a text file the language should be detected (using the method from the ```LanguageDetector``` class), the corresponding voices be loaded into the voice dropdown, and the dropdowns be enabled. If the user clears the text in the text field, both dropdowns should be disabled.

Example: When the app starts, both dropdowns are disabled. The user enters text or uploads a text file in Italian. The language dropdown will contain all languages but will have "Italian" selected. The voice dropdown will contain only the options corresponding to the Italian language, namely "if_sara" and "im_nicola" (see the ```VOICES.md``` file), and one of them will be selected.

Finally, add the trailing_icon "LANGUAGE" to the "language" dropdown and the trailing_icon "VOICE_CHAT" to the "voices" dropdown. Do not modify the rest of the code.


## Prompt 4: Text-To-Speech Client
Consider this code snippet:
```
import os
from huggingface_hub import InferenceClient

client = InferenceClient(
    provider="replicate",
    api_key=os.environ["HF_TOKEN_READ"],
)

user_text = input("Scrivi il testo da convertire in audio: \n").strip()

audio = client.text_to_speech(
    text=user_text,
    model="hexgrad/Kokoro-82M",
    extra_body={
        "voice": "if_sara",
    },
)
```

write a simple, effective class in order to perform text to speech actions as in the code. Make it adaptable to different models and different voices.


## Prompt 5: Implement the convert_on_click event
Currently the control event, is:

```
def on_convert_click(e: ft.ControlEvent):
    if mode["value"] == "insert":
    print(text_input.value.strip())
    elif selected_file_content["value"] is not None:
    print(selected_file_content["value"])

    e.control.disabled = True
    e.control.update()
```

implement the ```tts.synthesize(...)``` call in this method verifying that the ```text_input.value``` is not empty and that the ```selected_file_content["value"]``` is not None. The voice argument of the method will be the value of the ```voice_dropdown```.


## Prompt 6: Comment and document the code
Add docstrings to the ```main.py``` file and, if necessary, some comments to explain the code. Do not change the code order. Do not change the code logic. Do not change the code functionality. 
After that, modify the ```README.md``` file to document the project to a new user, underlying the use of AI (huggingface, kokoro82M) to perform text to speech actions and the ability to detect language from text.