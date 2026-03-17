import flet as ft
import flet_audio as fta
import base64, threading
from pathlib import Path
from datetime import datetime
from language_detector import LanguageDetector
from tts_client import TTSClient


def main(page: ft.Page):
    """
    The main entry point for the Flet application.

    Args:
        page (ft.Page): The page object provided by Flet.
    """
    def set_dropdowns_visibility(visible: bool):
        """Set the dropdowns visibility"""
        language_dropdown.visible = visible
        voice_dropdown.visible = visible
        language_dropdown.update()
        voice_dropdown.update()

    def update_language_and_voice(text: str | None):
        """
        Detects the language of the input text and updates the language/voice dropdowns.
        
        If text is empty, it disables the dropdowns.
        """
        content = (text or "").strip()
        if not content:
            # Empty and disable the dropdowns
            language_dropdown.disabled = True
            language_dropdown.value = None
            voice_dropdown.disabled = True
            voice_dropdown.value = None
            voice_dropdown.options = []
            language_dropdown.update()
            voice_dropdown.update()
            # Hide the dropdowns
            set_dropdowns_visibility(False)
            return

        detected_language = language_detector.detect_language(content)

        # Populate and enable the dropdowns
        language_dropdown.options = [
            ft.dropdown.Option(key=lang, text=lang) for lang in language_detector.languages
        ]
        language_dropdown.value = detected_language
        language_dropdown.disabled = False

        voices = language_detector.get_voices(detected_language)
        voice_dropdown.options = [
            ft.dropdown.Option(key=voice, text=voice) for voice in voices
        ]
        voice_dropdown.value = voices[0] if voices else None
        voice_dropdown.disabled = len(voices) == 0

        language_dropdown.update()
        voice_dropdown.update()

        # Show the dropdowns
        set_dropdowns_visibility(True)

    def on_language_change(e: ft.ControlEvent):
        """
        Handles language selection changes.
        
        Updates the voice dropdown options based on the selected language.
        """
        selected_language = e.control.value
        if selected_language:
            voices = language_detector.get_voices(selected_language)
            voice_dropdown.options = [
                ft.dropdown.Option(key=voice, text=voice) for voice in voices
            ]
            voice_dropdown.value = voices[0] if voices else None
            voice_dropdown.disabled = len(voices) == 0
            voice_dropdown.update()

    def reset_dropdowns_to_neutral():
        """Empty the options and values, then hide the dropdowns."""
        language_dropdown.options = []
        voice_dropdown.options = []
        language_dropdown.value = None
        voice_dropdown.value = None
        language_dropdown.disabled = True
        voice_dropdown.disabled = True
        language_dropdown.update()
        voice_dropdown.update()
        set_dropdowns_visibility(False)

    def update_controls():
        """
        Updates the visibility and state of UI controls based on the current mode and input state.
        """
        is_insert_mode = mode["value"] == "insert"
        text_input.visible = is_insert_mode
        cancel_row.visible = is_insert_mode
        upload_placeholder.visible = not is_insert_mode

        if is_insert_mode:
            has_text = len((text_input.value or "").strip()) > 0
            tts_button.disabled = not has_text
            cancel_button.disabled = not has_text
        else:
            tts_button.disabled = selected_file_path["value"] is None

        play_audio_button.disabled = True
        play_audio_button.update()
        text_input.update()
        cancel_button.update()
        tts_button.update()
        cancel_row.update()
        upload_placeholder.update()
    
    def on_text_submit(e: ft.ControlEvent):
        """
        Handles the event when user presses Enter (or Shift+Enter if configured) in the text input.
        """
        # If there is text -> populate and show the dropdown; otherwise hide them
        txt = e.control.value or ""
        if txt.strip():
            update_language_and_voice(txt)
        else:
            reset_dropdowns_to_neutral()
        update_controls()

    def on_cancel_click(_):
        """
        Clears the text input and resets the UI state.
        """
        text_input.value = ""
        text_input.update()
        reset_dropdowns_to_neutral()
        update_controls()

    def pick_files_result(e: ft.FilePickerResultEvent):
        """
        Handles the result of the file picker dialog.
        
        Reads the selected file content and updates the state.
        """
        selected_file_path["value"] = None
        selected_file_content["value"] = None
        if e.files:
            file_entry = e.files[0]
            file_path = file_entry.path if file_entry.path else file_entry.name
            selected_file_path["value"] = file_path
            try:
                with open(file_path, "r", encoding="utf-8") as file:
                    content = file.read()
                selected_file_content["value"] = content
                if content.strip():
                    update_language_and_voice(content)
                else:
                    reset_dropdowns_to_neutral()
            except Exception as err:
                print(f"Could not read file {file_path}: {err}")
                selected_file_path["value"] = None
                selected_file_content["value"] = None
                reset_dropdowns_to_neutral()
        else:
            selected_file_path["value"] = None
            selected_file_content["value"] = None
            reset_dropdowns_to_neutral()
        update_controls()
   
    def open_file_dialog():
        """
        Opens the file picker dialog to select a text file.
        """
        pick_files_dialog.pick_files(
            dialog_title="Select a TXT file",
            allow_multiple=False,
            allowed_extensions=["txt"],
        )

    def switch_mode(new_mode: str):
        """
        Switches between 'insert' (text input) and 'upload' (file upload) modes.
        """
        if mode["value"] == new_mode:
            insert_chip.selected = new_mode == "insert"
            upload_chip.selected = new_mode == "upload"
            page.update()
            return

        mode["value"] = new_mode
        insert_chip.selected = new_mode == "insert"
        upload_chip.selected = new_mode == "upload"

        if new_mode == "insert":
            selected_file_path["value"] = None
            selected_file_content["value"] = None
            # Empty and hide the dropdowns when switching mode
            reset_dropdowns_to_neutral()
            if text_input.value and text_input.value.strip():
                update_language_and_voice(text_input.value)
        else:  # upload mode
            text_input.value = ""
            selected_file_path["value"] = None
            selected_file_content["value"] = None
            # Empty and hide the dropdowns when switching mode
            reset_dropdowns_to_neutral()
            open_file_dialog()

        update_controls()
        page.update()

    def on_convert_click(e: ft.ControlEvent) -> None:
        """Handles the *Convert to Speech* button.

        It checks that a source text exists, a voice is selected,
        then calls `tts_client.synthesize(...)`. While the request is
        in‑flight the button is disabled and a SnackBar informs the user.
        """
        nonlocal audio_bytes

        # ----- 1️⃣ Determine source text -----
        if mode["value"] == "insert":
            source_text = (text_input.value or "").strip()
            if not source_text:
                page.open(ft.SnackBar(ft.Text("Please type some text first")))
                page.update()
                return
        else:   # upload mode
            source_text = selected_file_content["value"]
            if source_text is None or not source_text.strip():
                page.open(ft.SnackBar(ft.Text("No file selected or file empty")))
                page.update()
                return

        # ----- 2️⃣ Verify voice selection -----
        voice = voice_dropdown.value
        if not voice:
            page.open(ft.SnackBar(ft.Text("Select a voice from the dropdown")))
            page.update()
            return

        # ----- 3️⃣ Guard – make sure we have a working client -----
        if tts_client is None:
            page.open(ft.SnackBar(ft.Text("TTS client not available")))
            page.update()
            return

        # ----- 4️⃣ Run the synthesis in a background thread -----
        def _run_synthesis() -> None:
            try:
                nonlocal audio_bytes
                audio_bytes = tts_client.synthesize(text=source_text, voice=voice)
                # -----------------------------------------------------------------
                # At this point `audio_bytes` holds the raw WAV/PCM data.
                # You can:
                #   - write it to a temporary file and play it with ft.Audio,
                #   - store it for download, or just log its size.
                # -----------------------------------------------------------------
                page.open(ft.SnackBar(ft.Text("Audio generated successfully!")))
                e.control.disabled = True
                download_audio_button.disabled = False
                play_audio_button.disabled = False
                page.update()
            except Exception as synth_exc:
                page.open(ft.SnackBar(ft.Text(f"❌ TTS error: {synth_exc}")))
                page.update()            

        threading.Thread(target=_run_synthesis, daemon=True).start()

    def on_play_audio_click(e: ft.ControlEvent) -> None:
        """
        Plays the generated audio using the audio player control.
        """
        nonlocal audio_bytes

        if audio_bytes is not None:
            audio_player_tts.src_base64 = base64.b64encode(audio_bytes).decode("utf-8")
            audio_player_tts.update()
            audio_player_tts.play()
        
    def on_download_audio_click(e: ft.ControlEvent) -> None:
        """
        Downloads the generated audio content to a local file.
        """
        nonlocal audio_bytes

        if audio_bytes is not None:
            output_path = datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + "_audio_generated.wav"
            out_file = Path(output_path)
            try:
                out_file.write_bytes(audio_bytes)
                page.open(ft.SnackBar(ft.Text(f"Audio downloaded successfully to: {out_file.absolute()}")))
            except Exception as e:
                page.open(ft.SnackBar(ft.Text(f"Failed to save file: {e}")))
            
            e.control.disabled = True
            e.control.update()


    mode = {"value": "insert"}
    selected_file_path = {"value": None}
    selected_file_content = {"value": None}
    language_detector = LanguageDetector("VOICES.md")
    audio_player_tts = fta.Audio(autoplay=False, src_base64="https://luan.xyz/files/audio/ambient_c_motion.mp3")
    page.overlay.append(audio_player_tts)

    audio_bytes: bytes | None = None
    tts_client: TTSClient | None = None
    try:
        tts_client = TTSClient()
    except Exception as exc:    
        page.open(ft.SnackBar(ft.Text(f"⚠️  TTS client initialisation failed: {exc}")))
        page.update()
    
    pick_files_dialog = ft.FilePicker(on_result=pick_files_result)
    page.overlay.append(pick_files_dialog)

    page.title = "Text2Speech Kokoro82M"
    page.theme = ft.Theme(color_scheme_seed=ft.Colors.DEEP_ORANGE_50)
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.padding = 24
    

    tts_button = ft.FilledButton("Convert to Speech", disabled=True, on_click=on_convert_click)
    cancel_button = ft.FilledButton("Cancel Text", disabled=True, on_click=on_cancel_click)
    text_input = ft.TextField(
        label="Insert text to convert and press Enter",
        multiline=True,
        min_lines=15,
        max_lines=15,
        expand=True,
        shift_enter=True,
        on_submit=on_text_submit,
    )

    language_dropdown = ft.Dropdown(
        label="Language",
        options=[],
        width=280,
        disabled=True,
        visible=False,  # invisible at start
        leading_icon=ft.Icons.LANGUAGE,
        on_change=on_language_change,
    )
    
    voice_dropdown = ft.Dropdown(
        label="Voice",
        options=[],
        width=280,
        disabled=True,
        visible=False,  # invisible at start
        leading_icon=ft.Icons.VOICE_CHAT,
    )


    chips_row = ft.Row(
        alignment=ft.MainAxisAlignment.START,
        controls=[
            (insert_chip := ft.Chip(
                label=ft.Text("Insert Text"),
                leading=ft.Icon(ft.Icons.TEXT_FIELDS),
                show_checkmark=False,
                selected=True,
                on_select=lambda _: switch_mode("insert"),
            )),
            (upload_chip := ft.Chip(
                label=ft.Text("Upload Text File"),
                leading=ft.Icon(ft.Icons.UPLOAD_FILE),
                show_checkmark=False,
                selected=False,
                on_select=lambda _: switch_mode("upload"),
            )),
        ],
    )

    cancel_row = ft.Row(
        alignment=ft.MainAxisAlignment.START,
        controls=[
            cancel_button,
        ],
    )

    dropdown_row = ft.Row(
        alignment=ft.MainAxisAlignment.END,
        controls=[
            language_dropdown,
            voice_dropdown,
        ],
    )

    upload_placeholder = ft.Container(
        ft.Icon(ft.Icons.UPLOAD_FILE, size=80),
        alignment=ft.alignment.center,
        height=240,
        visible=False,
    )

    page.add(
        ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[
                chips_row,
                cancel_row,
                text_input,
                upload_placeholder,
                dropdown_row,
                tts_button,
                ft.Row(
                    [
                        play_audio_button := ft.IconButton(icon_size=30, icon=ft.Icons.MIC, tooltip="Play Audio", disabled=True, on_click=on_play_audio_click),
                        download_audio_button := ft.IconButton(icon_size=30, icon=ft.Icons.DOWNLOAD, tooltip="Download Audio File", disabled=True, on_click=on_download_audio_click),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
            ],
            spacing=16,
        )
    )

    update_controls()

ft.app(target=main, assets_dir="assets")
