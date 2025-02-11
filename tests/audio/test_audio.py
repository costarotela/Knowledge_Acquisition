import pyaudio
import wave
import speech_recognition as sr
from rich.console import Console
import time
import sounddevice as sd
import numpy as np

console = Console()

def list_audio_devices():
    """Lista todos los dispositivos de audio disponibles"""
    p = pyaudio.PyAudio()
    console.print("\n[bold blue]Dispositivos de Audio Disponibles:[/]")
    
    for i in range(p.get_device_count()):
        dev = p.get_device_info_by_index(i)
        name = dev['name']
        inputs = dev['maxInputChannels']
        outputs = dev['maxOutputChannels']
        
        if inputs > 0:
            console.print(f"[green]Dispositivo {i}: {name}")
            console.print(f"  Canales de entrada: {inputs}")
            console.print(f"  Canales de salida: {outputs}")
            console.print(f"  Tasa de muestreo predeterminada: {int(dev['defaultSampleRate'])}")
    
    p.terminate()

def test_microphone(duration=5, device_index=None):
    """Graba audio por un número específico de segundos y lo reproduce"""
    # Parámetros de audio más conservadores
    CHUNK = 4096  # Buffer más grande
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000  # Tasa de muestreo más baja
    RECORD_SECONDS = duration
    WAVE_OUTPUT_FILENAME = "test_recording.wav"

    p = pyaudio.PyAudio()

    try:
        # Mostrar información del dispositivo seleccionado
        if device_index is None:
            device_index = p.get_default_input_device_info()['index']
        
        device_info = p.get_device_info_by_index(device_index)
        console.print(f"\n[blue]Usando dispositivo: {device_info['name']}[/]")
        console.print(f"[blue]Tasa de muestreo: {RATE}Hz[/]")
        console.print(f"[blue]Tamaño de buffer: {CHUNK} frames[/]")

        # Abrir stream con manejo de errores
        try:
            stream = p.open(format=FORMAT,
                          channels=CHANNELS,
                          rate=RATE,
                          input=True,
                          input_device_index=device_index,
                          frames_per_buffer=CHUNK)
        except Exception as e:
            console.print(f"[bold red]Error abriendo el stream: {str(e)}[/]")
            return

        console.print("\n[bold yellow]Iniciando grabación...[/]")
        console.print("[yellow]Habla algo...[/]")

        frames = []
        
        # Grabar audio con mejor manejo de errores
        for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
            try:
                data = stream.read(CHUNK, exception_on_overflow=False)
                frames.append(data)
                if i % 5 == 0:  # Actualizar progreso cada 5 chunks
                    console.print(".", end="")
            except Exception as e:
                console.print(f"\n[red]Error leyendo audio: {str(e)}[/]")
                break

        console.print("\n[bold green]¡Grabación completada![/]")

        # Detener stream
        stream.stop_stream()
        stream.close()

        # Guardar el archivo
        wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
        wf.close()

        console.print("[bold blue]Audio guardado en test_recording.wav[/]")

    except Exception as e:
        console.print(f"[bold red]Error en la grabación: {str(e)}[/]")
    
    finally:
        p.terminate()

def test_speech_recognition(device_index=None):
    """Prueba el reconocimiento de voz"""
    r = sr.Recognizer()
    
    console.print("\n[bold blue]Prueba de Reconocimiento de Voz[/]")
    
    try:
        # Usar el dispositivo específico si se proporciona
        if device_index is not None:
            mic = sr.Microphone(device_index=device_index)
        else:
            mic = sr.Microphone()
        
        with mic as source:
            # Configuración inicial
            r.dynamic_energy_threshold = True
            r.energy_threshold = 4000  # Aumentado para ignorar más ruido de fondo
            r.dynamic_energy_adjustment_damping = 0.15
            r.dynamic_energy_ratio = 1.5
            r.pause_threshold = 0.8  # Reducido para detectar pausas más cortas
            r.phrase_threshold = 0.3
            r.non_speaking_duration = 0.4
            
            # Ajuste de ruido ambiental más largo
            console.print("[yellow]Calibrando para el ruido ambiental (mantén silencio)...[/]")
            r.adjust_for_ambient_noise(source, duration=3)
            
            # Mostrar configuración actual
            console.print(f"[blue]Umbral de energía actual: {r.energy_threshold}[/]")
            
            console.print("[bold green]Escuchando...[/]")
            console.print("[yellow]Habla algo (intenta estar cerca del micrófono)...[/]")
            
            try:
                audio = r.listen(source, timeout=5, phrase_time_limit=10)
                console.print("[yellow]Procesando audio...[/]")
                
                try:
                    # Intentar con diferentes niveles de confianza
                    text = r.recognize_google(audio, language="es-ES", show_all=True)
                    
                    if isinstance(text, dict) and 'alternative' in text:
                        # Mostrar todas las alternativas con su confianza
                        console.print("[green]Alternativas reconocidas:[/]")
                        for alt in text['alternative']:
                            confidence = alt.get('confidence', 0)
                            transcript = alt.get('transcript', '')
                            console.print(f"[blue]- {transcript} (Confianza: {confidence:.2%})[/]")
                    else:
                        # Si no hay alternativas, mostrar el texto directo
                        console.print(f"[bold green]Texto reconocido:[/] {text}")
                        
                except sr.UnknownValueError:
                    console.print("[red]No se pudo entender el audio. Intenta:[/]")
                    console.print("1. Hablar más cerca del micrófono")
                    console.print("2. Hablar más claro y pausado")
                    console.print("3. Reducir el ruido ambiental")
                except sr.RequestError as e:
                    console.print(f"[red]Error con el servicio de Google: {e}[/]")
                    
            except sr.WaitTimeoutError:
                console.print("[red]No se detectó audio en el tiempo especificado[/]")
                
    except Exception as e:
        console.print(f"[bold red]Error en el reconocimiento: {str(e)}[/]")

