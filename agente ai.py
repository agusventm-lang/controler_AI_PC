import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from ollama import chat
import os
import re
import json
import threading
import pyttsx3
import platform
import psutil

with open('main.json', 'r', encoding='utf-8') as f:
    aclaraciones = json.load(f)

print(os.path.abspath(__file__))

def obtener_resumen_hardware():
    """Genera una cadena compacta con el hardware actual para el contexto de la IA."""
    try:
        info_sistema = platform.uname()
        ram = psutil.virtual_memory()
        
        # Detectar GPU usando psutil (info disponible en Windows)
        gpu_info = "No se detectó GPU dedicada"
        try:
            # Intentar obtener info de GPU a través de comandos del sistema
            import subprocess
            resultado = subprocess.run(
                ['wmic', 'path', 'win32_videocontroller', 'get', 'name'],
                capture_output=True, text=True, timeout=2
            )
            gpus = [linea.strip() for linea in resultado.stdout.split('\n') if linea.strip() and linea.strip() != 'Name']
            if gpus:
                gpu_info = ", ".join(gpus)
        except:
            pass
            
        particiones = []
        for p in psutil.disk_partitions():
            if os.name == 'nt' and 'cdrom' in p.opts:
                continue
            try:
                particiones.append(f"{p.device} ({p.fstype})")
            except:
                continue
        discos_info = ", ".join(particiones)

        resumen = (
            f"SO: {info_sistema.system} {info_sistema.release} ({info_sistema.machine}) | "
            f"CPU: {info_sistema.processor} ({psutil.cpu_count(logical=False)} núcleos físicos, {psutil.cpu_count(logical=True)} lógicos) | "
            f"RAM Total: {ram.total / (1024**3):.2f} GB | "
            f"GPU: {gpu_info} | "
            f"Discos y Unidades Detectadas: {discos_info}"
        )
        return resumen
    except Exception as e:
        return f"Error al recopilar hardware de forma dinámica: {e}"

def guardar_nueva_regla_en_archivo(clave, comando):
    ruta_script = os.path.abspath(__file__)
    try:
        with open(ruta_script, 'r', encoding='utf-8') as f:
            contenido = f.read()

        match = re.search(r'aclaraciones\s*=\s*\{', contenido)
        if match:
            pos_insercion = match.end()
            nueva_entrada = f"\n    '{clave}': {{ 'comando': r'{comando}' }},"
            nuevo_contenido = contenido[:pos_insercion] + nueva_entrada + contenido[pos_insercion:]
            
            with open(ruta_script, 'w', encoding='utf-8') as f:
                f.write(nuevo_contenido)
            print(f"💾 Guardado permanentemente en el script: {clave} -> {comando}")
            return True
    except Exception as e:
        print(f"❌ Error al guardar en el archivo: {e}")
        return False

def ejecutar_en_cmd(comando):
    try:
        print(f"🚀 Ejecutando:\n{comando}")
        subprocess.run(comando, shell=True, check=True, text=True)
        return True
    except Exception as e:
        print(f"❌ Error al ejecutar: {e}")
        return False

def es_pregunta_general(pregunta):
    """Detecta si es una pregunta general o una orden de ejecutar comando."""
    palabras_comando = ['abre', 'ejecuta', 'corre', 'inicia', 'abre', 'lanza', 'cierra', 'mata', 'detén', 'pon', 'escribe', 'pausa', 'reproduce', 'toca', 'busca', 'descarga']
    pregunta_lower = pregunta.lower()
    
    # Si contiene palabras de comando, es un comando
    if any(palabra in pregunta_lower for palabra in palabras_comando):
        return False
    
    # Si es pregunta (¿ o palabras como "cuál", "cuánto", "qué", "cómo"), es general
    if '¿' in pregunta or any(palabra in pregunta_lower for palabra in ['cuál', 'cuánto', 'qué', 'cómo', 'dónde', 'cuándo', 'por qué', 'sirve', 'es', 'pesa', 'mide', 'cuesta', 'es bueno', 'es malo']):
        return True
    
    return False

def obtener_respuesta_general_ia(pregunta_usuario):
    """Responde preguntas generales sin ejecutar comandos."""
    instrucciones = """Eres un asistente inteligente que responde preguntas generales de forma clara, concisa y útil.
    Tienes amplio conocimiento sobre:
    - Tecnología y hardware (GPUs, procesadores, juegos, etc.)
    - Ciencia (animales, geografía, física, biología)
    - Historia, cultura y sociedad
    - Consejos prácticos
    
    REGLAS:
    1. Responde de forma BREVE Y DIRECTA (máximo 2-3 frases)
    2. Si es sobre hardware/rendimiento, da información técnica clara
    3. Si es pregunta de hechos, responde con seguridad
    4. Sé amigable y natural
    5. NO incluyas ningún marcador especial como 'ªIª'
    """
    
    response = chat(
        model='gpt-oss:120b-cloud',
        messages=[
            {'role': 'system', 'content': instrucciones},
            {'role': 'user', 'content': pregunta_usuario},
        ]
    )
    return response.message.content.strip()

