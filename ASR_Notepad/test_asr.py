import flet as ft
import sys
import os

# Ensure src directory is in the path
sys.path.append(os.path.join(os.getcwd(), "src"))
from asr_utils import ASRClient

def main(page: ft.Page):
    page.title = "ASR Test Tool"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    
    asr_client = ASRClient()
    
    status_text = ft.Text("Select an audio file (.mp3 or .wav) to test ASR", size=16)
    result_text = ft.TextField(
        label="ASR Result",
        multiline=True,
        min_lines=10,
        max_lines=15,
        read_only=True,
        expand=True
    )
    
    progress_bar = ft.ProgressBar(width=400, color="blue", visible=False)

    def on_file_result(e: ft.FilePickerResultEvent):
        if e.files:
            file_path = e.files[0].path
            status_text.value = f"Processing: {os.path.basename(file_path)}..."
            progress_bar.visible = True
            result_text.value = ""
            page.update()
            
            try:
                # Read file as bytes
                with open(file_path, "rb") as f:
                    audio_data = f.read()
                
                # Perform ASR
                # Using the exact same class/method as main app
                transcription = asr_client.asr(audio_data)
                
                result_text.value = transcription
                status_text.value = f"Finished: {os.path.basename(file_path)}"
            except Exception as ex:
                status_text.value = f"Error: {str(ex)}"
                result_text.value = f"An exception occurred: {str(ex)}"
            
            progress_bar.visible = False
            page.update()

    file_picker = ft.FilePicker(on_result=on_file_result)
    page.overlay.append(file_picker)

    page.add(
        ft.Column([
            ft.Icon(ft.Icons.AUDIO_FILE, size=50, color=ft.Colors.TEAL),
            status_text,
            ft.ElevatedButton(
                "Select Audio File",
                icon=ft.Icons.UPLOAD_FILE,
                on_click=lambda _: file_picker.pick_files(
                    allowed_extensions=["mp3", "wav"]
                )
            ),
            progress_bar,
            ft.Container(content=result_text, width=600, padding=20)
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    )

if __name__ == "__main__":
    ft.app(target=main)
