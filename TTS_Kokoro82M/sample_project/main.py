import os
from typing import Any

import flet as ft
from asr_utils import AudioRecorder, ASRClient
from dotenv import load_dotenv, set_key


def main(page: ft.Page) -> None:
    """
    Main entry point for the ASR Notepad application.
    Sets up the UI, initializes ASR services, and handles user interactions.
    """
    # --- Environment & Configuration ---
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    env_path = os.path.join(project_root, ".env")
    load_dotenv(env_path)

    # --- Directories Setup ---
    uploads_dir = os.path.join(project_root, "uploads")
    downloads_dir = os.path.join(project_root, "downloads")
    os.makedirs(uploads_dir, exist_ok=True)
    os.makedirs(downloads_dir, exist_ok=True)

    # --- ASR Initialization ---
    audio_recorder = AudioRecorder()
    initial_token = os.getenv("HUGGINGFACE_TOKEN_READ", "")
    asr_client = ASRClient(
        token=initial_token if initial_token else None,
        mode="hub"  # Default mode
    )
    is_recording = False

    # --- UI State Helpers ---
    def update_ui() -> None:
        """Helper to refresh the page."""
        page.update()

    def show_snack(message: str) -> None:
        """Displays a snackbar with the given message."""
        page.open(ft.SnackBar(ft.Text(message)))
        update_ui()

    # --- Event Handlers ---
    def create_new_note(e: ft.ControlEvent) -> None:
        """Clears the current note content."""
        note_field.value = ""
        update_ui()

    def open_settings(e: ft.ControlEvent) -> None:
        """Populates and opens the settings dialog."""
        try:
            token_field.value = os.getenv("HUGGINGFACE_TOKEN_READ", "")
            # Sync switch with current client mode
            mode_switch_dialog.value = (asr_client.mode == "local")
            token_container.visible = not mode_switch_dialog.value
            page.open(settings_dialog)
            update_ui()
        except Exception as ex:
            show_snack(f"Error opening settings: {ex}")

    def close_settings(e: ft.ControlEvent) -> None:
        """Closes the settings dialog."""
        page.close(settings_dialog)
        update_ui()

    def save_settings(e: ft.ControlEvent) -> None:
        """Saves ASR settings and persists API token."""
        new_mode = "local" if mode_switch_dialog.value else "hub"
        asr_client.set_mode(new_mode)

        new_token = token_field.value.strip()
        if new_token:
            set_key(env_path, "HUGGINGFACE_TOKEN_READ", new_token)
            os.environ["HUGGINGFACE_TOKEN_READ"] = new_token
            asr_client.set_token(new_token)

        page.close(settings_dialog)
        show_snack(f"Settings saved! Mode: {new_mode.upper()}")

    def on_mode_change_dialog(e: ft.ControlEvent) -> None:
        """Toggles API key field visibility based on ASR mode."""
        token_container.visible = not mode_switch_dialog.value
        update_ui()

    def process_transcription(text: str) -> None:
        """Appends transcribed text to the note field."""
        if not text:
            return
            
        current_val = note_field.value
        if current_val:
            note_field.value = f"{current_val} {text}"
        else:
            note_field.value = text
        update_ui()

    def refresh_uploads() -> None:
        """Updates the dropdown with files from the uploads directory."""
        files = []
        try:
            files = [f for f in os.listdir(uploads_dir) if os.path.isfile(os.path.join(uploads_dir, f)) and f.lower().endswith(('.mp3', '.wav', '.flac'))]
        except Exception:
            pass
        upload_dropdown.options = [ft.dropdown.Option(f) for f in files]
        if not files:
            upload_dropdown.value = None
            upload_dropdown.hint_text = "No audio files found in 'uploads'"
        else:
            upload_dropdown.hint_text = "Select a file"

    def perform_upload(e: ft.ControlEvent) -> None:
        filename = upload_dropdown.value
        page.close(upload_dialog)
        update_ui()
        if filename:
            file_path = os.path.join(uploads_dir, filename)
            show_snack(f"Transcribing {filename}...")
            transcription = asr_client.transcribe_audio(file_path)
            process_transcription(transcription)

    def open_upload_dialog(e: ft.ControlEvent) -> None:
        refresh_uploads()
        page.open(upload_dialog)
        update_ui()

    def copy_to_clipboard(e: ft.ControlEvent) -> None:
        """Copies the note content to the system clipboard."""
        if note_field.value:
            page.set_clipboard(note_field.value)
            show_snack("Copied to clipboard!")
        else:
            show_snack("Note is empty!")

    def perform_download(e: ft.ControlEvent) -> None:
        """Saves the note content directly to the downloads directory."""
        filename = download_filename.value.strip() or "note.txt"
        save_path = os.path.join(downloads_dir, filename)
        try:
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(note_field.value)
            show_snack(f"Saved successfully to: downloads/{filename}")
            page.close(download_dialog)
            update_ui()
        except Exception as ex:
            show_snack(f"Error saving file: {ex}")

    def open_download_dialog(e: ft.ControlEvent) -> None:
        page.open(download_dialog)
        update_ui()

    def toggle_mic_recording(e: ft.ControlEvent) -> None:
        """Starts or stops live audio recording and transcribes the result."""
        nonlocal is_recording

        if not is_recording:
            is_recording = True
            e.control.bgcolor = ft.Colors.RED
            e.control.icon = ft.Icons.STOP
            e.control.update()
            audio_recorder.start_recording()
        else:
            is_recording = False
            e.control.bgcolor = page.theme.color_scheme_seed
            e.control.icon = ft.Icons.MIC
            e.control.update()

            audio_data = audio_recorder.stop_recording()
            show_snack("Transcribing...")
            
            transcription = asr_client.transcribe_audio(audio_data)
            process_transcription(transcription)

    # --- UI Configuration ---
    page.theme = ft.Theme(color_scheme_seed=ft.Colors.TEAL_600)
    page.theme_mode = ft.ThemeMode.LIGHT
    page.title = "ASR Notepad"
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.window.maximized = True
    page.padding = ft.padding.only(top=80, bottom=20, left=250, right=250)
    page.scroll = ft.ScrollMode.AUTO

    # --- Dialogs & Pickers ---
    download_filename = ft.TextField(label="File name (e.g. note.txt)", value="note.txt", expand=True)
    download_dialog = ft.AlertDialog(
        title=ft.Text("Download Note"),
        content=ft.Column([
            ft.Text("Choose a name to save the note in the 'downloads' folder:"),
            download_filename
        ], tight=True),
        actions=[
            ft.TextButton("Cancel", on_click=lambda _: page.close(download_dialog)),
            ft.ElevatedButton("Save", on_click=perform_download),
        ],
    )

    upload_dropdown = ft.Dropdown(label="Select audio file", expand=True)
    upload_dialog = ft.AlertDialog(
        title=ft.Text("Transcribe from Uploads Folder"),
        content=ft.Column([
            ft.Text("Select an audio file from the 'uploads' folder:"),
            upload_dropdown
        ], tight=True),
        actions=[
            ft.TextButton("Cancel", on_click=lambda _: page.close(upload_dialog)),
            ft.ElevatedButton("Transcribe", on_click=perform_upload),
        ],
    )

    token_field = ft.TextField(
        label="Hugging Face API Key",
        password=True,
        can_reveal_password=True,
        expand=True,
    )

    mode_switch_dialog = ft.Switch(
        label="Local Mode",
        on_change=on_mode_change_dialog,
    )

    token_container = ft.Row([token_field], visible=True)

    settings_dialog = ft.AlertDialog(
        title=ft.Text("Settings"),
        content=ft.Column(
            [mode_switch_dialog, token_container],
            tight=True,
            spacing=20,
        ),
        actions=[
            ft.TextButton("Cancel", on_click=close_settings),
            ft.ElevatedButton("Save", on_click=save_settings),
        ],
    )

    # --- Floating Components ---
    settings_button = ft.Container(
        content=ft.IconButton(
            icon=ft.Icons.SETTINGS,
            icon_size=30,
            tooltip="Open Settings",
            on_click=open_settings,
            bgcolor=ft.Colors.with_opacity(0.1, ft.Colors.BLACK),
        ),
        bottom=20,
        right=20,
    )

    page.overlay.extend([
        download_dialog,
        upload_dialog,
        settings_dialog,
        settings_button,
    ])

    # --- UI Layout ---
    # 1. Toolbar logic
    toolbar = ft.Container(
        padding=10,
        border_radius=ft.border_radius.only(top_left=10, top_right=10),
        bgcolor=page.theme.color_scheme_seed,
        theme_mode=ft.ThemeMode.DARK,
        content=ft.Row(
            controls=[
                ft.IconButton(
                    icon_size=30,
                    icon=ft.Icons.NOTE_ADD,
                    tooltip="New Note",
                    on_click=create_new_note,
                ),
                ft.IconButton(
                    icon_size=30,
                    icon=ft.Icons.COPY,
                    tooltip="Copy to Clipboard",
                    on_click=copy_to_clipboard,
                ),
                ft.IconButton(
                    icon_size=30,
                    icon=ft.Icons.DOWNLOAD,
                    tooltip="Download Note",
                    on_click=open_download_dialog,
                ),
            ],
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=10,
        ),
    )

    # 2. Main note editor
    note_field = ft.TextField(
        multiline=True,
        min_lines=15,
        max_lines=15,
        expand=True,
        border=ft.InputBorder.NONE,
    )

    note_container = ft.Container(
        padding=ft.padding.only(top=25, bottom=25, left=55, right=55),
        border_radius=ft.border_radius.only(bottom_left=10, bottom_right=10),
        border=ft.border.all(2, page.theme.color_scheme_seed),
        content=note_field,
    )

    # 3. Action Buttons (Upload & Mic)
    action_buttons = ft.Row(
        [
            ft.IconButton(
                icon_size=50,
                icon=ft.Icons.UPLOAD_FILE,
                icon_color=ft.Colors.WHITE,
                bgcolor=page.theme.color_scheme_seed,
                tooltip="Upload audio file",
                on_click=open_upload_dialog,
            ),
            ft.IconButton(
                icon_size=50,
                icon=ft.Icons.MIC,
                icon_color=ft.Colors.WHITE,
                bgcolor=page.theme.color_scheme_seed,
                tooltip="Record your voice",
                on_click=toggle_mic_recording,
            ),
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        spacing=20,
    )

    # Combine all elements into the page
    page.add(
        ft.Column(
            controls=[
                toolbar,
                note_container,
                action_buttons,
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=0,
        )
    )


if __name__ == "__main__":
    is_docker = os.getenv("DOCKER_RUNNING") == "true"
    
    ft.app(
        target=main,
        assets_dir="assets",
        #upload_dir="uploads",
        view=ft.AppView.WEB_BROWSER if is_docker else None,
        host="0.0.0.0" if is_docker else "127.0.0.1",
        port=8080 if is_docker else 0
    )
