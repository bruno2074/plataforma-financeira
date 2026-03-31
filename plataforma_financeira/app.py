import customtkinter as ctk
import sqlcipher3.dbapi2 as sqlite3
import os
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import io
import hashlib
import secrets
import uuid
import json
from PIL import Image
from tkinter import filedialog, ttk

# --- Paleta Wealth.Core (Sci-Fi HUD) ---
COR_FUNDO = "#050914"       # Void Black/Blue (Fundo principal)
COR_CARD = "#0A1128"        # Deep Space Blue (Fundo dos painéis)
COR_BORDAS = "#00F0FF"      # Cyan Neon (Bordas simulando holograma)
COR_TEXTO = "#8AB4F8"       # Light Tech Blue (Texto padrão)
COR_RECEITA = "#00FF9D"     # Neon Green
COR_DESPESA = "#FF0055"     # Neon Red/Pink
COR_DESTAQUE = "#B026FF"    # Neon Purple

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# =====================================================================
# MOTOR CRIPTOGRÁFICO E MFA DE HARDWARE (ZERO TRUST)
# =====================================================================
def obter_salt_hardware_usuario(usuario):
    """MFA Físico: Extrai MAC Address e atrela ao nome do usuário."""
    mac = uuid.getnode()
    # Concatena MAC + Usuário para garantir salts únicos por tenant na mesma máquina
    return hashlib.sha256(f"{mac}_{usuario.lower()}".encode()).hexdigest()

def derivar_chave_db(usuario, senha_plana):
    """Motor KDF: Retorna a chave AES-256 final e o Salt utilizado."""
    salt = obter_salt_hardware_usuario(usuario)
    chave_hex = hashlib.pbkdf2_hmac(
        'sha512', 
        senha_plana.encode(), 
        salt.encode(), 
        210000
    ).hex()
    return chave_hex, salt

def gerar_chave_emergencia(usuario):
    """Gera chave de recuperação e salva no Shadow File do usuário."""
    chave_plana = secrets.token_hex(32) 
    hash_shadow = hashlib.sha512(chave_plana.encode()).hexdigest()
    shadow_file = f"shadow_{usuario.lower()}.json"
    with open(shadow_file, 'w') as f:
        json.dump({'recovery_hash': hash_shadow}, f)
    return chave_plana

def validar_chave_emergencia(usuario, input_chave):
    """Validação offline da chave de emergência."""
    shadow_file = f"shadow_{usuario.lower()}.json"
    if not os.path.exists(shadow_file): 
        return False
    with open(shadow_file, 'r') as f:
        dados = json.load(f)
    hash_input = hashlib.sha512(input_chave.encode()).hexdigest()
    return secrets.compare_digest(hash_input, dados.get('recovery_hash', ''))

