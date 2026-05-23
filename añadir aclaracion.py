import json
import tkinter as tk
from tkinter import messagebox

JSON_PATH = 'main.json'

# --- Cargar datos ---
with open(JSON_PATH, 'r', encoding='utf-8') as f:
    aclaraciones = json.load(f)

# --- Ventana principal ---
root = tk.Tk()
root.title('Añadir Aclaración')
root.geometry('420x380')
root.resizable(False, False)
root.configure(bg='#1e1e2e')

# --- Estilos ---
BG       = '#1e1e2e'
FG       = '#cdd6f4'
ENTRY_BG = '#313244'
BTN_BG   = '#89b4fa'
BTN_FG   = '#1e1e2e'
FONT     = ('Consolas', 11)
FONT_B   = ('Consolas', 11, 'bold')

def label(parent, text, **kw):
    return tk.Label(parent, text=text, bg=BG, fg=FG, font=FONT, **kw)

def entry(parent, textvariable=None):
    return tk.Entry(parent, textvariable=textvariable, bg=ENTRY_BG, fg=FG,
                    insertbackground=FG, font=FONT, relief='flat',
                    highlightthickness=1, highlightbackground='#45475a',
                    highlightcolor=BTN_BG)

def btn(parent, text, command, color=BTN_BG):
    return tk.Button(parent, text=text, command=command,
                     bg=color, fg=BTN_FG, font=FONT_B,
                     relief='flat', cursor='hand2',
                     padx=12, pady=6, activebackground='#b4befe',
                     activeforeground=BTN_FG)

# --- Variables ---
var_nombre  = tk.StringVar()
var_key     = tk.StringVar()
var_valor   = tk.StringVar()
entries_frame = None

# --- Lista de keys acumuladas en esta sesión ---
keys_pendientes = {}   # {nombre: {key: valor, ...}}

def limpiar_keys():
    var_key.set('')
    var_valor.set('')
    actualizar_lista()

def actualizar_lista():
    lista.delete(0, tk.END)
    nombre = var_nombre.get().strip()
    if nombre in keys_pendientes:
        for k, v in keys_pendientes[nombre].items():
            lista.insert(tk.END, f'  {k}  →  {v}')

def añadir_key():
    nombre = var_nombre.get().strip()
    key    = var_key.get().strip()
    valor  = var_valor.get().strip()

    if not nombre:
        messagebox.showwarning('Falta nombre', 'Escribe un nombre primero.')
        return
    if not key or not valor:
        messagebox.showwarning('Campos vacíos', 'Rellena la key y el texto.')
        return

    if nombre not in keys_pendientes:
        keys_pendientes[nombre] = {}
    keys_pendientes[nombre][key] = valor

    var_key.set('')
    var_valor.set('')
    actualizar_lista()

def guardar_y_cerrar():
    if not keys_pendientes:
        messagebox.showinfo('Nada que guardar', 'No has añadido ninguna aclaración.')
        return

    for nombre, keys in keys_pendientes.items():
        if nombre not in aclaraciones:
            aclaraciones[nombre] = {}
        aclaraciones[nombre].update(keys)

    with open(JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(aclaraciones, f, ensure_ascii=False, indent=4)

    messagebox.showinfo('Guardado', '¡Aclaraciones guardadas correctamente!')
    root.destroy()

def cancelar():
    root.destroy()

# --- Layout ---
tk.Label(root, text='✦ AÑADIR ACLARACIÓN', bg=BG, fg=BTN_BG,
         font=('Consolas', 13, 'bold')).pack(pady=(18, 10))

frame = tk.Frame(root, bg=BG)
frame.pack(padx=24, fill='x')

label(frame, 'Nombre:').grid(row=0, column=0, sticky='w', pady=4)
entry(frame, var_nombre).grid(row=0, column=1, sticky='ew', padx=(8, 0), pady=4)

label(frame, 'Key:').grid(row=1, column=0, sticky='w', pady=4)
entry(frame, var_key).grid(row=1, column=1, sticky='ew', padx=(8, 0), pady=4)

label(frame, 'Texto:').grid(row=2, column=0, sticky='w', pady=4)
entry(frame, var_valor).grid(row=2, column=1, sticky='ew', padx=(8, 0), pady=4)

frame.columnconfigure(1, weight=1)

btn(frame, '+ Añadir key', añadir_key).grid(
    row=3, column=0, columnspan=2, sticky='ew', pady=(10, 2))

# --- Lista de keys añadidas ---
tk.Label(root, text='Keys añadidas:', bg=BG, fg='#6c7086',
         font=('Consolas', 9)).pack(anchor='w', padx=24, pady=(8, 2))

lista = tk.Listbox(root, bg=ENTRY_BG, fg=FG, font=('Consolas', 10),
                   relief='flat', height=5, selectbackground='#45475a',
                   highlightthickness=0, bd=0)
lista.pack(padx=24, fill='x')

# --- Botones finales ---
bf = tk.Frame(root, bg=BG)
bf.pack(pady=14, padx=24, fill='x')

btn(bf, '💾 Guardar y cerrar', guardar_y_cerrar).pack(side='left', expand=True, fill='x', padx=(0, 6))
btn(bf, 'Cancelar', cancelar, color='#f38ba8').pack(side='left', expand=True, fill='x')

root.mainloop()