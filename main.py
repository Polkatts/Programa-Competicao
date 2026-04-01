import os
import shutil
import threading
import time
import json
import customtkinter as ctk
from tkinter import filedialog
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import filetype # Precisa de: pip install filetype

CONFIG_FILE = "config.json"

class OrganizadorHandler(FileSystemEventHandler):
    def __init__(self, destinos, log_func):
        self.destinos = destinos
        self.log_func = log_func

    def on_modified(self, event):
        pasta_origem = event.src_path if os.path.isdir(event.src_path) else os.path.dirname(event.src_path)
        
        for filename in os.listdir(pasta_origem):
            filepath = os.path.join(pasta_origem, filename)

            if os.path.isdir(filepath) or filename.endswith(('.tmp', '.crdownload', '.part')):
                continue

            nome, extensao = os.path.splitext(filename)
            extensao = extensao.lower()

            if not extensao:
                try:

                    kind = filetype.guess(filepath)
                    if kind:
                        extensao = f".{kind.extension}"
                        
                except Exception as e:
                    self.log_func(f"Erro ao identificar conteúdo de {filename}: {e}")

            if extensao in self.destinos:
                pasta_final = self.destinos[extensao]
                
                if not pasta_final or not os.path.exists(pasta_final): 
                    continue

                try:
                    
                    time.sleep(1)
                    
                    novo_nome = filename if filename.lower().endswith(extensao) else f"{filename}{extensao}"
                    destino_completo = os.path.join(pasta_final, novo_nome)
                    
                    base, ext = os.path.splitext(destino_completo)
                    contador = 1
                    while os.path.exists(destino_completo):
                        destino_completo = f"{base}_{contador}{ext}"
                        contador += 1
                    
                    shutil.move(filepath, destino_completo)
                    self.log_func(f"Sucesso: {filename} -> {os.path.basename(pasta_final)}")
                except Exception as e:
                    self.log_func(f"Falha ao mover {filename}: {e}")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Organizador Corporativo V2")
        self.geometry("700x620")
        
        self.caminhos = {
            "origem": "",
            "imagens": "",
            "videos": "",
            "docs": "",
            "excel": ""
        }
        
        self.observer = None
        self.carregar_configuracoes() 
        self.setup_ui()

    def setup_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.label_titulo = ctk.CTkLabel(self, text="Gerenciador de Arquivos Inteligente", font=("Roboto", 20, "bold"))
        self.label_titulo.grid(row=0, column=0, columnspan=2, pady=20)

        self.labels_caminhos = {}
        
        linhas = [
            ("Pasta de Origem:", "origem"),
            ("Imagens (.jpg, .png, .webp):", "imagens"),
            ("Vídeos (.mp4, .mov, .avi):", "videos"),
            ("Documentos (.pdf, .docx):", "docs"),
            ("Excel (.xlsx, .csv):", "excel")
        ]

        for i, (texto, chave) in enumerate(linhas, start=1):
            lbl_nome = ctk.CTkLabel(self, text=texto)
            lbl_nome.grid(row=i*2, column=0, padx=20, pady=(10, 0), sticky="w")
            
            caminho_exibido = self.caminhos[chave] if self.caminhos[chave] else "Não selecionado"
            lbl_status = ctk.CTkLabel(self, text=caminho_exibido, text_color="gray", font=("Arial", 10))
            lbl_status.grid(row=i*2+1, column=0, padx=25, sticky="w")
            self.labels_caminhos[chave] = lbl_status

            btn = ctk.CTkButton(self, text="Selecionar", width=100, command=lambda c=chave: self.escolher_pasta(c))
            btn.grid(row=i*2, column=1, rowspan=2, padx=20, sticky="e")

        self.btn_control = ctk.CTkButton(self, text="INICIAR MONITORAMENTO", fg_color="#2DAE60", hover_color="#27ae60", command=self.toggle_monitor)
        self.btn_control.grid(row=15, column=0, columnspan=2, pady=25, padx=20, sticky="ew")

        self.log_box = ctk.CTkTextbox(self, height=150)
        self.log_box.grid(row=16, column=0, columnspan=2, padx=20, pady=10, sticky="nsew")
        self.log_box.configure(state="disabled")

    def escolher_pasta(self, chave):
        caminho = filedialog.askdirectory()
        if caminho:
            self.caminhos[chave] = caminho
            self.labels_caminhos[chave].configure(text=caminho, text_color="white")
            self.salvar_configuracoes()
            self.adicionar_log(f"Configuração salva para {chave}.")

    def salvar_configuracoes(self):
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(self.caminhos, f)
        except Exception as e:
            self.adicionar_log(f"Erro ao salvar config: {e}")

    def carregar_configuracoes(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    self.caminhos = json.load(f)
            except:
                pass

    def adicionar_log(self, mensagem):
        self.log_box.configure(state="normal")
        timestamp = time.strftime('%H:%M:%S')
        self.log_box.insert("end", f"[{timestamp}] {mensagem}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def toggle_monitor(self):
        if not self.observer:
            if not self.caminhos["origem"]:
                self.adicionar_log("ERRO: Defina a pasta de origem primeiro!")
                return

            mapeamento = {
                ".jpg": self.caminhos["imagens"], ".png": self.caminhos["imagens"], ".jpeg": self.caminhos["imagens"],
                ".gif": self.caminhos["imagens"], ".webp": self.caminhos["imagens"],
                ".mov": self.caminhos["videos"], ".mp4": self.caminhos["videos"], ".avi": self.caminhos["videos"],
                ".pdf": self.caminhos["docs"], ".docx": self.caminhos["docs"], ".txt": self.caminhos["docs"],
                ".xlsx": self.caminhos["excel"], ".csv": self.caminhos["excel"]
            }

            self.event_handler = OrganizadorHandler(mapeamento, self.adicionar_log)
            self.observer = Observer()
            self.observer.schedule(self.event_handler, self.caminhos["origem"], recursive=False)
            
            thread = threading.Thread(target=self.observer.start, daemon=True)
            thread.start()
            
            self.btn_control.configure(text="PARAR MONITORAMENTO", fg_color="#E74C3C", hover_color="#c0392b")
            self.adicionar_log("Sistema de vigilância ativo.")
        else:
            self.observer.stop()
            self.observer = None
            self.btn_control.configure(text="INICIAR MONITORAMENTO", fg_color="#2DAE60", hover_color="#27ae60")
            self.adicionar_log("Sistema desligado.")

if __name__ == "__main__":
    app = App()
    app.mainloop()