def test_audio():
    """Prueba básica de grabación y reproducción de audio"""
    duration = 3  # segundos de grabación
    sample_rate = 44100  # frecuencia de muestreo estándar
    channels = 1

    console.print("Dispositivos de audio disponibles:")
    console.print(sd.query_devices())

    # Seleccionar dispositivos
    input_device = int(input("\nSelecciona dispositivo de entrada (número): "))
    output_device = int(input("Selecciona dispositivo de salida (número): "))

    console.print("\nGrabando 3 segundos...")
    recording = sd.rec(int(duration * sample_rate), 
                      samplerate=sample_rate, 
                      channels=channels,
                      device=input_device)

    # Esperar a que termine la grabación
    sd.wait()

    console.print("Reproduciendo...")
    sd.play(recording, sample_rate, device=output_device)
    sd.wait()

    console.print("¡Listo!")

def test_basic_audio():
    # Configuración
    duration = 3  # segundos
    sample_rate = 44100
    channels = 1
    
    print("Iniciando prueba básica de audio...")
    print("Grabando 3 segundos... (por favor habla algo)")
    
    # Grabar
    recording = sd.rec(
        int(duration * sample_rate),
        samplerate=sample_rate,
        channels=channels,
        dtype=np.float32,
        device=1  # HD-Audio Generic
    )
    sd.wait()
    
    print("Reproduciendo la grabación...")
    # Reproducir
    sd.play(recording, sample_rate, device=1)  # HD-Audio Generic
    sd.wait()
    
    print("Prueba completada!")

def main():
    selected_device = None
    
    while True:
        console.print("\n[bold cyan]Menú de Pruebas de Audio[/]")
        console.print("1. Listar dispositivos de audio")
        console.print("2. Seleccionar dispositivo de audio")
        console.print("3. Probar grabación de micrófono")
        console.print("4. Probar reconocimiento de voz")
        console.print("5. Ajustar configuración de audio")
        console.print("6. Prueba básica de audio")
        console.print("7. Prueba básica de audio (simple)")
        console.print("8. Salir")
        
        choice = input("\nElige una opción (1-8): ")
        
        if choice == '1':
            list_audio_devices()
        elif choice == '2':
            device_index = input("Ingresa el índice del dispositivo: ")
            try:
                selected_device = int(device_index)
                console.print(f"[green]Dispositivo {selected_device} seleccionado[/]")
            except:
                console.print("[red]Índice inválido[/]")
        elif choice == '3':
            duration = input("Duración de la grabación en segundos (default 5): ")
            try:
                duration = int(duration)
            except:
                duration = 5
            test_microphone(duration, selected_device)
        elif choice == '4':
            test_speech_recognition(selected_device)
        elif choice == '5':
            console.print("\n[bold cyan]Configuración de Audio[/]")
            console.print("1. Aumentar sensibilidad al ruido")
            console.print("2. Disminuir sensibilidad al ruido")
            console.print("3. Ajuste automático")
            
            sub_choice = input("\nElige una opción (1-3): ")
            if sub_choice == '1':
                r = sr.Recognizer()
                r.energy_threshold -= 500
                console.print(f"[green]Sensibilidad aumentada. Nuevo umbral: {r.energy_threshold}[/]")
            elif sub_choice == '2':
                r = sr.Recognizer()
                r.energy_threshold += 500
                console.print(f"[green]Sensibilidad disminuida. Nuevo umbral: {r.energy_threshold}[/]")
            elif sub_choice == '3':
                console.print("[yellow]Usa la opción 4 para un nuevo ajuste automático[/]")
        elif choice == '6':
            test_audio()
        elif choice == '7':
            test_basic_audio()
        elif choice == '8':
            break
        else:
            console.print("[red]Opción no válida[/]")
        
        time.sleep(1)

if __name__ == "__main__":
    main()
