import os
import shutil
import threading
import time
import json
import customtkinter as ctk
from tkinter import filedialog
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import filetype

CONFIG_FILE = "config.json"

class OrganizadorHandler(FileSystemEventHandler):
    def __init__(self, destinos, log_func):
        self.destinos = destinos
        self.log_func = log_func

    def on_created(self, event):
        if not event.is_directory:
            self.processar(event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            self.processar(event.src_path)

    def processar(self, filepath):
        if not os.path.exists(filepath):
            return

        filename = os.path.basename(filepath)
        
        if filename.endswith(('.tmp', '.crdownload', '.part')) or filename.startswith('.'):
            return

        
        for _ in range(5):
            try:
                with open(filepath, 'rb'):
                    break
            except IOError:
                time.sleep(1)
        else:
            return 

        nome_base, extensao_original = os.path.splitext(filename)
        extensao = extensao_original.lower()

        if not extensao:
            try:
                kind = filetype.guess(filepath)
                if kind:
                    extensao = f".{kind.extension}"
            except:
                pass

        if extensao in self.destinos:
            pasta_final = self.destinos[extensao]
            if not pasta_final or not os.path.exists(pasta_final):
                return

            try:
                nome_final = filename if filename.lower().endswith(extensao) else f"{filename}{extensao}"
                caminho_destino = os.path.join(pasta_final, nome_final)
                
                base, ext = os.path.splitext(caminho_destino)
                contador = 1
                while os.path.exists(caminho_destino):
                    caminho_destino = f"{base}_{contador}{ext}"
                    contador += 1
                
                shutil.move(filepath, caminho_destino)
                self.log_func(f"Movido: {filename}")
            except Exception as e:
                self.log_func(f"Erro ao mover {filename}: {e}")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Organizador Corporativo Pro V3")
        self.geometry("700x650")
        
        self.caminhos = {"origem": "", "imagens": "", "videos": "", "docs": "", "excel": ""}
        self.observer = None
        self.carregar_configuracoes() 
        self.setup_ui()

    def setup_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.label_titulo = ctk.CTkLabel(self, text="Gerenciador de Arquivos Inteligente", font=("Roboto", 22, "bold"))
        self.label_titulo.grid(row=0, column=0, columnspan=2, pady=20)

        self.labels_caminhos = {}
        config_linhas = [
            ("Pasta de Origem:", "origem"),
            ("Imagens (.jpg, .png):", "imagens"),
            ("Vídeos (.mp4, .mov):", "videos"),
            ("Documentos (.pdf, .docx):", "docs"),
            ("Planilhas Excel:", "excel")
        ]

        for i, (texto, chave) in enumerate(config_linhas, start=1):
            lbl_nome = ctk.CTkLabel(self, text=texto, font=("Arial", 12, "bold"))
            lbl_nome.grid(row=i*2, column=0, padx=20, pady=(10, 0), sticky="w")
            
            caminho_texto = self.caminhos[chave] if self.caminhos[chave] else "Não configurado"
            lbl_status = ctk.CTkLabel(self, text=caminho_texto, text_color="gray", font=("Arial", 10))
            lbl_status.grid(row=i*2+1, column=0, padx=25, sticky="w")
            self.labels_caminhos[chave] = lbl_status

            btn = ctk.CTkButton(self, text="Alterar", width=100, command=lambda c=chave: self.escolher_pasta(c))
            btn.grid(row=i*2, column=1, rowspan=2, padx=20, sticky="e")

        self.btn_control = ctk.CTkButton(self, text="LIGAR ORGANIZADOR", fg_color="#2DAE60", hover_color="#219150", height=50, command=self.toggle_monitor)
        self.btn_control.grid(row=15, column=0, columnspan=2, pady=30, padx=20, sticky="ew")

        self.log_box = ctk.CTkTextbox(self, height=180)
        self.log_box.grid(row=16, column=0, columnspan=2, padx=20, pady=(0, 20), sticky="nsew")
        self.log_box.configure(state="disabled")

    def escolher_pasta(self, chave):
        caminho = filedialog.askdirectory()
        if caminho:
            self.caminhos[chave] = caminho
            self.labels_caminhos[chave].configure(text=caminho, text_color="#3498DB")
            self.salvar_configuracoes()

    def salvar_configuracoes(self):
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.caminhos, f)

    def carregar_configuracoes(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    self.caminhos = json.load(f)
            except: pass

    def adicionar_log(self, mensagem):
        
        self.after(0, self._escrever_log, mensagem)

    def _escrever_log(self, mensagem):
        self.log_box.configure(state="normal")
        ts = time.strftime('%H:%M:%S')
        self.log_box.insert("end", f"[{ts}] {mensagem}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def varredura_inicial(self, handler):
        origem = self.caminhos["origem"]
        if not origem or not os.path.exists(origem): return

        self.adicionar_log("Iniciando varredura de arquivos existentes...")
        arquivos = [f for f in os.listdir(origem) if os.path.isfile(os.path.join(origem, f))]
        
        for filename in arquivos:
            filepath = os.path.join(origem, filename)
            handler.processar(filepath)
            
        self.adicionar_log(f"Varredura finalizada. {len(arquivos)} itens verificados.")

    def toggle_monitor(self):
        if not self.observer:
            if not self.caminhos["origem"]:
                self.adicionar_log("ERRO: Configure a origem primeiro!")
                return
            
            mapeamento = {
                ".jpg": self.caminhos["imagens"], ".png": self.caminhos["imagens"], ".jpeg": self.caminhos["imagens"],
                ".webp": self.caminhos["imagens"], ".gif": self.caminhos["imagens"],
                ".mp4": self.caminhos["videos"], ".mov": self.caminhos["videos"], ".avi": self.caminhos["videos"],
                ".pdf": self.caminhos["docs"], ".docx": self.caminhos["docs"], ".txt": self.caminhos["docs"],
                ".xlsx": self.caminhos["excel"], ".xls": self.caminhos["excel"], ".csv": self.caminhos["excel"]
            }

            self.event_handler = OrganizadorHandler(mapeamento, self.adicionar_log)
           
            thread_varredura = threading.Thread(target=self.varredura_inicial, args=(self.event_handler,), daemon=True)
            thread_varredura.start()

            self.observer = Observer()
            self.observer.schedule(self.event_handler, self.caminhos["origem"], recursive=False)
            self.observer.start()
            
            self.btn_control.configure(text="DESLIGAR ORGANIZADOR", fg_color="#E74C3C")
            self.adicionar_log("Vigilância em tempo real ativa.")
        else:
            self.observer.stop()
            self.observer.join()
            self.observer = None
            self.btn_control.configure(text="LIGAR ORGANIZADOR", fg_color="#2DAE60")
            self.adicionar_log("Monitoramento encerrado.")

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    app = App()
    app.mainloop()
