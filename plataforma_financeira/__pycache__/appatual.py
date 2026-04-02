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
from contextlib import contextmanager
from PIL import Image
from tkinter import filedialog, ttk

# --- PALETA DE CORES (Sci-Fi HUD) ---
COR_FUNDO = "#12121A"       
COR_CARD = "#1E1E2C"        
COR_BORDAS = "#2A2A3D"      
COR_TEXTO = "#A0A0B5"       
COR_TEXTO_FORTE = "#FFFFFF" 
COR_PRIMARIA = "#7B61FF"    
COR_RECEITA = "#00FF9D"     
COR_DESPESA = "#FF4757"     
COR_HOVER_LIFT = "#29293D"  
COR_HOVER_BORDA = "#F1C40F" 
COR_ZEBRA_1 = "#1A1A28"     
COR_ZEBRA_2 = "#1E1E2C"
COR_DESTAQUE = "#B026FF"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# =====================================================================
# MÓDULO 1: MOTOR CRIPTOGRÁFICO E MFA
# =====================================================================
def obter_salt_hardware_usuario(usuario):
    mac = uuid.getnode()
    return hashlib.sha256(f"{mac}_{usuario.lower()}".encode()).hexdigest()

def derivar_chave_db(usuario, senha_plana):
    salt = obter_salt_hardware_usuario(usuario)
    chave_hex = hashlib.pbkdf2_hmac('sha512', senha_plana.encode(), salt.encode(), 210000).hex()
    return chave_hex, salt

def gerar_chave_emergencia(usuario):
    chave_plana = secrets.token_hex(32) 
    hash_shadow = hashlib.sha512(chave_plana.encode()).hexdigest()
    with open(f"shadow_{usuario.lower()}.json", 'w') as f:
        json.dump({'recovery_hash': hash_shadow}, f)
    return chave_plana

def validar_chave_emergencia(usuario, input_chave):
    arquivo = f"shadow_{usuario.lower()}.json"
    if not os.path.exists(arquivo): return False
    with open(arquivo, 'r') as f: dados = json.load(f)
    return secrets.compare_digest(hashlib.sha512(input_chave.encode()).hexdigest(), dados.get('recovery_hash', ''))