class PlataformaFinanceira(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Wealth Engine - Command Center")
        self.geometry("550x550")
        self.resizable(False, False)
        
        self.db_conn = None 
        self.usuario_atual = None
        self.db_path_atual = None
        self.modo_privacidade = False 
        self.tela_atual = "dash"      
        self.tentativas_falhas = 0 
        self.modo_lockdown = False

        self.style = ttk.Style()
        self.style.theme_use("default")
        # Cores da tabela adaptadas para o modo HUD
        self.style.configure(
            "Treeview", 
            background=COR_CARD, 
            foreground=COR_TEXTO, 
            fieldbackground=COR_CARD, 
            borderwidth=0, 
            rowheight=30, 
            font=("Courier", 10)
        )
        self.style.map('Treeview', background=[('selected', COR_BORDAS)], foreground=[('selected', '#000000')])
        self.style.configure(
            "Treeview.Heading", 
            background=COR_FUNDO, 
            foreground=COR_BORDAS, 
            relief="flat", 
            font=('Courier', 11, 'bold')
        )

        self.construir_tela_login()

    def inicializar_banco_relacional(self, db_path, chave_hex):
        """DDL Interno: Injeta estrutura SQL segura e blindada."""
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA key=\"x'{chave_hex}'\"")
        cursor.execute("PRAGMA foreign_keys = ON;")
        
        cursor.executescript('''
            CREATE TABLE IF NOT EXISTS tb_contas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                tipo TEXT NOT NULL,
                saldo_inicial REAL DEFAULT 0.0
            );
            CREATE TABLE IF NOT EXISTS tb_categorias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL UNIQUE,
                tipo_fluxo TEXT CHECK(tipo_fluxo IN ('RECEITA', 'DESPESA')) NOT NULL
            );
            CREATE TABLE IF NOT EXISTS tb_transacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conta_id INTEGER NOT NULL,
                categoria_id INTEGER NOT NULL,
                valor REAL NOT NULL,
                data_transacao DATE NOT NULL,
                descricao TEXT,
                FOREIGN KEY (conta_id) REFERENCES tb_contas(id) ON DELETE RESTRICT,
                FOREIGN KEY (categoria_id) REFERENCES tb_categorias(id) ON DELETE RESTRICT
            );
            CREATE TABLE IF NOT EXISTS tb_orcamentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                categoria_id INTEGER NOT NULL UNIQUE,
                limite_mensal REAL NOT NULL,
                FOREIGN KEY (categoria_id) REFERENCES tb_categorias(id) ON DELETE CASCADE
            );
        ''')
        # Injeção das categorias base (Auto-Healing)
        cursor.execute("INSERT OR IGNORE INTO tb_categorias (id, nome, tipo_fluxo) VALUES (1, 'Receitas Gerais', 'RECEITA')")
        cursor.execute("INSERT OR IGNORE INTO tb_categorias (id, nome, tipo_fluxo) VALUES (4, 'Despesas Gerais', 'DESPESA')")
        cursor.execute("INSERT OR IGNORE INTO tb_categorias (id, nome, tipo_fluxo) VALUES (5, 'Investimentos', 'DESPESA')")
        conn.commit()
        conn.close()

    def calcular_cores_dinamicas(self):
        try:
            cursor = self.db_conn.cursor()
            cursor.execute("""
                SELECT c.tipo_fluxo, SUM(t.valor) 
                FROM tb_transacoes t 
                JOIN tb_categorias c ON t.categoria_id = c.id 
                GROUP BY c.tipo_fluxo
            """)
            fluxos = dict(cursor.fetchall())
            rec = fluxos.get('RECEITA', 0.001) 
            desp = fluxos.get('DESPESA', 0)
            ratio = desp / rec
            
            if ratio >= 0.8: 
                return "#A5D6A7", "#D50000" 
            if ratio <= 0.5: 
                return "#00E676", "#EF9A9A" 
            return "#4CAF50", "#F44336" 
        except Exception: 
            return "#4CAF50", "#F44336"

    def ligar_clique_recursivo(self, widget, comando):
        """Aplica o evento de clique a um frame e a todos os seus filhos."""
        widget.bind("<Button-1>", comando)
        for filho in widget.winfo_children():
            self.ligar_clique_recursivo(filho, comando)

    def construir_tela_login(self):
        self.frame_login = ctk.CTkFrame(self)
        self.frame_login.pack(pady=40, padx=40, fill="both", expand=True)

        self.label_titulo = ctk.CTkLabel(self.frame_login, text="Cofre Criptográfico (MFA)", font=ctk.CTkFont(size=20, weight="bold"))
        self.label_titulo.pack(pady=(20, 10))

        self.entry_usuario = ctk.CTkEntry(self.frame_login, placeholder_text="ID do Usuário")
        self.entry_usuario.pack(pady=10, padx=20, fill="x")

        self.entry_senha = ctk.CTkEntry(self.frame_login, placeholder_text="Senha (Master Key)", show="*")
        self.entry_senha.pack(pady=10, padx=20, fill="x")

        self.entry_senha_confirma = ctk.CTkEntry(self.frame_login, placeholder_text="Confirme a Senha", show="*")

        self.btn_login = ctk.CTkButton(self.frame_login, text="Descriptografar (Autenticar)", command=self.tentar_login)
        self.btn_login.pack(pady=20, padx=20, fill="x")

        self.modo_registro = False
        def alternar_modo_auth():
            if not self.modo_registro:
                self.modo_registro = True
                self.label_titulo.configure(text="Forjar Novo Cofre de Usuário")
                self.btn_login.configure(text="Criar Conta Criptografada", command=self.registrar_usuario, fg_color="#27ae60", hover_color="#2ecc71")
                self.entry_senha_confirma.pack(after=self.entry_senha, pady=(0, 10), padx=20, fill="x")
                self.btn_register.configure(text="Voltar ao Cofre (Login)")
            else:
                self.modo_registro = False
                self.label_titulo.configure(text="Cofre Criptográfico (MFA)")
                self.btn_login.configure(text="Descriptografar (Autenticar)", command=self.tentar_login, fg_color=["#3B8ED0", "#1F6AA5"], hover_color=["#36719F", "#144870"])
                self.entry_senha_confirma.pack_forget()
                self.btn_register.configure(text="Registrar Nova Conta")
            
            self.label_status.configure(text="")
            if hasattr(self, 'frame_emergencia'):
                self.frame_emergencia.pack_forget()

        self.btn_register = ctk.CTkButton(self.frame_login, text="Registrar Nova Conta", fg_color="transparent", border_width=1, command=alternar_modo_auth)
        self.btn_register.pack(pady=(0, 10), padx=20, fill="x")

        self.label_status = ctk.CTkLabel(self.frame_login, text="", text_color="red", justify="center")
        self.label_status.pack(pady=(0, 5))

        self.frame_emergencia = ctk.CTkFrame(self.frame_login, fg_color="transparent")
        
        self.btn_toggle_emergencia = ctk.CTkButton(self.frame_emergencia, text="Chave de Emergência ▼", fg_color="#c0392b", hover_color="#e74c3c")
        self.btn_toggle_emergencia.pack(pady=5)
        
        self.entry_chave_emergencia = ctk.CTkEntry(self.frame_emergencia, font=ctk.CTkFont(family="Courier", size=11), justify="center")

        def alternar_chave():
            if self.entry_chave_emergencia.winfo_ismapped():
                self.entry_chave_emergencia.pack_forget()
                self.btn_toggle_emergencia.configure(text="Chave de Emergência ▼")
            else:
                self.entry_chave_emergencia.pack(pady=5, padx=20, fill="x")
                self.btn_toggle_emergencia.configure(text="Chave de Emergência ▲")
        
        self.btn_toggle_emergencia.configure(command=alternar_chave)

    def incrementar_falha_e_verificar_destruicao(self, usuario):
        self.tentativas_falhas += 1
        db_path = f"vault_{usuario.lower()}.db"
        shadow_path = f"shadow_{usuario.lower()}.json"
        
        if self.tentativas_falhas == 3:
            self.modo_lockdown = True
            self.label_status.configure(text="[LOCKDOWN] 3 Falhas.\nInsira a Chave de Emergência offline.", text_color="orange")
            self.entry_senha.delete(0, 'end')
            self.entry_senha.configure(placeholder_text="Chave de Emergência", show="")
            self.btn_login.configure(text="Validar Override", fg_color="#c0392b", hover_color="#e74c3c")
            
        elif self.tentativas_falhas >= 5:
            if self.db_conn: 
                self.db_conn.close()
            if os.path.exists(db_path): 
                os.remove(db_path)
            if os.path.exists(shadow_path): 
                os.remove(shadow_path)
            self.label_status.configure(text=f"[EXPURGO] Conta '{usuario}' vaporizada.", text_color="red")
            self.btn_login.configure(state="disabled")
        else:
            self.label_status.configure(text=f"Acesso Negado (Senha ou Hardware). Falhas: {self.tentativas_falhas}/5", text_color="red")

    def tentar_login(self):
        usuario = self.entry_usuario.get()
        if not usuario:
            self.label_status.configure(text="Erro: ID do Usuário obrigatório.", text_color="red")
            return

        db_path = f"vault_{usuario.lower()}.db"

        if self.modo_lockdown:
            chave_emergencia = self.entry_senha.get()
            if validar_chave_emergencia(usuario, chave_emergencia):
                self.modo_lockdown = False
                self.tentativas_falhas = 0
                self.label_status.configure(text="[OVERRIDE] Status verde. Tente a Senha novamente.", text_color="green")
                self.entry_senha.delete(0, 'end')
                self.entry_senha.configure(placeholder_text="Senha (Master Key)", show="*")
                self.btn_login.configure(text="Descriptografar (Autenticar)", fg_color=["#3B8ED0", "#1F6AA5"])
            else:
                self.incrementar_falha_e_verificar_destruicao(usuario)
            return

        senha_digitada = self.entry_senha.get()
        if not os.path.exists(db_path):
            self.label_status.configure(text="Erro: Cofre não encontrado. Registre-se.", text_color="orange")
            return

        try:
            chave_hex, salt_mfa = derivar_chave_db(usuario, senha_digitada)
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            cursor.execute(f"PRAGMA key=\"x'{chave_hex}'\"")
            cursor.execute("SELECT count(*) FROM sqlite_master;") 
            cursor.fetchone()
            cursor.execute("PRAGMA foreign_keys = ON;")
            
            # --- AUTO-HEALING: Garantia de Integridade Relacional ---
            try:
                cursor.execute("INSERT OR IGNORE INTO tb_categorias (id, nome, tipo_fluxo) VALUES (1, 'Receitas Gerais', 'RECEITA')")
                cursor.execute("INSERT OR IGNORE INTO tb_categorias (id, nome, tipo_fluxo) VALUES (4, 'Despesas Gerais', 'DESPESA')")
                cursor.execute("INSERT OR IGNORE INTO tb_categorias (id, nome, tipo_fluxo) VALUES (5, 'Investimentos', 'DESPESA')")
                
                # Injeção da Tabela de Orçamentos a quente
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS tb_orcamentos (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        categoria_id INTEGER NOT NULL UNIQUE,
                        limite_mensal REAL NOT NULL,
                        FOREIGN KEY (categoria_id) REFERENCES tb_categorias(id) ON DELETE CASCADE
                    )
                ''')
                conn.commit()
            except Exception as e_db:
                print(f"Erro no Auto-Healing: {e_db}")
            # --------------------------------------------------------
            
            self.tentativas_falhas = 0
            self.db_conn = conn
            self.usuario_atual = usuario
            self.db_path_atual = db_path
            self.after(1, self.carregar_dashboard)

        except sqlite3.DatabaseError:
            self.incrementar_falha_e_verificar_destruicao(usuario)

    def registrar_usuario(self):
        usuario = self.entry_usuario.get()
        if not usuario:
            self.label_status.configure(text="Erro: Forneça um ID de Usuário.", text_color="red")
            return

        db_path = f"vault_{usuario.lower()}.db"
        if os.path.exists(db_path):
            self.label_status.configure(text="Erro: Este usuário já possui um cofre.", text_color="red")
            return
            
        senha_nova = self.entry_senha.get()
        if len(senha_nova) < 6 or senha_nova != self.entry_senha_confirma.get():
            self.label_status.configure(text="Erro: Senha inválida ou divergente.", text_color="red")
            return
            
        try:
            # Geração das assinaturas criptográficas
            chave_emergencia = gerar_chave_emergencia(usuario)
            chave_hex, salt_mfa = derivar_chave_db(usuario, senha_nova)
            
            # Criação do banco físico
            self.inicializar_banco_relacional(db_path, chave_hex)
            
            self.label_status.configure(text="Cofre forjado! Guarde a Chave e faça Login.", text_color="green")
            self.entry_senha.delete(0, 'end')
            self.entry_senha_confirma.delete(0, 'end')
            
            # --- ACORDEÃO DA CHAVE DE EMERGÊNCIA ---
            if hasattr(self, 'frame_emergencia'): self.frame_emergencia.destroy()
            self.frame_emergencia = ctk.CTkFrame(self.frame_login, fg_color="transparent")
            self.frame_emergencia.pack(pady=10, fill="x")
            
            self.btn_mostrar_chave = ctk.CTkButton(self.frame_emergencia, text="Chave de Emergência ▼", fg_color="#c0392b", hover_color="#e74c3c")
            self.btn_mostrar_chave.pack()
            
            # Campo de texto readonly para facilitar a cópia
            self.txt_chave = ctk.CTkTextbox(self.frame_emergencia, height=60, font=ctk.CTkFont(family="Courier", size=12))
            self.txt_chave.insert("0.0", chave_emergencia)
            self.txt_chave.configure(state="disabled") # Impede edição, permite cópia
            
            def toggle_chave():
                if self.txt_chave.winfo_ismapped():
                    self.txt_chave.pack_forget()
                    self.btn_mostrar_chave.configure(text="Chave de Emergência ▼")
                else:
                    self.txt_chave.pack(pady=10, padx=20, fill="x")
                    self.btn_mostrar_chave.configure(text="Ocultar Chave ▲")
                    
            self.btn_mostrar_chave.configure(command=toggle_chave)
            # ----------------------------------------
        except Exception as e:
            self.label_status.configure(text=f"Erro crítico: {e}", text_color="red")

    def carregar_dashboard(self):
        self.frame_login.destroy()
        self.geometry("1100x750")
        self.resizable(True, True)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0, fg_color=COR_CARD)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(7, weight=1) 

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text=f"Wealth.Core\n[{self.usuario_atual}]", font=ctk.CTkFont(size=18, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 30))

        self.btn_nav_dash = ctk.CTkButton(self.sidebar_frame, text="Visão Geral", command=lambda: self.rotear_tela("dash"), fg_color="transparent", border_width=1, border_color=COR_BORDAS)
        self.btn_nav_dash.grid(row=1, column=0, padx=20, pady=10)

        self.btn_nav_lancamentos = ctk.CTkButton(self.sidebar_frame, text="Lançamentos (I/O)", command=lambda: self.rotear_tela("lancamentos"), fg_color="transparent", border_width=1, border_color=COR_BORDAS)
        self.btn_nav_lancamentos.grid(row=2, column=0, padx=20, pady=10)

        self.btn_nav_orcamento = ctk.CTkButton(self.sidebar_frame, text="Orçamentos", command=lambda: self.rotear_tela("orcamento"), fg_color="transparent", border_width=1, border_color=COR_BORDAS)
        self.btn_nav_orcamento.grid(row=3, column=0, padx=20, pady=10)

        def toggle_privacidade():
            self.modo_privacidade = not self.modo_privacidade
            txt = "👁‍🗨 Revelar Valores" if self.modo_privacidade else "🕶 Ocultar Valores"
            self.btn_privacidade.configure(text=txt)
            self.rotear_tela(self.tela_atual) 

        self.btn_privacidade = ctk.CTkButton(self.sidebar_frame, text="🕶 Ocultar Valores", fg_color="#333333", command=toggle_privacidade)
        self.btn_privacidade.grid(row=8, column=0, padx=20, pady=20, sticky="s")

        self.main_frame = ctk.CTkFrame(self, corner_radius=0, fg_color=COR_FUNDO)
        self.main_frame.grid(row=0, column=1, padx=0, pady=0, sticky="nsew")
        
        self.rotear_tela("dash")

    def rotear_tela(self, tela_destino, kwargs=None):
        self.tela_atual = tela_destino 
        
        # Correção PEP 8: Loops expandidos
        for widget in self.main_frame.winfo_children():
            widget.destroy()

        cor_receita_dinamica, cor_despesa_dinamica = self.calcular_cores_dinamicas()
            
        if tela_destino == "dash":
            titulo = ctk.CTkLabel(self.main_frame, text="Visão Geral Financeira", font=ctk.CTkFont(size=24, weight="bold", family="Courier"))
            titulo.pack(pady=20, padx=20, anchor="w")
            
            try:
                cursor = self.db_conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM tb_contas")
                total_contas = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*), SUM(valor) FROM tb_transacoes")
                stats_transacoes = cursor.fetchone()
            except Exception as e_dash:
                ctk.CTkLabel(self.main_frame, text=f"Erro de Banco de Dados: {e_dash}", text_color="red").pack()
                return

            painel_cards = ctk.CTkFrame(self.main_frame, fg_color="transparent")
            painel_cards.pack(fill="x", padx=20, pady=10)
            painel_cards.grid_columnconfigure((0, 1), weight=1)

            # CARD: GESTÃO DE CONTAS
            card_contas = ctk.CTkFrame(painel_cards, corner_radius=5, fg_color=COR_CARD, border_width=1, border_color=COR_BORDAS, cursor="hand2")
            card_contas.grid(row=0, column=0, padx=10, sticky="nsew")
            
            lbl_tit_contas = ctk.CTkLabel(card_contas, text="GESTÃO DE CONTAS BANCÁRIAS", font=ctk.CTkFont(family="Courier", size=14, weight="bold"), text_color=COR_BORDAS)
            lbl_tit_contas.pack(pady=15)
            
            if total_contas > 0:
                ctk.CTkLabel(card_contas, text=f"Contas Ativas: {total_contas}", text_color=COR_TEXTO).pack(pady=5)
                ctk.CTkLabel(card_contas, text="[ Clique para Gerenciar ]", text_color="#2980b9", font=ctk.CTkFont(size=10)).pack(pady=5)
            else:
                ctk.CTkLabel(card_contas, text="Nenhuma instituição cadastrada.", text_color=COR_TEXTO).pack(pady=10)
            
            self.ligar_clique_recursivo(card_contas, lambda e: self.rotear_tela("detalhes_contas"))

            # CARD: MÉTRICAS DE INGESTÃO
            card_extrato = ctk.CTkFrame(painel_cards, corner_radius=5, cursor="hand2", fg_color=COR_CARD, border_width=1, border_color=COR_BORDAS)
            card_extrato.grid(row=0, column=1, padx=10, sticky="nsew")
            
            lbl_title = ctk.CTkLabel(card_extrato, text="MÉTRICAS DE INGESTÃO (DADOS)", font=ctk.CTkFont(family="Courier", size=14, weight="bold"), text_color=COR_BORDAS)
            lbl_title.pack(pady=15)
            
            qtd_transacoes = stats_transacoes[0] if stats_transacoes else 0
            volume_movimentado = stats_transacoes[1] if stats_transacoes and stats_transacoes[1] else 0.0
            vol_str = "****" if self.modo_privacidade else f"R$ {volume_movimentado:,.2f}"
            
            ctk.CTkLabel(card_extrato, text=f"Registros Processados: {qtd_transacoes}", text_color=COR_TEXTO).pack(pady=5)
            ctk.CTkLabel(card_extrato, text=f"Volume Movimentado: {vol_str}", text_color=COR_TEXTO).pack(pady=5)
            ctk.CTkLabel(card_extrato, text="[ Clique para Histórico Detalhado ]", text_color="#2980b9", font=ctk.CTkFont(size=10)).pack(pady=5)
            
            self.ligar_clique_recursivo(card_extrato, lambda e: self.rotear_tela("historico_dados"))

            # --- GRÁFICO PLACEHOLDER E RENDERIZAÇÃO ---
            self.frame_grafico = ctk.CTkFrame(self.main_frame, fg_color=COR_CARD, corner_radius=5, border_width=1, border_color=COR_BORDAS)
            self.frame_grafico.pack(pady=20, padx=30, fill="x")
            
            lbl_placeholder = ctk.CTkLabel(self.frame_grafico, text="Renderizando Projeção Gráfica...", text_color=COR_TEXTO, font=ctk.CTkFont(family="Courier"))
            lbl_placeholder.pack(pady=40)

            if not self.modo_privacidade:
                try:
                    cursor_grafico = self.db_conn.cursor()
                    cursor_grafico.execute("SELECT c.tipo_fluxo, SUM(t.valor) as total FROM tb_transacoes t JOIN tb_categorias c ON t.categoria_id = c.id GROUP BY c.tipo_fluxo")
                    dados_bd = cursor_grafico.fetchall()
                    colunas = [desc[0] for desc in cursor_grafico.description]
                    df_grafico = pd.DataFrame(dados_bd, columns=colunas)

                    if not df_grafico.empty:
                        fig = px.bar(
                            df_grafico, 
                            x='tipo_fluxo', 
                            y='total', 
                            color='tipo_fluxo', 
                            color_discrete_map={'RECEITA': cor_receita_dinamica, 'DESPESA': cor_despesa_dinamica}, 
                            text_auto='.2s'
                        )
                        fig.update_layout(
                            xaxis_title=None, 
                            yaxis_title=None, 
                            showlegend=False, 
                            margin=dict(l=0, r=0, t=20, b=0), 
                            paper_bgcolor="rgba(0,0,0,0)", 
                            plot_bgcolor="rgba(10, 17, 40, 0.5)", 
                            height=300,
                            font=dict(family="Courier", color=COR_TEXTO)
                        )
                        fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='#1E2D5A', tickfont=dict(size=12, color=COR_BORDAS))
                        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='#1E2D5A', visible=True, tickfont=dict(color=COR_TEXTO))
                        
                        img_bytes = fig.to_image(format="png", width=600, height=300)
                        imagem_pil = Image.open(io.BytesIO(img_bytes))
                        
                        lbl_placeholder.destroy() # Remove placeholder
                        ctk.CTkLabel(self.frame_grafico, image=ctk.CTkImage(light_image=imagem_pil, dark_image=imagem_pil, size=(600, 300)), text="").pack(pady=10)
                    else:
                        lbl_placeholder.configure(text="Área de Projeção Gráfica (Aguardando Dados)")
                except Exception as err_grafico: 
                    lbl_placeholder.configure(text=f"Erro de Plotagem: {err_grafico}", text_color="red")
            else:
                lbl_placeholder.configure(text="Telemetria Ocultada (Modo de Privacidade Ativo)")

        elif tela_destino == "detalhes_contas":
            ctk.CTkButton(self.main_frame, text="← Retornar à Visão Geral", fg_color="transparent", command=lambda: self.rotear_tela("dash")).pack(pady=(20, 0), padx=20, anchor="w")
            ctk.CTkLabel(self.main_frame, text="Gestão de Contas Bancárias", font=ctk.CTkFont(size=24, weight="bold", family="Courier")).pack(pady=20, padx=20, anchor="w")

            frame_split = ctk.CTkFrame(self.main_frame, fg_color="transparent")
            frame_split.pack(fill="both", expand=True, padx=20)
            frame_split.grid_columnconfigure(0, weight=1)
            frame_split.grid_columnconfigure(1, weight=1)

            frame_lista = ctk.CTkFrame(frame_split, fg_color=COR_CARD, corner_radius=5, border_width=1, border_color=COR_BORDAS)
            frame_lista.grid(row=0, column=0, sticky="nsew", padx=(0,10))
            
            ctk.CTkLabel(frame_lista, text="Contas Ativas (Duplo Clique para Isolar)", font=ctk.CTkFont(family="Courier", weight="bold")).pack(pady=10)

            # Correção: Adicionada coluna Saldo
            tree_contas = ttk.Treeview(frame_lista, columns=('ID', 'Nome', 'Tipo', 'Saldo'), show='headings', height=8)
            tree_contas.heading('ID', text='ID')
            tree_contas.heading('Nome', text='Instituição')
            tree_contas.heading('Tipo', text='Tipo')
            tree_contas.heading('Saldo', text='Saldo (R$)')
            
            tree_contas.column('ID', width=30)
            tree_contas.column('Nome', width=120)
            tree_contas.column('Tipo', width=90)
            tree_contas.column('Saldo', width=100, anchor='e')
            tree_contas.pack(fill="both", expand=True, padx=10, pady=10)

            # --- DRILL-DOWN: REABILITAR DUPLO CLIQUE ---
            def on_double_click(event):
                item = tree_contas.selection()
                if item:
                    item_data = tree_contas.item(item[0])
                    id_banco = item_data['values'][0]
                    nome_banco = item_data['values'][1]
                    self.rotear_tela("detalhes_banco_especifico", kwargs={'id': id_banco, 'nome': nome_banco})
            
            tree_contas.bind("<Double-1>", on_double_click)

            try:
                cursor = self.db_conn.cursor()
                # Query com cálculo de saldo (Receita - Despesa)
                cursor.execute("""
                    SELECT 
                        c.id, 
                        c.nome, 
                        c.tipo, 
                        COALESCE(SUM(CASE WHEN cat.tipo_fluxo = 'RECEITA' THEN t.valor ELSE -t.valor END), 0) as saldo
                    FROM tb_contas c
                    LEFT JOIN tb_transacoes t ON c.id = t.conta_id
                    LEFT JOIN tb_categorias cat ON t.categoria_id = cat.id
                    GROUP BY c.id
                """)
                for row in cursor.fetchall():
                    # Formatação monetária na Treeview
                    linha_formatada = (row[0], row[1], row[2], f"{row[3]:.2f}")
                    tree_contas.insert('', 'end', values=linha_formatada)
            except Exception as e_tree: 
                print(f"Erro ao carregar lista de contas: {e_tree}")

            frame_cad = ctk.CTkFrame(frame_split, fg_color=COR_CARD, corner_radius=5, border_width=1, border_color=COR_BORDAS)
            frame_cad.grid(row=0, column=1, sticky="nsew", padx=(10,0))
            ctk.CTkLabel(frame_cad, text="Vincular Nova Instituição", font=ctk.CTkFont(family="Courier", weight="bold")).pack(pady=10)

            entry_nome_conta = ctk.CTkEntry(frame_cad, width=200, placeholder_text="Nome do Banco (Ex: Itaú)")
            entry_nome_conta.pack(padx=20, pady=(0, 10))
            combo_tipo_conta = ctk.CTkOptionMenu(frame_cad, values=["CORRENTE", "POUPANCA", "INVESTIMENTO"], fg_color="#333333")
            combo_tipo_conta.pack(padx=20, pady=(0, 10))

            def salvar_conta():
                if not entry_nome_conta.get(): 
                    return
                try:
                    cursor = self.db_conn.cursor()
                    cursor.execute("INSERT INTO tb_contas (nome, tipo, saldo_inicial) VALUES (?, ?, 0.0)", (entry_nome_conta.get(), combo_tipo_conta.get()))
                    self.db_conn.commit()
                    self.rotear_tela("detalhes_contas") 
                except Exception as e_save_acc:
                    print(e_save_acc)

            ctk.CTkButton(frame_cad, text="Gravar Nova Conta", fg_color="#2980b9", command=salvar_conta).pack(pady=20, padx=20)

        elif tela_destino == "lancamentos":
            ctk.CTkButton(self.main_frame, text="← Retornar à Visão Geral", fg_color="transparent", command=lambda: self.rotear_tela("dash")).pack(pady=(20, 0), padx=20, anchor="w")
            ctk.CTkLabel(self.main_frame, text="Módulo de Inserção de Dados (I/O)", font=ctk.CTkFont(size=24, weight="bold", family="Courier")).pack(pady=10, padx=20, anchor="w")

            try:
                cursor = self.db_conn.cursor()
                cursor.execute("SELECT id, nome FROM tb_contas")
                contas_disponiveis = cursor.fetchall()
                mapa_contas = {f"{nome} (ID: {id_c})": id_c for id_c, nome in contas_disponiveis}
                lista_nomes_contas = list(mapa_contas.keys()) if mapa_contas else ["Nenhuma conta cadastrada"]
            except Exception:
                lista_nomes_contas = ["Erro ao carregar contas"]
                mapa_contas = {}

            frame_manual = ctk.CTkFrame(self.main_frame, corner_radius=5, fg_color=COR_CARD, border_width=1, border_color=COR_BORDAS)
            frame_manual.pack(fill="x", padx=20, pady=10)
            
            ctk.CTkLabel(frame_manual, text="[ ENTRADA MANUAL DE REGISTROS ]", font=ctk.CTkFont(family="Courier", weight="bold"), text_color=COR_BORDAS).grid(row=0, column=0, columnspan=2, pady=10)

            combo_conta_alvo = ctk.CTkOptionMenu(frame_manual, values=lista_nomes_contas, fg_color="#333333", width=200)
            combo_conta_alvo.grid(row=1, column=0, padx=10, pady=10)
            
            # --- MÁSCARA ESTREITA DE DATA (DD/MM/YYYY) (AppSec Reabilitada) ---
            self.var_data = ctk.StringVar()
            def mascara_data(*args):
                texto_bruto = self.var_data.get()
                texto_limpo = ''.join(filter(str.isdigit, texto_bruto))
                if len(texto_limpo) > 8: 
                    texto_limpo = texto_limpo[:8]
                
                texto_formatado = ""
                for i, digito in enumerate(texto_limpo):
                    if i in [2, 4]: 
                        texto_formatado += "/"
                    texto_formatado += digito
                
                if texto_bruto != texto_formatado:
                    self.var_data.set(texto_formatado)

            self.var_data.trace_add("write", mascara_data)
            
            entry_data = ctk.CTkEntry(frame_manual, textvariable=self.var_data, placeholder_text="Data (DD/MM/YYYY)")
            entry_data.grid(row=1, column=1, padx=10, pady=10)
            
            entry_desc = ctk.CTkEntry(frame_manual, placeholder_text="Descrição (Ex: Supermercado)", width=200)
            entry_desc.grid(row=2, column=0, padx=10, pady=10)
            
            # --- MÁSCARA ESTREITA DE VALOR (Numérico + Ponto) ---
            self.var_valor = ctk.StringVar()
            def mascara_valor(*args):
                texto = self.var_valor.get()
                valido = ''.join(c for c in texto if c.isdigit() or c == '.')
                if valido.count('.') > 1: 
                    valido = valido[:-1]
                if texto != valido: 
                    self.var_valor.set(valido)

            self.var_valor.trace_add("write", mascara_valor)

            entry_valor = ctk.CTkEntry(frame_manual, textvariable=self.var_valor, placeholder_text="Valor Bruto (R$)")
            entry_valor.grid(row=2, column=1, padx=10, pady=10)
            
            # Simplificação exigida: Apenas 3 opções de movimentação
            combo_tipo = ctk.CTkOptionMenu(frame_manual, values=["Despesa", "Recebimento", "Investimento"], fg_color="#333333", width=200)
            combo_tipo.grid(row=3, column=0, padx=10, pady=10)

            lbl_feedback_io = ctk.CTkLabel(frame_manual, text="")
            lbl_feedback_io.grid(row=4, column=0, columnspan=2, pady=5)

            def salvar_manual():
                try:
                    if not mapa_contas: 
                        raise ValueError("Cadastre uma instituição bancária primeiro.")
                    
                    data_digitada = entry_data.get()
                    if len(data_digitada) != 10: 
                        raise ValueError("Preencha a data no formato completo (DD/MM/YYYY).")
                    
                    try:
                        # Validação Gregorian estrita no backend
                        data_obj = datetime.strptime(data_digitada, '%d/%m/%Y')
                        d_iso = data_obj.strftime('%Y-%m-%d')
                    except ValueError:
                        raise ValueError("Data informada não existe no calendário.")

                    valor_string = entry_valor.get()
                    if not valor_string:
                        raise ValueError("O valor da transação é obrigatório.")
                    v = float(valor_string)
                    
                    desc = entry_desc.get()
                    if not desc: 
                        raise ValueError("A descrição não pode ficar em branco.")
                    
                    # Mapeamento do Dropdown para os IDs da tb_categorias
                    tipo_selecionado = combo_tipo.get()
                    if tipo_selecionado == "Recebimento":
                        cat_id = 1
                    elif tipo_selecionado == "Despesa":
                        cat_id = 4
                    elif tipo_selecionado == "Investimento":
                        cat_id = 5
                    else:
                        cat_id = 4 # Fallback
                    
                    cursor = self.db_conn.cursor()
                    cursor.execute(
                        "INSERT INTO tb_transacoes (conta_id, categoria_id, valor, data_transacao, descricao) VALUES (?, ?, ?, ?, ?)", 
                        (mapa_contas[combo_conta_alvo.get()], cat_id, abs(v), d_iso, desc)
                    )
                    self.db_conn.commit()
                    
                    self.var_data.set("")
                    self.var_valor.set("")
                    entry_desc.delete(0, 'end')
                    lbl_feedback_io.configure(text="[+] Transação registrada com sucesso no Cofre.", text_color=COR_RECEITA)
                except Exception as e_save: 
                    lbl_feedback_io.configure(text=f"[X] {e_save}", text_color=COR_DESPESA)

            ctk.CTkButton(frame_manual, text="Gravar Registro no Cofre", fg_color="#27ae60", hover_color="#2ecc71", command=salvar_manual).grid(row=3, column=1, pady=15)

            # --- MÓDULO I/O BATCH (CSV) ---
            frame_csv = ctk.CTkFrame(self.main_frame, corner_radius=5, fg_color=COR_CARD, border_width=1, border_color=COR_BORDAS)
            frame_csv.pack(fill="x", padx=20, pady=10)
            ctk.CTkLabel(frame_csv, text="[ INGESTÃO MASSIVA DE LOTE (.CSV) ]", font=ctk.CTkFont(family="Courier", weight="bold"), text_color=COR_BORDAS).pack(pady=10)
            
            ctk.CTkLabel(frame_csv, text="Selecione a conta destino para os dados:").pack()
            combo_conta_csv = ctk.CTkOptionMenu(frame_csv, values=lista_nomes_contas, fg_color="#333333", width=200)
            combo_conta_csv.pack(pady=5)

            def importar_csv_interno():
                caminho = filedialog.askopenfilename(filetypes=[("Arquivos CSV", "*.csv")])
                if not caminho: 
                    return
                try:
                    if not mapa_contas: 
                        raise ValueError("Cadastre uma conta antes de importar lotes.")
                    id_conta_alvo = mapa_contas[combo_conta_csv.get()]

                    df = pd.read_csv(caminho, header=0, names=['Data', 'Descricao', 'Valor'])
                    df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, format='mixed').dt.strftime('%Y-%m-%d')
                    registros = []
                    for _, row in df.iterrows():
                        v = float(row['Valor'])
                        cat = 1 if v > 0 else 4
                        registros.append((id_conta_alvo, cat, abs(v), row['Data'], row['Descricao']))
                    
                    cursor = self.db_conn.cursor()
                    cursor.executemany("INSERT INTO tb_transacoes (conta_id, categoria_id, valor, data_transacao, descricao) VALUES (?, ?, ?, ?, ?)", registros)
                    self.db_conn.commit()
                    self.rotear_tela("dash") 
                except Exception as e_csv:
                    ctk.CTkLabel(frame_csv, text=f"[X] Falha no Processamento: {e_csv}", text_color=COR_DESPESA).pack(pady=5)

            ctk.CTkButton(frame_csv, text="Carregar Arquivo .CSV", fg_color="#2980b9", command=importar_csv_interno).pack(pady=10)

        # --- NOVA ROTA: BANCO ISOLADO (Reabilitado) ---
        elif tela_destino == "detalhes_banco_especifico":
            kwargs = kwargs or {}
            id_banco = kwargs.get('id')
            nome_banco = kwargs.get('nome')

            ctk.CTkButton(self.main_frame, text="← Retornar à Lista de Contas", fg_color="transparent", command=lambda: self.rotear_tela("detalhes_contas")).pack(pady=(20, 0), padx=20, anchor="w")
            ctk.CTkLabel(self.main_frame, text=f"Inspeção Isolada: Instituição [{nome_banco}]", font=ctk.CTkFont(size=20, weight="bold", family="Courier"), text_color=COR_BORDAS).pack(pady=10, padx=20, anchor="w")

            frame_filtro = ctk.CTkFrame(self.main_frame, fg_color="transparent")
            frame_filtro.pack(fill="x", padx=20, pady=10)
            ctk.CTkLabel(frame_filtro, text="Janela de Tempo da Telemetria:").pack(side="left", padx=(0, 10))
            combo_tempo = ctk.CTkOptionMenu(frame_filtro, values=["1 Mês", "3 Meses", "6 Meses", "1 Ano"], fg_color="#333333")
            combo_tempo.pack(side="left")

            frame_kpi = ctk.CTkFrame(self.main_frame, fg_color=COR_CARD, corner_radius=5, border_width=1, border_color=COR_BORDAS)
            frame_kpi.pack(fill="x", padx=20, pady=10)

            def atualizar_kpi_banco(*args):
                meses = int(combo_tempo.get().split()[0])
                data_corte = (datetime.now() - timedelta(days=30*meses)).strftime('%Y-%m-%d')
                
                for widget in frame_kpi.winfo_children(): 
                    widget.destroy()

                try:
                    cursor = self.db_conn.cursor()
                    cursor.execute("""
                        SELECT c.tipo_fluxo, SUM(t.valor) 
                        FROM tb_transacoes t 
                        JOIN tb_categorias c ON t.categoria_id = c.id
                        WHERE t.conta_id = ? AND t.data_transacao >= ?
                        GROUP BY c.tipo_fluxo
                    """, (id_banco, data_corte))
                    fluxos = dict(cursor.fetchall())
                    rec = fluxos.get('RECEITA', 0)
                    desp = fluxos.get('DESPESA', 0)

                    val_rec = "****" if self.modo_privacidade else f"R$ {rec:,.2f}"
                    val_desp = "****" if self.modo_privacidade else f"R$ {desp:,.2f}"

                    ctk.CTkLabel(frame_kpi, text=f"Entradas Acumuladas:\n{val_rec}", font=ctk.CTkFont(weight="bold"), text_color=COR_RECEITA).pack(side="left", expand=True, pady=20)
                    ctk.CTkLabel(frame_kpi, text=f"Saídas Acumuladas:\n{val_desp}", font=ctk.CTkFont(weight="bold"), text_color=COR_DESPESA).pack(side="left", expand=True, pady=20)
                except Exception as e_kpi: 
                    ctk.CTkLabel(frame_kpi, text=f"Erro de compilação: {e_kpi}", text_color="red").pack()

            atualizar_kpi_banco()
            combo_tempo.configure(command=atualizar_kpi_banco)

        elif tela_destino == "historico_dados":
            ctk.CTkButton(self.main_frame, text="← Retornar à Visão Geral", fg_color="transparent", command=lambda: self.rotear_tela("dash")).pack(pady=(20, 0), padx=20, anchor="w")
            ctk.CTkLabel(self.main_frame, text="Livro-Razão (Histórico Massivo)", font=ctk.CTkFont(size=24, weight="bold", family="Courier")).pack(pady=10, padx=20, anchor="w")

            frame_tabela = ctk.CTkFrame(self.main_frame, fg_color=COR_CARD, border_width=1, border_color=COR_BORDAS)
            frame_tabela.pack(fill="both", expand=True, padx=20, pady=10)
            
            # Correção: Adicionada coluna 'Banco' e alterada cor para Ciano Neon (#00FFFF)
            tree = ttk.Treeview(frame_tabela, columns=('Data', 'Descricao', 'Natureza', 'Valor', 'Banco'), show='headings')
            tree.heading('Data', text='Data')
            tree.heading('Descricao', text='Descrição')
            tree.heading('Natureza', text='Fluxo')
            tree.heading('Valor', text='Valor (R$)')
            tree.heading('Banco', text='Banco')
            
            tree.column('Data', width=100, anchor='center')
            tree.column('Descricao', width=300, anchor='w')
            tree.column('Natureza', width=100, anchor='center')
            tree.column('Valor', width=120, anchor='e')
            tree.column('Banco', width=120, anchor='w')
            
            # Ciano Neon no conteúdo da tabela
            self.style.configure("Treeview", foreground="#00FFFF")

            scrollbar = ttk.Scrollbar(frame_tabela, orient="vertical", command=tree.yview)
            tree.configure(yscrollcommand=scrollbar.set)
            scrollbar.pack(side="right", fill="y")
            tree.pack(fill="both", expand=True, padx=2, pady=2)

            try:
                cursor = self.db_conn.cursor()
                cursor.execute("""
                    SELECT t.data_transacao, t.descricao, c.tipo_fluxo, t.valor, con.nome
                    FROM tb_transacoes t 
                    JOIN tb_categorias c ON t.categoria_id = c.id 
                    JOIN tb_contas con ON t.conta_id = con.id
                    ORDER BY t.data_transacao DESC
                """)
                for row in cursor.fetchall():
                    val = "****" if self.modo_privacidade else f"R$ {row[3]:.2f}"
                    # row[4] é o nome do banco
                    tree.insert('', 'end', values=(row[0], row[1], row[2], val, row[4]))
            except Exception as err_tree_hist:
                print(f"Erro ao carregar árvore histórica: {err_tree_hist}")

        elif tela_destino == "orcamento":
            ctk.CTkButton(self.main_frame, text="← Retornar à Visão Geral", fg_color="transparent", command=lambda: self.rotear_tela("dash")).pack(pady=(20, 0), padx=20, anchor="w")
            ctk.CTkLabel(self.main_frame, text="Módulo WIP: Planejamento Orçamentário", font=ctk.CTkFont(size=24, weight="bold")).pack(pady=20, padx=20, anchor="w")

if __name__ == "__main__":
    app = PlataformaFinanceira()
    app.mainloop()
