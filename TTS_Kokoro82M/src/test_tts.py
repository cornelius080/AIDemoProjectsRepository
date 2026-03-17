from tts_client import TTSClient
from pydub import AudioSegment
import io
import simpleaudio as sa

tts = TTSClient(provider="replicate", model="hexgrad/Kokoro-82M")  


text = "Buongiorno! Questo è un test di sintesi vocale."


wav_bytes = tts.synthesize(text=text, voice="if_sara")
print(f"Generated {len(wav_bytes)} bytes of audio.")
print("Playing audio...")
audio = AudioSegment.from_wav(io.BytesIO(wav_bytes))  
play_obj = sa.play_buffer(audio.raw_data, num_channels=audio.channels, bytes_per_sample=audio.sample_width, sample_rate=audio.frame_rate)
play_obj.wait_done()  


tts.synthesize_to_file(output_path="test_tts.wav", text=text, voice="if_sara")
print("Saved audio to test_tts.wav")