class PlataformaFinanceira(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Wealth Engine - Command Center")
        self.geometry("600x650")
        self.resizable(False, False)
        self.configure(fg_color=COR_FUNDO)
        
        self.db_conn = None 
        self.usuario_atual = None
        self.db_path_atual = None
        self.modo_privacidade = False 
        self.tela_atual = "dash"      
        self.tentativas_falhas = 0 
        self.modo_lockdown = False

        self.style = ttk.Style()
        self.style.theme_use("default")
        self.style.configure("Treeview", background=COR_CARD, foreground=COR_TEXTO_FORTE, fieldbackground=COR_CARD, borderwidth=0, rowheight=35, font=("Helvetica", 11))
        self.style.map('Treeview', background=[('selected', COR_PRIMARIA)])
        self.style.configure("Treeview.Heading", background=COR_FUNDO, foreground=COR_TEXTO_FORTE, relief="flat", font=('Helvetica', 12, 'bold'))

        self.construir_tela_login()

    # =====================================================================
    # MÓDULO 2: TRANSAÇÕES ACID, WRAPPERS E MICRO-INTERAÇÕES
    # =====================================================================
    @contextmanager
    def transacao_db(self):
        """[NOVO] Engrenagem ACID: Garante Rollback em falhas e previne DB Locks."""
        cursor = self.db_conn.cursor()
        try:
            yield cursor
            self.db_conn.commit()
        except Exception as e:
            self.db_conn.rollback()
            raise e
        finally:
            cursor.close()

    def aplicar_mascara_financeira(self, valor_numerico):
        if self.modo_privacidade: return "R$ ****"
        return f"R$ {float(valor_numerico):,.2f}"

    def aplicar_efeito_hover(self, widget):
        cor_padrao = widget.cget("fg_color")
        borda_padrao = widget.cget("border_color")
        def on_enter(e): widget.configure(fg_color=COR_HOVER_LIFT, border_color=COR_HOVER_BORDA, border_width=2)
        def on_leave(e): widget.configure(fg_color=cor_padrao, border_color=borda_padrao, border_width=1)
        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)
        for child in widget.winfo_children():
            child.bind("<Enter>", on_enter)
            child.bind("<Leave>", on_leave)

    def ligar_clique_recursivo(self, widget, comando):
        widget.bind("<Button-1>", comando)
        for filho in widget.winfo_children():
            self.ligar_clique_recursivo(filho, comando)

    def inicializar_banco_relacional(self, db_path, chave_hex):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA key=\"x'{chave_hex}'\"")
        cursor.execute("PRAGMA foreign_keys = ON;")
        
        cursor.execute("DROP TABLE IF EXISTS tb_orcamentos") 
        
        cursor.executescript('''
            CREATE TABLE IF NOT EXISTS tb_contas (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, tipo TEXT NOT NULL, saldo_inicial REAL DEFAULT 0.0);
            CREATE TABLE IF NOT EXISTS tb_categorias (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL UNIQUE, tipo_fluxo TEXT CHECK(tipo_fluxo IN ('RECEITA', 'DESPESA')) NOT NULL);
            CREATE TABLE IF NOT EXISTS tb_transacoes (id INTEGER PRIMARY KEY AUTOINCREMENT, conta_id INTEGER NOT NULL, categoria_id INTEGER NOT NULL, valor REAL NOT NULL, data_transacao DATE NOT NULL, descricao TEXT, FOREIGN KEY (conta_id) REFERENCES tb_contas(id) ON DELETE RESTRICT, FOREIGN KEY (categoria_id) REFERENCES tb_categorias(id) ON DELETE RESTRICT);
            
            CREATE TABLE tb_orcamentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                nome TEXT NOT NULL, 
                tipo TEXT NOT NULL, 
                data_vencimento DATE NOT NULL,
                valor REAL NOT NULL, 
                mes_referencia TEXT NOT NULL
            );
            
            CREATE TABLE IF NOT EXISTS tb_metas (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, valor_alvo REAL NOT NULL, valor_acumulado REAL DEFAULT 0.0);
        ''')
        cursor.execute("INSERT OR IGNORE INTO tb_categorias (id, nome, tipo_fluxo) VALUES (1, 'Receitas Gerais', 'RECEITA')")
        cursor.execute("INSERT OR IGNORE INTO tb_categorias (id, nome, tipo_fluxo) VALUES (4, 'Despesas Gerais', 'DESPESA')")
        cursor.execute("INSERT OR IGNORE INTO tb_categorias (id, nome, tipo_fluxo) VALUES (5, 'Investimentos', 'DESPESA')")
        conn.commit()
        conn.close()

    # =====================================================================
    # MÓDULO 3: AUTENTICAÇÃO
    # =====================================================================
    def construir_tela_login(self):
        self.frame_login = ctk.CTkFrame(self, fg_color=COR_CARD, corner_radius=20)
        self.frame_login.pack(pady=50, padx=50, fill="both", expand=True)

        self.label_titulo = ctk.CTkLabel(self.frame_login, text="Login do Cofre", font=ctk.CTkFont(size=26, weight="bold"))
        self.label_titulo.pack(pady=(30, 20))

        self.entry_usuario = ctk.CTkEntry(self.frame_login, placeholder_text="ID do Usuário", height=45, corner_radius=10)
        self.entry_usuario.pack(pady=10, padx=40, fill="x")

        self.entry_senha = ctk.CTkEntry(self.frame_login, placeholder_text="Senha Master", show="*", height=45, corner_radius=10)
        self.entry_senha.pack(pady=10, padx=40, fill="x")

        self.entry_senha_confirma = ctk.CTkEntry(self.frame_login, placeholder_text="Confirme a Senha", show="*", height=45, corner_radius=10)

        self.btn_login = ctk.CTkButton(self.frame_login, text="Autenticar", fg_color=COR_PRIMARIA, height=45, corner_radius=10, command=self.tentar_login)
        self.btn_login.pack(pady=20, padx=40, fill="x")

        self.modo_registro = False
        def alternar_modo_auth():
            if not self.modo_registro:
                self.modo_registro = True
                self.label_titulo.configure(text="Forjar Novo Usuário")
                self.btn_login.configure(text="Registrar Conta", command=self.registrar_usuario, fg_color="#27AE60")
                self.entry_senha_confirma.pack(after=self.entry_senha, pady=(0, 10), padx=40, fill="x")
                self.btn_register.configure(text="Já possuo um cofre (Login)")
            else:
                self.modo_registro = False
                self.label_titulo.configure(text="Login do Cofre")
                self.btn_login.configure(text="Autenticar", command=self.tentar_login, fg_color=COR_PRIMARIA)
                self.entry_senha_confirma.pack_forget()
                self.btn_register.configure(text="Criar nova conta")
            
            self.label_status.configure(text="")
            if hasattr(self, 'frame_emergencia'): self.frame_emergencia.pack_forget()

        self.btn_register = ctk.CTkButton(self.frame_login, text="Criar nova conta", fg_color="transparent", text_color=COR_TEXTO, hover_color=COR_FUNDO, command=alternar_modo_auth)
        self.btn_register.pack(pady=(0, 10), padx=40, fill="x")

        self.label_status = ctk.CTkLabel(self.frame_login, text="", text_color=COR_DESPESA)
        self.label_status.pack(pady=(0, 5))

        self.frame_emergencia = ctk.CTkFrame(self.frame_login, fg_color="transparent")
        self.btn_toggle_emergencia = ctk.CTkButton(self.frame_emergencia, text="Chave de Emergência ▼", fg_color="transparent", text_color=COR_DESPESA, hover_color=COR_FUNDO)
        self.btn_toggle_emergencia.pack(pady=5)
        
        self.entry_chave_emergencia = ctk.CTkEntry(self.frame_emergencia, font=ctk.CTkFont(family="Courier", size=11), justify="center", height=35)

        def alternar_chave():
            if self.entry_chave_emergencia.winfo_ismapped():
                self.entry_chave_emergencia.pack_forget()
                self.btn_toggle_emergencia.configure(text="Chave de Emergência ▼")
            else:
                self.entry_chave_emergencia.pack(pady=5, padx=20, fill="x")
                self.btn_toggle_emergencia.configure(text="Ocultar Chave ▲")
        self.btn_toggle_emergencia.configure(command=alternar_chave)

    def incrementar_falha_e_verificar_destruicao(self, usuario):
        self.tentativas_falhas += 1
        if self.tentativas_falhas == 3:
            self.modo_lockdown = True
            self.label_status.configure(text="[LOCKDOWN] Insira a Chave de Emergência.")
            self.entry_senha.delete(0, 'end'); self.entry_senha.configure(placeholder_text="Chave de Emergência", show="")
            self.btn_login.configure(text="Validar Override", fg_color=COR_DESPESA)
        elif self.tentativas_falhas >= 5:
            db_path = f"vault_{usuario.lower()}.db"
            if self.db_conn: self.db_conn.close()
            if os.path.exists(db_path): os.remove(db_path)
            self.label_status.configure(text="[EXPURGO] Conta vaporizada."); self.btn_login.configure(state="disabled")
        else:
            self.label_status.configure(text=f"Acesso Negado. Falhas: {self.tentativas_falhas}/5")

    def tentar_login(self):
        usuario = self.entry_usuario.get()
        if not usuario: return
        db_path = f"vault_{usuario.lower()}.db"

        if self.modo_lockdown:
            chave_emergencia = self.entry_senha.get()
            if validar_chave_emergencia(usuario, chave_emergencia):
                self.modo_lockdown = False; self.tentativas_falhas = 0
                self.label_status.configure(text="[OVERRIDE] Tente a Senha novamente.", text_color=COR_RECEITA)
                self.entry_senha.delete(0, 'end'); self.entry_senha.configure(placeholder_text="Senha Master", show="*")
                self.btn_login.configure(text="Autenticar", fg_color=COR_PRIMARIA)
            else: self.incrementar_falha_e_verificar_destruicao(usuario)
            return

        if not os.path.exists(db_path):
            self.label_status.configure(text="Cofre não encontrado.", text_color="orange"); return

        try:
            chave_hex, _ = derivar_chave_db(usuario, self.entry_senha.get())
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA key=\"x'{chave_hex}'\"")
            cursor.execute("SELECT count(*) FROM sqlite_master;") 
            cursor.execute("PRAGMA foreign_keys = ON;")
            
            try:
                cursor.execute("PRAGMA table_info(tb_orcamentos)")
                colunas = [col[1] for col in cursor.fetchall()]
                if 'categoria_id' in colunas:
                    cursor.execute("DROP TABLE tb_orcamentos")
                    
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS tb_orcamentos (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, 
                        nome TEXT NOT NULL, 
                        tipo TEXT NOT NULL, 
                        data_vencimento DATE NOT NULL,
                        valor REAL NOT NULL, 
                        mes_referencia TEXT NOT NULL
                    )
                ''')
                cursor.execute("CREATE TABLE IF NOT EXISTS tb_metas (id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL, valor_alvo REAL NOT NULL, valor_acumulado REAL DEFAULT 0.0)")
                conn.commit()
            except Exception as e: print(f"Erro Migration: {e}")

            self.tentativas_falhas = 0
            self.db_conn = conn
            self.usuario_atual = usuario
            self.db_path_atual = db_path
            self.after(1, self.carregar_dashboard)
        except sqlite3.DatabaseError: self.incrementar_falha_e_verificar_destruicao(usuario)

    def registrar_usuario(self):
        usuario = self.entry_usuario.get()
        db_path = f"vault_{usuario.lower()}.db"
        senha_nova = self.entry_senha.get()
        if not usuario or os.path.exists(db_path) or len(senha_nova) < 6 or senha_nova != self.entry_senha_confirma.get(): return
            
        try:
            chave_emergencia = gerar_chave_emergencia(usuario)
            chave_hex, _ = derivar_chave_db(usuario, senha_nova)
            self.inicializar_banco_relacional(db_path, chave_hex)
            
            self.label_status.configure(text=f"Conta '{usuario}' forjada.", text_color=COR_RECEITA)
            self.entry_chave_emergencia.configure(state="normal")
            self.entry_chave_emergencia.delete(0, 'end')
            self.entry_chave_emergencia.insert(0, chave_emergencia)
            self.entry_chave_emergencia.configure(state="readonly")
            
            self.frame_emergencia.pack(fill="x", pady=5)
            self.entry_chave_emergencia.pack_forget() 
            self.btn_toggle_emergencia.configure(text="Chave de Emergência ▼")
            self.entry_senha.delete(0, 'end'); self.entry_senha_confirma.delete(0, 'end')
        except Exception as e: self.label_status.configure(text=f"Erro: {e}")

    # =====================================================================
    # MÓDULO 4: ENGINE DE ROTEAMENTO (SPA FRAMEWORK)
    # =====================================================================
    def carregar_dashboard(self):
        self.frame_login.destroy()
        self.geometry("1200x800")
        self.resizable(True, True)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.sidebar_frame = ctk.CTkFrame(self, width=240, corner_radius=0, fg_color=COR_CARD)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(7, weight=1) 

        ctk.CTkLabel(self.sidebar_frame, text=f"Wealth.Core\n[{self.usuario_atual}]", font=ctk.CTkFont(size=22, weight="bold")).grid(row=0, column=0, padx=20, pady=(30, 40))

        def btn_nav(texto, comando):
            return ctk.CTkButton(self.sidebar_frame, text=texto, command=comando, fg_color="transparent", hover_color=COR_FUNDO, anchor="w", font=ctk.CTkFont(size=14), height=45)

        btn_nav("📊 Visão Geral", lambda: self.rotear_tela("dash")).grid(row=1, column=0, padx=15, pady=5, sticky="ew")
        btn_nav("⚡ Lançamentos (I/O)", lambda: self.rotear_tela("lancamentos")).grid(row=2, column=0, padx=15, pady=5, sticky="ew")
        btn_nav("🎯 Planejamento", lambda: self.rotear_tela("planejamento")).grid(row=3, column=0, padx=15, pady=5, sticky="ew")

        if self.usuario_atual.lower() == 'admin':
            btn_sys = btn_nav("🛠️ SysAdmin Console", lambda: self.rotear_tela("sysadmin"))
            btn_sys.configure(text_color=COR_DESPESA)
            btn_sys.grid(row=4, column=0, padx=15, pady=5, sticky="ew")

        def toggle_privacidade():
            self.modo_privacidade = not self.modo_privacidade
            self.btn_privacidade.configure(text="👁‍🗨 Revelar Valores" if self.modo_privacidade else "🕶 Ocultar Valores")
            self.rotear_tela(self.tela_atual, getattr(self, 'kwargs_atual', None)) 

        self.btn_privacidade = ctk.CTkButton(self.sidebar_frame, text="🕶 Ocultar Valores", fg_color=COR_BORDAS, text_color="#000000", hover_color=COR_FUNDO, command=toggle_privacidade, height=45)
        self.btn_privacidade.grid(row=8, column=0, padx=20, pady=20, sticky="sew")

        self.main_frame = ctk.CTkFrame(self, corner_radius=0, fg_color=COR_FUNDO)
        self.main_frame.grid(row=0, column=1, sticky="nsew")
        self.rotear_tela("dash")

    def rotear_tela(self, tela_destino, kwargs=None):
        self.tela_atual = tela_destino 
        self.kwargs_atual = kwargs
        for widget in self.main_frame.winfo_children(): widget.destroy()
            
        # -------------------------------------------------------------
        # ROTA 1: DASHBOARD
        # -------------------------------------------------------------
        if tela_destino == "dash":
            ctk.CTkLabel(self.main_frame, text="Visão Geral", font=ctk.CTkFont(size=30, weight="bold")).pack(pady=(30, 10), padx=40, anchor="w")
            
            try:
                cursor = self.db_conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM tb_contas")
                total_contas = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*), SUM(valor) FROM tb_transacoes")
                stats = cursor.fetchone()
            except: return

            painel_cards = ctk.CTkFrame(self.main_frame, fg_color="transparent")
            painel_cards.pack(fill="x", padx=30, pady=10)
            painel_cards.grid_columnconfigure((0, 1), weight=1)

            card_contas = ctk.CTkFrame(painel_cards, corner_radius=15, fg_color=COR_CARD, border_width=1, border_color=COR_BORDAS, cursor="hand2")
            card_contas.grid(row=0, column=0, padx=10, sticky="nsew", ipadx=10, ipady=15)
            ctk.CTkLabel(card_contas, text="Suas Contas", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w", padx=15)
            ctk.CTkLabel(card_contas, text=f"{total_contas} Instituições Ativas", text_color=COR_TEXTO).pack(anchor="w", padx=15, pady=(5,0))
            self.ligar_clique_recursivo(card_contas, lambda e: self.rotear_tela("detalhes_contas"))
            self.aplicar_efeito_hover(card_contas) 

            card_extrato = ctk.CTkFrame(painel_cards, corner_radius=15, fg_color=COR_CARD, border_width=1, border_color=COR_BORDAS, cursor="hand2")
            card_extrato.grid(row=0, column=1, padx=10, sticky="nsew", ipadx=10, ipady=15)
            ctk.CTkLabel(card_extrato, text="Métricas Globais", font=ctk.CTkFont(size=18, weight="bold")).pack(anchor="w", padx=15)
            vol_str = self.aplicar_mascara_financeira(stats[1] if stats[1] else 0.0)
            ctk.CTkLabel(card_extrato, text=f"Volume Bruto: {vol_str}", text_color=COR_TEXTO).pack(anchor="w", padx=15, pady=(5,0))
            ctk.CTkLabel(card_extrato, text=f"[{self.db_path_atual}]", text_color="#2980b9", font=ctk.CTkFont(size=10)).pack(anchor="w", padx=15, pady=(5,0))
            self.ligar_clique_recursivo(card_extrato, lambda e: self.rotear_tela("historico_dados"))
            self.aplicar_efeito_hover(card_extrato) 

            self.frame_grafico = ctk.CTkFrame(self.main_frame, fg_color=COR_CARD, corner_radius=15, border_width=1, border_color=COR_BORDAS)
            self.frame_grafico.pack(pady=30, padx=40, fill="x")
            
            if not self.modo_privacidade:
                try:
                    cursor.execute("SELECT c.tipo_fluxo, SUM(t.valor) as total FROM tb_transacoes t JOIN tb_categorias c ON t.categoria_id = c.id GROUP BY c.tipo_fluxo")
                    dados_bd = cursor.fetchall()
                    if dados_bd:
                        df = pd.DataFrame(dados_bd, columns=['tipo_fluxo', 'total'])
                        cores = {'RECEITA': COR_RECEITA, 'DESPESA': COR_DESPESA}
                        fig = px.bar(df, x='tipo_fluxo', y='total', color='tipo_fluxo', color_discrete_map=cores, text_auto='.2s')
                        fig.update_layout(xaxis_title=None, yaxis_title=None, showlegend=False, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=300)
                        fig.update_xaxes(showgrid=False, tickfont=dict(size=14, color=COR_TEXTO_FORTE))
                        fig.update_yaxes(visible=False, showgrid=False)
                        img_bytes = fig.to_image(format="png", width=650, height=300)
                        imagem_pil = Image.open(io.BytesIO(img_bytes))
                        ctk.CTkLabel(self.frame_grafico, image=ctk.CTkImage(light_image=imagem_pil, dark_image=imagem_pil, size=(650, 300)), text="").pack(pady=20)
                    else: ctk.CTkLabel(self.frame_grafico, text="Sem dados para plotagem.", text_color=COR_TEXTO).pack(pady=40)
                except: pass
            else: ctk.CTkLabel(self.frame_grafico, text="Gráficos desativados em Modo Privacidade.", text_color=COR_TEXTO).pack(pady=60)

        # -------------------------------------------------------------
        # ROTA 2: SYSADMIN (DEBUG RAW DB)
        # -------------------------------------------------------------
        elif tela_destino == "sysadmin":
            if self.usuario_atual.lower() != 'admin': return 
            ctk.CTkButton(self.main_frame, text="← Voltar", fg_color="transparent", command=lambda: self.rotear_tela("dash")).pack(pady=(20, 0), padx=30, anchor="w")
            ctk.CTkLabel(self.main_frame, text="Console Forense (SysAdmin)", font=ctk.CTkFont(size=26, weight="bold")).pack(pady=10, padx=40, anchor="w")
            
            frame_query = ctk.CTkFrame(self.main_frame, fg_color=COR_CARD, corner_radius=15, border_width=1, border_color=COR_BORDAS)
            frame_query.pack(fill="x", padx=30, pady=10)
            
            entry_sql = ctk.CTkEntry(frame_query, placeholder_text="SELECT * FROM tb_orcamentos;", height=45, font=ctk.CTkFont(family="Courier", size=14))
            entry_sql.pack(side="left", fill="x", expand=True, padx=(20, 10), pady=15)
            
            lbl_err = ctk.CTkLabel(self.main_frame, text="", text_color=COR_DESPESA)
            lbl_err.pack()
            
            frame_res = ctk.CTkFrame(self.main_frame, fg_color=COR_CARD, corner_radius=15, border_width=1, border_color=COR_BORDAS)
            frame_res.pack(fill="both", expand=True, padx=30, pady=10)
            
            tree_res = ttk.Treeview(frame_res, show='headings')
            scroll_y = ttk.Scrollbar(frame_res, orient="vertical", command=tree_res.yview)
            scroll_x = ttk.Scrollbar(frame_res, orient="horizontal", command=tree_res.xview)
            tree_res.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
            
            scroll_y.pack(side="right", fill="y")
            scroll_x.pack(side="bottom", fill="x")
            tree_res.pack(fill="both", expand=True, padx=5, pady=5)
            
            def run_query():
                q = entry_sql.get()
                if not q: return
                try:
                    c = self.db_conn.cursor()
                    c.execute(q)
                    if q.strip().upper().startswith("SELECT") or q.strip().upper().startswith("PRAGMA"):
                        rows = c.fetchall()
                        cols = [desc[0] for desc in c.description] if c.description else []
                        tree_res.delete(*tree_res.get_children())
                        tree_res["columns"] = cols
                        for col in cols:
                            tree_res.heading(col, text=col)
                            tree_res.column(col, width=120, anchor="w")
                        for r in rows: tree_res.insert('', 'end', values=r)
                        lbl_err.configure(text=f"Query executada. Linhas: {len(rows)}", text_color=COR_RECEITA)
                    else:
                        self.db_conn.commit()
                        lbl_err.configure(text="DML/DDL executado com sucesso.", text_color=COR_RECEITA)
                except Exception as e: lbl_err.configure(text=f"Erro SQL: {e}", text_color=COR_DESPESA)
                    
            ctk.CTkButton(frame_query, text="Executar", fg_color=COR_DESPESA, hover_color="#C0392B", height=45, command=run_query).pack(side="right", padx=(0, 20), pady=15)

        # -------------------------------------------------------------
        # ROTA 3: GESTÃO DE CONTAS (DETALHES)
        # -------------------------------------------------------------
        elif tela_destino == "detalhes_contas":
            ctk.CTkButton(self.main_frame, text="← Voltar", fg_color="transparent", command=lambda: self.rotear_tela("dash")).pack(pady=(20, 0), padx=30, anchor="w")
            ctk.CTkLabel(self.main_frame, text="Gestão de Contas", font=ctk.CTkFont(size=26, weight="bold")).pack(pady=10, padx=40, anchor="w")

            frame_split = ctk.CTkFrame(self.main_frame, fg_color="transparent")
            frame_split.pack(fill="both", expand=True, padx=30)
            frame_split.grid_columnconfigure(0, weight=1); frame_split.grid_columnconfigure(1, weight=1)

            frame_lista = ctk.CTkFrame(frame_split, fg_color=COR_CARD, corner_radius=15, border_width=1, border_color=COR_BORDAS)
            frame_lista.grid(row=0, column=0, sticky="nsew", padx=(0,10), ipadx=10, ipady=10)
            ctk.CTkLabel(frame_lista, text="Instituições Ativas (Duplo Clique)", font=ctk.CTkFont(weight="bold")).pack(pady=10)
            
            tree = ttk.Treeview(frame_lista, columns=('ID', 'Nome', 'Saldo'), show='headings', height=10)
            tree.heading('ID', text='ID'); tree.heading('Nome', text='Banco'); tree.heading('Saldo', text='Saldo Líquido')
            tree.column('ID', width=40, anchor='center'); tree.column('Nome', width=150); tree.column('Saldo', width=100, anchor='e')
            tree.pack(fill="both", expand=True, padx=10, pady=10)

            def drill_down(e):
                item = tree.selection()
                if item:
                    valores = tree.item(item[0])['values']
                    self.rotear_tela("detalhes_banco_especifico", kwargs={'id': valores[0], 'nome': valores[1]})
            tree.bind("<Double-1>", drill_down)

            try:
                cursor = self.db_conn.cursor()
                cursor.execute("SELECT c.id, c.nome, COALESCE(SUM(CASE WHEN cat.tipo_fluxo = 'RECEITA' THEN t.valor ELSE -t.valor END), 0) FROM tb_contas c LEFT JOIN tb_transacoes t ON c.id = t.conta_id LEFT JOIN tb_categorias cat ON t.categoria_id = cat.id GROUP BY c.id")
                for r in cursor.fetchall(): tree.insert('', 'end', values=(r[0], r[1], f"R$ {r[2]:.2f}"))
            except: pass

            frame_cad = ctk.CTkFrame(frame_split, fg_color=COR_CARD, corner_radius=15, border_width=1, border_color=COR_BORDAS)
            frame_cad.grid(row=0, column=1, sticky="nsew", padx=(10,0))
            ctk.CTkLabel(frame_cad, text="Vincular Nova Conta", font=ctk.CTkFont(weight="bold")).pack(pady=(20, 10))
            entry_nome = ctk.CTkEntry(frame_cad, width=220, placeholder_text="Instituição", height=45, corner_radius=10)
            entry_nome.pack(padx=20, pady=10)
            combo_tipo = ctk.CTkOptionMenu(frame_cad, values=["CORRENTE", "POUPANCA", "INVESTIMENTO"], fg_color=COR_FUNDO, height=45, corner_radius=10)
            combo_tipo.pack(padx=20, pady=10)

            def salvar():
                if entry_nome.get():
                    with self.transacao_db() as c: # [ACID IMPL]
                        c.execute("INSERT INTO tb_contas (nome, tipo) VALUES (?, ?)", (entry_nome.get(), combo_tipo.get()))
                    self.rotear_tela("detalhes_contas")
            ctk.CTkButton(frame_cad, text="Gravar Conta", fg_color=COR_PRIMARIA, height=45, corner_radius=10, command=salvar).pack(pady=20)

        # -------------------------------------------------------------
        # ROTA 4: TELEMETRIA ISOLADA
        # -------------------------------------------------------------
        elif tela_destino == "detalhes_banco_especifico":
            id_banco, nome_banco = kwargs.get('id'), kwargs.get('nome')
            ctk.CTkButton(self.main_frame, text="← Voltar", fg_color="transparent", command=lambda: self.rotear_tela("detalhes_contas")).pack(pady=(20, 0), padx=30, anchor="w")
            ctk.CTkLabel(self.main_frame, text=f"Telemetria: {nome_banco}", font=ctk.CTkFont(size=26, weight="bold")).pack(pady=10, padx=40, anchor="w")

            frame_kpi = ctk.CTkFrame(self.main_frame, fg_color="transparent")
            frame_kpi.pack(fill="x", padx=30, pady=20)
            frame_kpi.grid_columnconfigure((0, 1), weight=1)

            card_in = ctk.CTkFrame(frame_kpi, fg_color=COR_CARD, corner_radius=15, border_width=1, border_color=COR_BORDAS)
            card_in.grid(row=0, column=0, sticky="nsew", padx=10, ipadx=10, ipady=20)
            ctk.CTkLabel(card_in, text="Entradas", text_color=COR_TEXTO).pack(anchor="w", padx=20)
            lbl_in = ctk.CTkLabel(card_in, text="R$ 0,00", font=ctk.CTkFont(size=28, weight="bold"), text_color=COR_RECEITA)
            lbl_in.pack(anchor="w", padx=20, pady=(5,0))

            card_out = ctk.CTkFrame(frame_kpi, fg_color=COR_CARD, corner_radius=15, border_width=1, border_color=COR_BORDAS)
            card_out.grid(row=0, column=1, sticky="nsew", padx=10, ipadx=10, ipady=20)
            ctk.CTkLabel(card_out, text="Saídas", text_color=COR_TEXTO).pack(anchor="w", padx=20)
            lbl_out = ctk.CTkLabel(card_out, text="R$ 0,00", font=ctk.CTkFont(size=28, weight="bold"), text_color=COR_DESPESA)
            lbl_out.pack(anchor="w", padx=20, pady=(5,0))

            try:
                cursor = self.db_conn.cursor()
                cursor.execute("SELECT c.tipo_fluxo, COALESCE(SUM(t.valor), 0) FROM tb_transacoes t JOIN tb_categorias c ON t.categoria_id = c.id WHERE t.conta_id = ? GROUP BY c.tipo_fluxo", (id_banco,))
                fluxos = dict(cursor.fetchall())
                lbl_in.configure(text=self.aplicar_mascara_financeira(fluxos.get('RECEITA', 0)))
                lbl_out.configure(text=self.aplicar_mascara_financeira(fluxos.get('DESPESA', 0)))
            except Exception as e: print(e)

        # -------------------------------------------------------------
        # ROTA 5: HISTÓRICO GERAL
        # -------------------------------------------------------------
        elif tela_destino == "historico_dados":
            ctk.CTkButton(self.main_frame, text="← Voltar", fg_color="transparent", command=lambda: self.rotear_tela("dash")).pack(pady=(20, 0), padx=30, anchor="w")
            ctk.CTkLabel(self.main_frame, text="Livro-Razão Completo", font=ctk.CTkFont(size=26, weight="bold")).pack(pady=10, padx=40, anchor="w")
            
            frame_t = ctk.CTkFrame(self.main_frame, fg_color=COR_CARD, corner_radius=15, border_width=1, border_color=COR_BORDAS)
            frame_t.pack(fill="both", expand=True, padx=30, pady=10)
            tree = ttk.Treeview(frame_t, columns=('Data', 'Descricao', 'Valor', 'Banco'), show='headings')
            tree.heading('Data', text='Data'); tree.heading('Descricao', text='Descrição'); tree.heading('Valor', text='Valor'); tree.heading('Banco', text='Banco')
            tree.column('Data', width=100, anchor='center'); tree.column('Descricao', width=300); tree.column('Valor', width=120, anchor='e'); tree.column('Banco', width=120)
            tree.pack(fill="both", expand=True, padx=10, pady=10)
            try:
                cursor = self.db_conn.cursor()
                cursor.execute("SELECT t.data_transacao, t.descricao, t.valor, c.nome, cat.tipo_fluxo FROM tb_transacoes t JOIN tb_contas c ON t.conta_id = c.id JOIN tb_categorias cat ON t.categoria_id = cat.id ORDER BY t.data_transacao DESC")
                for r in cursor.fetchall():
                    tree.insert('', 'end', values=(r[0], r[1], self.aplicar_mascara_financeira(r[2]), r[3]))
            except: pass

        # -------------------------------------------------------------
        # ROTA 6: LANÇAMENTOS (I/O)
        # -------------------------------------------------------------
        elif tela_destino == "lancamentos":
            ctk.CTkButton(self.main_frame, text="← Voltar", fg_color="transparent", command=lambda: self.rotear_tela("dash")).pack(pady=(20, 0), padx=30, anchor="w")
            ctk.CTkLabel(self.main_frame, text="Motor de Lançamentos", font=ctk.CTkFont(size=26, weight="bold")).pack(pady=10, padx=40, anchor="w")

            try:
                cursor = self.db_conn.cursor()
                cursor.execute("SELECT id, nome FROM tb_contas")
                mapa_contas = {f"{nome}": id_c for id_c, nome in cursor.fetchall()}
                lista_contas = list(mapa_contas.keys()) if mapa_contas else ["Sem contas"]
            except: lista_contas = []; mapa_contas = {}

            frame_manual = ctk.CTkFrame(self.main_frame, fg_color=COR_CARD, corner_radius=15, border_width=1, border_color=COR_BORDAS)
            frame_manual.pack(fill="x", padx=30, pady=10)
            ctk.CTkLabel(frame_manual, text="Inserção Manual", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=2, pady=(15, 10))

            combo_conta = ctk.CTkOptionMenu(frame_manual, values=lista_contas, fg_color=COR_FUNDO, height=40, corner_radius=8)
            combo_conta.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
            
            self.var_data = ctk.StringVar()
            def masc_dt(*args):
                t = ''.join(filter(str.isdigit, self.var_data.get()))[:8]
                r = "".join([d + ("/" if i in [1, 3] else "") for i, d in enumerate(t)])
                if self.var_data.get() != r: self.var_data.set(r)
            self.var_data.trace_add("write", masc_dt)
            entry_dt = ctk.CTkEntry(frame_manual, textvariable=self.var_data, placeholder_text="DD/MM/YYYY", height=40, corner_radius=8)
            entry_dt.grid(row=1, column=1, padx=20, pady=10, sticky="ew")

            entry_desc = ctk.CTkEntry(frame_manual, placeholder_text="Descrição", height=40, corner_radius=8)
            entry_desc.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
            
            self.var_valor = ctk.StringVar()
            def masc_val(*args):
                v = ''.join(c for c in self.var_valor.get() if c.isdigit() or c=='.')
                if v.count('.')>1: v=v[:-1]
                if self.var_valor.get() != v: self.var_valor.set(v)
            self.var_valor.trace_add("write", masc_val)
            entry_val = ctk.CTkEntry(frame_manual, textvariable=self.var_valor, placeholder_text="Valor Bruto (R$)", height=40, corner_radius=8)
            entry_val.grid(row=2, column=1, padx=20, pady=10, sticky="ew")

            combo_tipo = ctk.CTkOptionMenu(frame_manual, values=["Despesa", "Recebimento"], fg_color=COR_FUNDO, height=40, corner_radius=8)
            combo_tipo.grid(row=3, column=0, padx=20, pady=10, sticky="ew")

            lbl_fb_man = ctk.CTkLabel(frame_manual, text="")
            lbl_fb_man.grid(row=4, column=0, columnspan=2, pady=5)

            def salvar_man():
                if not mapa_contas: return
                try:
                    d_iso = datetime.strptime(entry_dt.get(), '%d/%m/%Y').strftime('%Y-%m-%d')
                    v = float(entry_val.get())
                    cat = 1 if combo_tipo.get() == "Recebimento" else 4
                    with self.transacao_db() as c: # [ACID IMPL]
                        c.execute("INSERT INTO tb_transacoes (conta_id, categoria_id, valor, data_transacao, descricao) VALUES (?, ?, ?, ?, ?)", (mapa_contas[combo_conta.get()], cat, abs(v), d_iso, entry_desc.get()))
                    self.rotear_tela("dash")
                except Exception as e: lbl_fb_man.configure(text=f"Erro: {e}", text_color=COR_DESPESA)

            ctk.CTkButton(frame_manual, text="Gravar", fg_color=COR_PRIMARIA, height=40, corner_radius=8, command=salvar_man).grid(row=3, column=1, padx=20, pady=10, sticky="ew")
            frame_manual.grid_columnconfigure((0,1), weight=1)

            frame_csv = ctk.CTkFrame(self.main_frame, fg_color=COR_CARD, corner_radius=15, border_width=1, border_color=COR_BORDAS)
            frame_csv.pack(fill="x", padx=30, pady=10)
            ctk.CTkLabel(frame_csv, text="Ingestão de Lote (.CSV)", font=ctk.CTkFont(weight="bold")).pack(pady=(15, 5))
            combo_csv = ctk.CTkOptionMenu(frame_csv, values=lista_contas, fg_color=COR_FUNDO, height=40, corner_radius=8)
            combo_csv.pack(pady=10, padx=20, fill="x")
            
            lbl_fb_csv = ctk.CTkLabel(frame_csv, text="")
            lbl_fb_csv.pack()

            def imp_csv():
                cam = filedialog.askopenfilename(filetypes=[("CSV", "*.csv")])
                if cam and mapa_contas:
                    try:
                        df = pd.read_csv(cam, header=0, names=['Data', 'Descricao', 'Valor'])
                        df['Data'] = pd.to_datetime(df['Data'], dayfirst=True, format='mixed').dt.strftime('%Y-%m-%d')
                        reg = [(mapa_contas[combo_csv.get()], 1 if float(r['Valor'])>0 else 4, abs(float(r['Valor'])), r['Data'], r['Descricao']) for _, r in df.iterrows()]
                        with self.transacao_db() as c: # [ACID IMPL]
                            c.executemany("INSERT INTO tb_transacoes (conta_id, categoria_id, valor, data_transacao, descricao) VALUES (?, ?, ?, ?, ?)", reg)
                        self.rotear_tela("dash") 
                    except Exception as e: lbl_fb_csv.configure(text=f"Erro CSV: {e}", text_color=COR_DESPESA)
            ctk.CTkButton(frame_csv, text="Carregar Arquivo", fg_color="#2980b9", height=40, corner_radius=8, command=imp_csv).pack(pady=10, padx=20, fill="x")

        # -------------------------------------------------------------
        # ROTA 7: PLANEJAMENTO (ORÇAMENTOS E METAS FUNCIONAIS)
        # -------------------------------------------------------------
        elif tela_destino == "planejamento":
            kwargs = kwargs or {}
            aba = kwargs.get('aba', 'orcamentos')

            frame_top = ctk.CTkFrame(self.main_frame, fg_color="transparent")
            frame_top.pack(fill="x", padx=30, pady=(20,0))
            ctk.CTkLabel(frame_top, text="Planejamento Financeiro", font=ctk.CTkFont(size=26, weight="bold")).pack(side="left")

            frame_nav = ctk.CTkFrame(self.main_frame, fg_color="transparent")
            frame_nav.pack(fill="x", padx=30, pady=15)
            
            c_orc = COR_PRIMARIA if aba == 'orcamentos' else COR_CARD
            c_met = COR_PRIMARIA if aba == 'metas' else COR_CARD

            ctk.CTkButton(frame_nav, text="Orçamentos (Mensal)", fg_color=c_orc, corner_radius=8, height=40, command=lambda: self.rotear_tela("planejamento", {'aba': 'orcamentos'})).pack(side="left", padx=(0, 10))
            ctk.CTkButton(frame_nav, text="Metas (Capital)", fg_color=c_met, corner_radius=8, height=40, command=lambda: self.rotear_tela("planejamento", {'aba': 'metas'})).pack(side="left")

            frame_conteudo = ctk.CTkFrame(self.main_frame, fg_color="transparent")
            frame_conteudo.pack(fill="both", expand=True, padx=30, pady=5)

            if aba == 'orcamentos':
                f_split = ctk.CTkFrame(frame_conteudo, fg_color="transparent")
                f_split.pack(fill="both", expand=True)
                f_split.grid_columnconfigure(0, weight=1)
                f_split.grid_columnconfigure(1, weight=2) 

                f_forjar = ctk.CTkFrame(f_split, fg_color=COR_CARD, corner_radius=15, border_width=1, border_color=COR_BORDAS)
                f_forjar.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
                ctk.CTkLabel(f_forjar, text="Adicionar Despesa", font=ctk.CTkFont(weight="bold")).pack(pady=20)

                e_nome_desp = ctk.CTkEntry(f_forjar, placeholder_text="Nome da Despesa", height=45, corner_radius=10)
                e_nome_desp.pack(pady=10, padx=20, fill="x")
                
                cb_tipo_desp = ctk.CTkOptionMenu(f_forjar, values=["Essencial", "Variável", "Assinatura", "Imposto"], fg_color=COR_FUNDO, height=45, corner_radius=10)
                cb_tipo_desp.pack(pady=10, padx=20, fill="x")

                v_data = ctk.StringVar()
                def m_data(*args):
                    t = ''.join(filter(str.isdigit, v_data.get()))[:8]
                    r = "".join([d + ("/" if i in [1, 3] else "") for i, d in enumerate(t)])
                    if v_data.get() != r: v_data.set(r)
                v_data.trace_add("write", m_data)

                e_venc = ctk.CTkEntry(f_forjar, textvariable=v_data, placeholder_text="Data (DD/MM/YYYY)", height=45, corner_radius=10)
                e_venc.pack(pady=10, padx=20, fill="x")

                e_preco = ctk.CTkEntry(f_forjar, placeholder_text="Preço $", height=45, corner_radius=10)
                e_preco.pack(pady=10, padx=20, fill="x")

                lbl_fb_orc = ctk.CTkLabel(f_forjar, text="", text_color=COR_DESPESA)
                lbl_fb_orc.pack(pady=5)

                def gravar_despesa():
                    try:
                        if not e_nome_desp.get() or not e_preco.get(): raise ValueError("Nome e Preço obrigatórios.")
                        if len(e_venc.get()) != 10: raise ValueError("Data DD/MM/YYYY.")
                            
                        d_iso = datetime.strptime(e_venc.get(), '%d/%m/%Y').strftime('%Y-%m-%d')
                        mes = datetime.now().strftime('%Y-%m')
                        valor_formatado = float(e_preco.get().replace(',','.'))
                        
                        with self.transacao_db() as c: # [ACID IMPL]
                            c.execute("INSERT INTO tb_orcamentos (nome, tipo, data_vencimento, valor, mes_referencia) VALUES (?, ?, ?, ?, ?)", 
                                      (e_nome_desp.get(), cb_tipo_desp.get(), d_iso, abs(valor_formatado), mes))
                        self.rotear_tela("planejamento", {'aba': 'orcamentos'})
                    except ValueError as ve: lbl_fb_orc.configure(text=f"Aviso: {ve}")
                    except Exception as e: lbl_fb_orc.configure(text=f"Erro Banco: {e}")

                ctk.CTkButton(f_forjar, text="Gravar Despesa", fg_color=COR_PRIMARIA, height=45, corner_radius=10, command=gravar_despesa).pack(pady=10, padx=20, fill="x")

                f_lista = ctk.CTkScrollableFrame(f_split, fg_color=COR_CARD, corner_radius=15, border_width=1, border_color=COR_BORDAS)
                f_lista.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
                ctk.CTkLabel(f_lista, text="Orçamento Comprometido (Mês Atual)", font=ctk.CTkFont(weight="bold")).pack(pady=10)

                header = ctk.CTkFrame(f_lista, fg_color=COR_FUNDO, corner_radius=5)
                header.pack(fill="x", padx=10, pady=5, ipadx=5, ipady=5)
                header.grid_columnconfigure((0,1,2,3), weight=1)
                ctk.CTkLabel(header, text="NOME", font=ctk.CTkFont(weight="bold", size=11), text_color=COR_BORDAS).grid(row=0, column=0, sticky="w")
                ctk.CTkLabel(header, text="TIPO", font=ctk.CTkFont(weight="bold", size=11), text_color=COR_BORDAS).grid(row=0, column=1, sticky="w")
                ctk.CTkLabel(header, text="VENCIMENTO", font=ctk.CTkFont(weight="bold", size=11), text_color=COR_BORDAS).grid(row=0, column=2, sticky="center")
                ctk.CTkLabel(header, text="VALOR", font=ctk.CTkFont(weight="bold", size=11), text_color=COR_BORDAS).grid(row=0, column=3, sticky="e")

                try:
                    mes_corrente = datetime.now().strftime('%Y-%m')
                    cursor = self.db_conn.cursor()
                    cursor.execute("SELECT nome, tipo, data_vencimento, valor FROM tb_orcamentos WHERE mes_referencia = ? ORDER BY data_vencimento ASC", (mes_corrente,))
                    linhas = cursor.fetchall()
                    if not linhas:
                        ctk.CTkLabel(f_lista, text="Nenhuma despesa orçada.", text_color=COR_TEXTO).pack(pady=20)
                    else:
                        for idx, (nome, tipo, dv, val) in enumerate(linhas):
                            cor_linha = COR_ZEBRA_1 if idx % 2 == 0 else COR_ZEBRA_2
                            row_f = ctk.CTkFrame(f_lista, fg_color=cor_linha, corner_radius=0)
                            row_f.pack(fill="x", padx=10, pady=0, ipadx=5, ipady=8)
                            row_f.grid_columnconfigure((0,1,2,3), weight=1)
                            
                            dv_fmt = datetime.strptime(dv, '%Y-%m-%d').strftime('%d/%m/%Y')
                            ctk.CTkLabel(row_f, text=nome, text_color=COR_TEXTO_FORTE).grid(row=0, column=0, sticky="w")
                            ctk.CTkLabel(row_f, text=tipo, text_color=COR_TEXTO).grid(row=0, column=1, sticky="w")
                            ctk.CTkLabel(row_f, text=dv_fmt, text_color=COR_TEXTO).grid(row=0, column=2, sticky="center")
                            ctk.CTkLabel(row_f, text=self.aplicar_mascara_financeira(val), text_color=COR_DESPESA, font=ctk.CTkFont(weight="bold")).grid(row=0, column=3, sticky="e")
                except Exception as e: ctk.CTkLabel(f_lista, text=f"Erro de DB: {e}", text_color=COR_DESPESA).pack()

            elif aba == 'metas':
                f_split_m = ctk.CTkFrame(frame_conteudo, fg_color="transparent")
                f_split_m.pack(fill="both", expand=True)
                f_split_m.grid_columnconfigure(0, weight=1)
                f_split_m.grid_columnconfigure(1, weight=2)

                f_meta = ctk.CTkFrame(f_split_m, fg_color=COR_CARD, corner_radius=15, border_width=1, border_color=COR_BORDAS)
                f_meta.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
                ctk.CTkLabel(f_meta, text="Forjar Nova Meta", font=ctk.CTkFont(weight="bold")).pack(pady=20)

                e_nm = ctk.CTkEntry(f_meta, placeholder_text="Nome (Ex: Casa)", height=45, corner_radius=10)
                e_nm.pack(pady=10, padx=20, fill="x")
                e_alv = ctk.CTkEntry(f_meta, placeholder_text="Alvo Financeiro (R$)", height=45, corner_radius=10)
                e_alv.pack(pady=10, padx=20, fill="x")
                e_ap = ctk.CTkEntry(f_meta, placeholder_text="Aporte Atual (R$)", height=45, corner_radius=10)
                e_ap.pack(pady=10, padx=20, fill="x")
                
                lbl_fb_meta = ctk.CTkLabel(f_meta, text="", text_color=COR_DESPESA)
                lbl_fb_meta.pack(pady=5)

                def gravar_meta():
                    try:
                        n_meta = e_nm.get(); t_alvo = e_alv.get(); t_ap = e_ap.get()
                        if not n_meta or not t_alvo: raise ValueError("Nome e Alvo obrigatórios.")
                        v_alvo = float(t_alvo.replace(',','.'))
                        v_aporte = float(t_ap.replace(',','.')) if t_ap.strip() else 0.0
                        with self.transacao_db() as c: # [ACID IMPL]
                            c.execute("INSERT INTO tb_metas (nome, valor_alvo, valor_acumulado) VALUES (?, ?, ?)", (n_meta, v_alvo, v_aporte))
                        self.rotear_tela("planejamento", {'aba': 'metas'})
                    except ValueError as ve: lbl_fb_meta.configure(text=f"Aviso: {ve}")
                    except Exception as e: lbl_fb_meta.configure(text=f"Erro: {e}")

                ctk.CTkButton(f_meta, text="Gravar Meta", fg_color=COR_PRIMARIA, height=45, corner_radius=10, command=gravar_meta).pack(pady=10, padx=20, fill="x")

                p_track = ctk.CTkScrollableFrame(f_split_m, fg_color=COR_CARD, corner_radius=15, border_width=1, border_color=COR_BORDAS)
                p_track.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
                ctk.CTkLabel(p_track, text="Tracking de Capital", font=ctk.CTkFont(weight="bold")).pack(pady=10)

                try:
                    c = self.db_conn.cursor()
                    c.execute("SELECT nome, valor_alvo, valor_acumulado FROM tb_metas")
                    dados_metas = c.fetchall()
                    if not dados_metas: ctk.CTkLabel(p_track, text="Nenhuma meta forjada.", text_color=COR_TEXTO).pack(pady=20)
                    for n, a, ac in dados_metas:
                        cd = ctk.CTkFrame(p_track, fg_color=COR_FUNDO, corner_radius=8)
                        cd.pack(fill="x", pady=5, padx=10, ipadx=10, ipady=10)
                        pct = min(ac/a, 1.0) if a>0 else 1.0
                        
                        head_f = ctk.CTkFrame(cd, fg_color="transparent")
                        head_f.pack(fill="x")
                        ctk.CTkLabel(head_f, text=n, font=ctk.CTkFont(weight="bold")).pack(side="left")
                        ctk.CTkLabel(head_f, text=f"{pct*100:.1f}%", text_color=COR_RECEITA, font=ctk.CTkFont(weight="bold")).pack(side="right")
                        
                        br = ctk.CTkProgressBar(cd, progress_color=COR_RECEITA, fg_color="#1E1E2C", height=15)
                        br.pack(fill="x", pady=8); br.set(pct)
                        ctk.CTkLabel(cd, text=f"Alocado: {self.aplicar_mascara_financeira(ac)} / Alvo: {self.aplicar_mascara_financeira(a)}", text_color=COR_TEXTO, font=ctk.CTkFont(size=11)).pack(anchor="w")
                except: pass

if __name__ == "__main__":
    app = PlataformaFinanceira()
    app.mainloop()
