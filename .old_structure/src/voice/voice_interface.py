import os
import logging
import tempfile
import asyncio
import numpy as np
import sounddevice as sd
import soundfile as sf
from TTS.api import TTS
import whisper
import torch
from rich.console import Console
from typing import Optional, Callable, Awaitable
import wave
from datetime import datetime
import resampy
import pygame

def list_audio_devices():
    """Lista todos los dispositivos de audio disponibles"""
    print("\nDispositivos de audio disponibles:")
    print("----------------------------------")
    devices = sd.query_devices()
    for i, dev in enumerate(devices):
        print(f"{i}: {dev['name']}")
        print(f"   Canales entrada: {dev['max_input_channels']}")
        print(f"   Canales salida: {dev['max_output_channels']}")
        print(f"   Frecuencias soportadas: {dev['default_samplerate']}")
        print()
    return devices

class VoiceInterface:
    """Interfaz de voz mejorada usando Whisper y Coqui TTS"""
    
    def __init__(self, language: str = "es", input_device: Optional[int] = 4, 
                 output_device: Optional[int] = 4, whisper_model: str = "medium"):
        self.language = language
        self.input_device = input_device
        self.output_device = output_device
        self.console = Console()
        
        # Mostrar dispositivos disponibles si no se especificaron
        if input_device is None or output_device is None:
            list_audio_devices()
        
        # Configuración de audio optimizada
        self.RATE = 16000  # Tasa de muestreo que sabemos que funciona
        self.CHANNELS = 1
        self.CHUNK = 1024
        self.FORMAT = 'float32'  # Formato que funciona bien con sounddevice
        
        # Obtener la tasa de muestreo soportada por el dispositivo de salida
        device_info = sd.query_devices(self.output_device, 'output')
        self.OUTPUT_RATE = int(device_info['default_samplerate'])
        
        # Configurar logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Cargar modelo de Whisper
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.logger.info(f"Usando dispositivo: {self.device}")
        self.model = whisper.load_model(whisper_model).to(self.device)
        
        # Configurar Coqui TTS con el modelo más reciente en español
        self.logger.info("Configurando Coqui TTS...")
        try:
            # Intentar cargar el modelo más reciente
            self.tts = TTS(model_name="tts_models/es/css10/vits").to(self.device)
        except Exception as e:
            self.logger.error(f"Error cargando el modelo TTS: {e}")
            raise
        
        # Inicializar pygame para reproducción de audio
        pygame.mixer.init()
        pygame.mixer.set_num_channels(8)  # Aumentar número de canales
        
        # Crear directorio temporal si no existe
        self.temp_dir = os.path.join(os.getcwd(), "temp_audio")
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # Crear y cargar sonidos de notificación
        self._create_notification_sounds()
        self.start_beep = pygame.mixer.Sound(os.path.join(self.temp_dir, "start_listening.wav"))
        self.stop_beep = pygame.mixer.Sound(os.path.join(self.temp_dir, "stop_listening.wav"))
    
    def _create_notification_sounds(self):
        """Crear sonidos de notificación para inicio y fin de escucha"""
        # Sonido de inicio (beep ascendente)
        start_file = os.path.join(self.temp_dir, "start_listening.wav")
        t = np.linspace(0, 0.1, int(self.RATE * 0.1))
        start_note = np.sin(2 * np.pi * 440 * t) * np.exp(t * 5)
        start_note = np.clip(start_note, -0.3, 0.3)
        self._save_wave(start_file, start_note)
        
        # Sonido de fin (beep descendente)
        stop_file = os.path.join(self.temp_dir, "stop_listening.wav")
        stop_note = np.sin(2 * np.pi * 880 * t) * np.exp(-t * 5)
        stop_note = np.clip(stop_note, -0.3, 0.3)
        self._save_wave(stop_file, stop_note)
    
    def _save_wave(self, filename, audio_data):
        """Guardar datos de audio como archivo WAV"""
        audio_data = (audio_data * 32767).astype(np.int16)
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.RATE)
            wf.writeframes(audio_data.tobytes())
    
    def _play_sound(self, sound):
        """Reproducir un sonido y esperar a que termine"""
        try:
            channel = sound.play()
            while channel.get_busy():
                pygame.time.wait(10)
        except Exception as e:
            self.logger.error(f"Error reproduciendo sonido: {e}")
    
    def _play_notification(self, sound_file):
        """Reproducir un sonido de notificación"""
        try:
            self._play_sound(sound_file)
        except Exception as e:
            self.logger.error(f"Error reproduciendo notificación: {e}")
    
    def _get_temp_filepath(self) -> str:
        """Genera un nombre de archivo temporal único"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return os.path.join(self.temp_dir, f"temp_audio_{timestamp}.wav")
    
    async def listen(self, timeout: int = 5) -> Optional[str]:
        """Graba y reconoce voz usando Whisper"""
        try:
            print("\n🎤 Presiona Enter cuando estés listo para hablar (o Ctrl+C para salir)...")
            try:
                input()  # Esperar Enter
            except KeyboardInterrupt:
                print("\n👋 Programa terminado!")
                raise SystemExit
            
            # Reproducir sonido de inicio
            self._play_notification(self.start_beep)
            
            print("\n" + "=" * 50)
            print("🎤 ESCUCHANDO... (habla ahora)")
            print("=" * 50)
            
            print("⏺️  Grabando... (presiona Enter para detener)")
            
            audio_data = []
            recording = True
            stop_recording = False
            
            def callback(indata, frames, time, status):
                if status:
                    self.logger.warning(f"Status: {status}")
                if not stop_recording:
                    audio_data.append(indata.copy())
                    # Mostrar progreso
                    duration = len(audio_data) * self.CHUNK / self.RATE
                    bars = "=" * int(duration * 10)
                    spaces = " " * (50 - len(bars))
                    print(f"\rGrabando: [{bars}{spaces}] {duration:.1f}s", end="", flush=True)
            
            # Iniciar grabación
            stream = sd.InputStream(callback=callback,
                                 device=self.input_device,
                                 channels=self.CHANNELS,
                                 samplerate=self.RATE,
                                 blocksize=self.CHUNK,
                                 dtype=self.FORMAT)
            
            with stream:
                # Esperar hasta que el usuario presione Enter o Ctrl+C
                try:
                    input()
                    stop_recording = True
                except KeyboardInterrupt:
                    stop_recording = True
                    print("\n👋 Grabación cancelada!")
                    return None
            
            # Reproducir sonido de fin
            self._play_notification(self.stop_beep)
            
            print("\n" + "-" * 50)
            print("🔄 Procesando audio...")
            print("-" * 50)
            
            if not audio_data:
                print("\n⚠️ No se detectó audio!")
                return None
            
            # Convertir audio a numpy array
            audio = np.concatenate(audio_data, axis=0)
            
            # Guardar audio en archivo temporal
            temp_path = self._get_temp_filepath()
            sf.write(temp_path, audio, self.RATE)
            
            # Transcribir con Whisper
            print("\n🎯 Transcribiendo...")
            result = self.model.transcribe(temp_path, language=self.language)
            transcribed_text = result["text"].strip()
            
            # Limpiar archivo temporal
            os.remove(temp_path)
            
            if transcribed_text:
                print(f"\n🗣️  Texto reconocido: {transcribed_text}")
                return transcribed_text
            else:
                print("\n⚠️ No se pudo reconocer ningún texto")
                return None
            
        except Exception as e:
            self.logger.error(f"Error durante la grabación/transcripción: {e}")
            return None

    async def speak(self, text: str):
        """Sintetiza y reproduce texto usando TTS"""
        try:
            if not text:
                self.logger.warning("No hay texto para sintetizar")
                return
            
            print("\n" + "=" * 50)
            print("🔊 RESPONDIENDO...")
            print("=" * 50)
            print(f"'{text}'")
            
            # Generar audio
            temp_path = self._get_temp_filepath()
            self.tts.tts_to_file(text=text, file_path=temp_path)
            
            # Reproducir audio
            sound = pygame.mixer.Sound(temp_path)
            self._play_sound(sound)
            
            print("-" * 50)
            
            # Limpiar archivo temporal
            try:
                os.remove(temp_path)
            except:
                pass
            
        except Exception as e:
            self.logger.error(f"Error en speak: {e}")
            print("\n⚠️ Error al sintetizar el texto")
    
    def is_wake_word(self, text: str) -> bool:
        """Verifica si el texto contiene la palabra de activación"""
        wake_words = ["nutrición", "agente", "consulta", "ayuda"]
        words = text.lower().split()
        return any(word in words for word in wake_words)
    
    async def run_voice_interface(self, process_query: Callable[[str], Awaitable[str]]):
        """Ejecuta la interfaz de voz en un bucle"""
        print("\n📝 Instrucciones:")
        print("  1. Presiona Enter cuando quieras hablar")
        print("  2. Habla durante 5 segundos")
        print("  3. Espera la transcripción")
        print("  4. Di 'salir' o presiona Ctrl+C en cualquier momento para terminar")
        
        try:
            while True:
                text = await self.listen()
                if text:
                    if text.lower().strip() in ['salir', 'terminar', 'adiós', 'chau']:
                        print("\n👋 ¡Hasta luego!")
                        break
                    
                    response = await process_query(text)
                    if response:
                        print(f"\n🤖 Respuesta: {response}")
        except KeyboardInterrupt:
            print("\n👋 Programa terminado!")
        except SystemExit:
            pass
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")

# Ejemplo de uso
async def main():
    try:
        print("\n🎤 Iniciando interfaz de voz...")
        print("📝 Instrucciones:")
        print("  1. Presiona Enter cuando quieras hablar")
        print("  2. Habla durante 5 segundos")
        print("  3. Espera la transcripción")
        print("  4. Di 'salir' o presiona Ctrl+C para terminar")
        print("\nPrueba preguntando sobre nutrición deportiva:")
        print("  - '¿Qué debo comer antes de entrenar?'")
        print("  - '¿Cuáles son las mejores fuentes de proteína?'")
        print("  - '¿Qué alimentos me dan más energía?'")
        
        # Inicializar el agente de nutrición
        from agentic_rag import AgenticNutritionRAG
        agent = AgenticNutritionRAG()
        await agent.load_knowledge_base('knowledge_base.json')
        
        # Usar directamente el dispositivo 4 (HD-Audio Generic)
        voice = VoiceInterface(input_device=4, output_device=4, whisper_model="medium")
        
        print("\n✅ Sistema iniciado y listo para escuchar!")
        
        async def process_query(query: str) -> str:
            """Procesa la consulta usando el agente de nutrición"""
            if query.lower().strip() in ['salir', 'terminar', 'adiós', 'chau']:
                return "¡Hasta luego!"
                
            response = await agent.answer_question(query)
            if "error" in response:
                return "Lo siento, hubo un error procesando tu consulta. Por favor, intenta de nuevo."
                
            # Crear respuesta hablada más concisa
            spoken_response = "Basado en mi análisis: "
            analysis_sentences = response['análisis'].split('.')[:3]
            spoken_response += '. '.join(analysis_sentences) + '.'
            
            action_sentences = response['plan_de_acción'].split('.')[:2]
            spoken_response += "\nMis recomendaciones principales son: "
            spoken_response += '. '.join(action_sentences) + '.'
            
            return spoken_response
        
        await voice.run_voice_interface(process_query)
        
    except KeyboardInterrupt:
        print("\n👋 ¡Hasta luego! Programa finalizado por el usuario.")
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        print("Intenta reiniciar el programa si el error persiste.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