def obtener_comando_ia(pregunta_usuario, error_previo=None):
    # Extraemos dinámicamente el estado del hardware para pasárselo a la regla 12
    hardware_actual = obtener_resumen_hardware()

    instrucciones = f"""
    estas son las aclaraciones con las que trabajaras{aclaraciones}
    Eres un traductor de lenguaje natural a comandos de Windows (CMD o PowerShell).
    REGLAS ESTRICTAS:
    1. Responde con dos cosas la parte de lo que quieres decir una brebe texto y otra que su comienzo sera maracada colocando el texto  'ªIª' loego ira solo 
      el comando o bloque de código ejecutable en UNA SOLA LÍNEA o encadenado. No uses textos adicionales, ni comillas invertidas (```).
      #ejemplo:una abre youtuve
        claro aqui te habro toutuve tu tranquilo ªIª run chrome...
    2. Si el usuario quiere abrir un programa, usa 'start "" "ruta_al_programa"'. Recuerda usar siempre 'start ""' para no bloquear la consola.
    3. Si el usuario pide algo peligroso o imposible, responde: nose
    4. Si el juego es original de Steam (según la lista '{aclaraciones}'), usa: start steam://rungameid/ID
    5. Si el juego es pirata, y no se encuentra en la lista de aclaraciones: ({aclaraciones}), búscalo directamente en el Escritorio como acceso directo.
    6. REINTENTOS POR ERROR o BÚSQUEDA GLOBAL: Si el comando anterior falló o el usuario pide buscarlo en Windows, debes generar un comando en PowerShell que busque el archivo (.exe) desde la RAÍZ DEL DISCO (C:\\) de manera exacta y lo ejecute al encontrarlo.
    7. Si de repente eso falla, búscalo en el disco D:\\.
    8. ¡MUY IMPORTANTE!: Si necesitas ejecutar varias tareas o abrir varios programas a la vez, DEBES poner todos los comandos en la misma línea separados obligatoriamente por el operador ' & '.
    9. Configuración de perfiles de Chrome según la lista: Si pide spotify o chrome normal usa 'Default'. Si especifica colegio/cole usa 'Profile 2'.
    10. REGLA DE ESCRITURA AUTOMÁTICA: Si el usuario dice "escribe X" o "escribir X", debes anteponer OBLIGATORIAMENTE un retraso de 3 segundos con 'Start-Sleep -s 3;' para dar tiempo a que el usuario cambie de ventana activa.
        - Ejemplo exacto para escribir "hola": powershell -command "Start-Sleep -s 3; $wsh = New-Object -ComObject WScript.Shell; $wsh.SendKeys('hola')"
        - Si te piden escribir algo y dar enter: powershell -command "Start-Sleep -s 3; $wsh = New-Object -ComObject WScript.Shell; $wsh.SendKeys('hola{{ENTER}}')"
    11. LA CARPETA EN LA Q SE ENCUENTRA EL CODIGO ES (carpeta = os.path.dirname({os.path.abspath(__file__)})),y este es lo que compone la carpeta Mode          LastWriteTime         Length Name
        ----                -------------         ------ ----
        -a----        17/05/2026     22:27            8771 agente ai.py
        -a----        16/05/2026     14:43             135 asistente.bat
        -a----        17/05/2026     22:21            3140 main.json
    12. este es todo el hardware que tiene mi pc por si lo necesitas para optimizar los comandos o conocer las unidades de disco válidas: {hardware_actual}
    """
    
    contenido_usuario = pregunta_usuario
    if error_previo:
        contenido_usuario += f"\n[EL COMANDO ANTERIOR FALLÓ CON ESTE ERROR: {error_previo}. Por favor, genera un comando de búsqueda exacta para encontrar el archivo y ejecutarlo]"

    response = chat(
        model='gpt-oss:120b-cloud',
        messages=[
            {'role': 'system', 'content': instrucciones},
            {'role': 'user', 'content': contenido_usuario},
        ]
    )
    return response.message.content.strip()


class AsistenteVozGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Asistente PC")
        
        ancho, alto = 440, 360
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        pos_x = screen_width - ancho - 800
        pos_y = screen_height - alto - 500
        self.root.geometry(f"{ancho}x{alto}+{pos_x}+{pos_y}")
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True)

        self.historial_comandos = []

        # Inicializar el motor de voz de Windows (SAPI5)
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 175) 

        lbl_instruccion = tk.Label(root, text="¿Qué quieres que haga el sistema?", font=("Segoe UI", 10, "bold"))
        lbl_instruccion.pack(pady=(10, 5))

        self.entry_pregunta = tk.Entry(root, width=42, font=("Segoe UI", 10))
        self.entry_pregunta.pack(pady=5)
        self.entry_pregunta.focus_set()
        
        self.entry_pregunta.bind("<Return>", lambda event: self.procesar_orden())

        self.btn_enviar = tk.Button(root, text="Ejecutar comando", command=self.procesar_orden, bg="#4CAF50", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", padx=10)
        self.btn_enviar.pack(pady=5)

        tk.Label(root, text="Respuesta de la IA:", font=("Segoe UI", 8, "bold"), fg="#666666").pack(pady=(10, 0))
        
        self.frame_respuesta = tk.Frame(root, bg="#f4f7f6", bd=1, relief="solid")
        self.frame_respuesta.pack(pady=5, fill="x", padx=20)

        self.lbl_respuesta_ia = tk.Label(
            self.frame_respuesta, 
            text="Esperando una orden...", 
            font=("Segoe UI Semibold", 9, "italic"), 
            fg="#1a73e8", 
            bg="#f4f7f6",
            wraplength=380, 
            justify="center",
            pady=10
        )
        self.lbl_respuesta_ia.pack(fill="x")

        tk.Label(root, text="Historial reciente:", font=("Segoe UI", 8, "italic"), fg="#888888").pack(pady=(10, 2))
        self.combo_historial = ttk.Combobox(root, width=45, state="readonly")
        self.combo_historial.pack(pady=2)

    def decir_en_voz_alta(self, texto):
        """Función auxiliar para procesar la voz sin colgar el hilo secundario."""
        try:
            self.engine.say(texto)
            self.engine.runAndWait()
        except Exception as e:
            print(f"Error en el motor de voz: {e}")

    def procesar_orden(self):
        pregunta = self.entry_pregunta.get().strip()
        if not pregunta:
            return
            
        if pregunta.lower() == 'salir':
            self.root.destroy()
            return

        self.btn_enviar.config(state="disabled", bg="#cccccc")
        self.lbl_respuesta_ia.config(text="Pensando...", fg="#f39c12")
        self.entry_pregunta.delete(0, tk.END)

        hilo = threading.Thread(target=self._hilo_ia, args=(pregunta,))
        hilo.start()

    def _hilo_ia(self, pregunta):
        # Detectar si es pregunta general o comando
        if es_pregunta_general(pregunta):
            # Responder pregunta general
            respuesta = obtener_respuesta_general_ia(pregunta)
            print("Respuesta general:", respuesta)
            
            texto_a_decir = respuesta
            self.root.after(0, lambda t=respuesta: self.lbl_respuesta_ia.config(text=t, fg="#1a73e8"))
            self.root.after(0, lambda: self.agregar_al_historial(f"Q: {pregunta}"))
            
            self.decir_en_voz_alta(texto_a_decir)
            self.root.after(2000, lambda: self.btn_enviar.config(state="normal", bg="#4CAF50"))
            return
        
        # Si no es pregunta general, ejecutar como comando
        error_actual = None
        intentos = 2
        ejecutado_con_exito = False
        texto_a_decir = ""

        for intento in range(intentos):
            respuesta = obtener_comando_ia(pregunta, error_previo=error_actual)
            print("Respuesta cruda de Ollama:", respuesta)
            
            idx_separador = respuesta.find('ªIª')
            
            if idx_separador != -1:
                texto_ia = respuesta[:idx_separador].strip()
                comando = respuesta[idx_separador + 3:].strip()
            else:
                texto_ia = "Comando generado."
                comando = respuesta.strip()

            texto_a_decir = texto_ia
            self.root.after(0, lambda t=texto_ia: self.lbl_respuesta_ia.config(text=t, fg="#1a73e8"))

            if comando.lower() == "nose":
                msg_error = "No sé cómo hacer eso exactamente."
                self.root.after(0, lambda: self.lbl_respuesta_ia.config(text=msg_error, fg="#d93025"))
                self.root.after(0, lambda: self.agregar_al_historial(f"Fallo: {pregunta} (No sé)"))
                
                self.decir_en_voz_alta(msg_error)
                subprocess.run(["python", "añadir aclaracion.py"])
                self.root.after(0, lambda: self.btn_enviar.config(state="normal", bg="#4CAF50"))
                return

            exito = ejecutar_en_cmd(comando)
            if exito:
                self.root.after(0, lambda c=comando: self.agregar_al_historial(f"Éxito: {c}"))
                ejecutado_con_exito = True
                break
            else:
                error_actual = "El archivo o ruta no fue encontrado en el sistema o el comando falló."
                if intento == 1:
                    texto_a_decir = "El comando falló tras los intentos establecidos."
                    self.root.after(0, lambda: self.lbl_respuesta_ia.config(text=texto_a_decir, fg="#d93025"))
                    self.root.after(0, lambda: self.agregar_al_historial(f"Error: {pregunta}"))
                    subprocess.run(["python", "añadir aclaracion.py"])

        if texto_a_decir:
            self.decir_en_voz_alta(texto_a_decir)

        if ejecutado_con_exito:
            self.root.after(1000, self.root.destroy)
        else:
            self.root.after(0, lambda: self.btn_enviar.config(state="normal", bg="#4CAF50"))

    def agregar_al_historial(self, texto):
        self.historial_comandos.insert(0, texto)
        self.combo_historial['values'] = self.historial_comandos
        self.combo_historial.current(0)


if __name__ == "__main__":
    app = tk.Tk()
    ventana = AsistenteVozGUI(app)
    app.mainloop()