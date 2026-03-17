from language_detector import LanguageDetector


def main():
    # Initialize detector
    detector = LanguageDetector("VOICES.md")
    
    # Test 1: Print all languages
    print("Queste le lingue rilevate:\n")
    languages = detector.languages
    for language in languages:
        print(language)
    
    print("\n" + "="*50 + "\n")
    
    # Test 2: Print all languages with their voices
    print("Queste le lingue rilevate:\n")
    for language in languages:
        voices = detector.get_voices(language)
        voices_str = ", ".join(voices) if voices else "Nessuna voce disponibile"
        print(f"{language}\nVoices: {voices_str}\n")
    
    print("="*50 + "\n")
    
    # Test 3: Interactive language detection
    print("Inserire una frase per la verifica della language detection (Press 'q' to exit the input):")
    
    while True:
        user_input = input("*****\n")
        
        if user_input.lower().strip() == 'q':
            print("Uscita dal test.")
            break
        
        if not user_input.strip():
            print("Input vuoto. Inserire una frase valida o 'q' per uscire.")
            continue
        
        detected_language = detector.detect_language(user_input)
        
        if detected_language:
            print(f"La lingua rilevata è:\n{detected_language}\n")
        else:
            print("Lingua non rilevata o non supportata.\n")
        
        print("Inserire una frase per la verifica della language detection (Press 'q' to exit the input):")


if __name__ == "__main__":
    main()

