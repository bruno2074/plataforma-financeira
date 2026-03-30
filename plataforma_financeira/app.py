import customtkinter as ctk
import sqlcipher3.dbapi2 as sqlite3
import os
import pandas as pd
import plotly.express as px
import io
from PIL import Image
from tkinter import filedialog
from database_core import init_db

# --- Paleta Wealth.Core (Anti-Neon / Cyberpunk Institucional) ---
COR_FUNDO = "#0D0E15"       # Matte Obsidian
COR_CARD = "#1A1B26"        # Aço Escovado
COR_TEXTO = "#A9B1D6"       # Cinza Gelo
COR_RECEITA = "#41A5B4"     # Ciano Institucional
COR_DESPESA = "#C5A880"     # Ouro Envelhecido / Bronze

# Configuração global de design minimalista
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

class PlataformaFinanceira(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Wealth Engine - Elliot")
        self.geometry("400x300")
        self.resizable(False, False)
        
        # Estado Global de Autenticação e UX
        self.db_conn = None 
        self.modo_privacidade = False # Trava de segurança visual
        self.tela_atual = "dash"      # Rastreador de navegação

        self.construir_tela_login()

    def construir_tela_login(self):
        self.frame_login = ctk.CTkFrame(self)
        self.frame_login.pack(pady=40, padx=40, fill="both", expand=True)

        self.label_titulo = ctk.CTkLabel(self.frame_login, text="Cofre Criptográfico", font=ctk.CTkFont(size=20, weight="bold"))
        self.label_titulo.pack(pady=(20, 10))

        self.entry_senha = ctk.CTkEntry(self.frame_login, placeholder_text="Insira a Master Key", show="*")
        self.entry_senha.pack(pady=10, padx=20, fill="x")

        self.btn_login = ctk.CTkButton(self.frame_login, text="Descriptografar e Entrar", command=self.tentar_login)
        self.btn_login.pack(pady=20, padx=20, fill="x")

        self.label_status = ctk.CTkLabel(self.frame_login, text="", text_color="red")
        self.label_status.pack(pady=(0, 10))

    def tentar_login(self):
        senha_digitada = self.entry_senha.get()
        if not senha_digitada:
            self.label_status.configure(text="Erro: Chave vazia.")
            return

        try:
            if not os.path.exists('finance_core.db'):
                init_db(senha_digitada) 

            conn = sqlite3.connect('finance_core.db')
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA key='{senha_digitada}'")
            cursor.execute("SELECT count(*) FROM sqlite_master;") 
            cursor.fetchone()
            
            self.db_conn = conn
            self.label_status.configure(text="Acesso Concedido!", text_color="green")
            self.after(1, self.carregar_dashboard)

        except sqlite3.DatabaseError:
            self.label_status.configure(text="Erro: Chave Incorreta ou DB Corrompido.")
            if 'conn' in locals():
                conn.close()

    def carregar_dashboard(self):
        self.frame_login.destroy()
        self.geometry("1100x700")
        self.title("Wealth Engine - Command Center")
        self.resizable(True, True)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # --- SIDEBAR & NAVEGAÇÃO ---
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(6, weight=1) 

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="Wealth.Core", font=ctk.CTkFont(size=22, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 30))

        self.btn_nav_dash = ctk.CTkButton(self.sidebar_frame, text="Visão Geral", command=lambda: self.rotear_tela("dash"))
        self.btn_nav_dash.grid(row=1, column=0, padx=20, pady=10)

        self.btn_nav_lancamentos = ctk.CTkButton(self.sidebar_frame, text="Lançamentos (I/O)", command=lambda: self.rotear_tela("lancamentos"))
        self.btn_nav_lancamentos.grid(row=2, column=0, padx=20, pady=10)

        self.btn_nav_orcamento = ctk.CTkButton(self.sidebar_frame, text="Orçamentos", command=lambda: self.rotear_tela("orcamento"))
        self.btn_nav_orcamento.grid(row=3, column=0, padx=20, pady=10)

        self.btn_nav_invest = ctk.CTkButton(self.sidebar_frame, text="Investimentos", command=lambda: self.rotear_tela("invest"))
        self.btn_nav_invest.grid(row=4, column=0, padx=20, pady=10)

        # --- BOTÃO: PRIVACY MODE ---
        def toggle_privacidade():
            self.modo_privacidade = not self.modo_privacidade
            txt = "👁‍🗨 Revelar Valores" if self.modo_privacidade else "🕶 Ocultar Valores"
            self.btn_privacidade.configure(text=txt)
            self.rotear_tela(self.tela_atual) 

        self.btn_privacidade = ctk.CTkButton(self.sidebar_frame, text="🕶 Ocultar Valores", fg_color="#333333", hover_color="#555555", command=toggle_privacidade)
        self.btn_privacidade.grid(row=7, column=0, padx=20, pady=20, sticky="s")

        self.main_frame = ctk.CTkFrame(self, corner_radius=10, fg_color=COR_FUNDO)
        self.main_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        
        self.rotear_tela("dash")

    def rotear_tela(self, tela_destino):
        self.tela_atual = tela_destino 
        for widget in self.main_frame.winfo_children():
            widget.destroy()
            
        if tela_destino == "dash":
            titulo = ctk.CTkLabel(self.main_frame, text="Visão Geral Financeira", font=ctk.CTkFont(size=24, weight="bold"))
            titulo.pack(pady=20, padx=20, anchor="w")
            
            try:
                cursor = self.db_conn.cursor()
                cursor.execute("SELECT nome, tipo FROM tb_contas")
                contas_db = cursor.fetchall()
                cursor.execute("SELECT COUNT(*), SUM(valor) FROM tb_transacoes")
                stats_transacoes = cursor.fetchone()
            except Exception as e:
                ctk.CTkLabel(self.main_frame, text=f"Erro de DB: {e}", text_color="red").pack()
                return

            painel_cards = ctk.CTkFrame(self.main_frame, fg_color="transparent")
            painel_cards.pack(fill="x", padx=20, pady=10)
            painel_cards.grid_columnconfigure((0, 1), weight=1)

            # CARD 1: CONTAS
            card_contas = ctk.CTkFrame(painel_cards, corner_radius=10, fg_color=COR_CARD)
            card_contas.grid(row=0, column=0, padx=10, sticky="nsew")
            ctk.CTkLabel(card_contas, text="🏦 Suas Contas", font=ctk.CTkFont(size=16, weight="bold"), text_color="white").pack(pady=10)
            if contas_db:
                for nome, tipo in contas_db:
                    ctk.CTkLabel(card_contas, text=f"{nome} ({tipo})", text_color=COR_TEXTO).pack(pady=2)

            # CARD 2: EXTRATO (COM DRILL-DOWN EVENT BINDING)
            card_extrato = ctk.CTkFrame(painel_cards, corner_radius=10, cursor="hand2", fg_color=COR_CARD)
            card_extrato.grid(row=0, column=1, padx=10, sticky="nsew")
            
            card_extrato.bind("<Button-1>", lambda event: self.rotear_tela("historico_dados"))
            
            lbl_title = ctk.CTkLabel(card_extrato, text="📊 Dados Ingeridos (Clique para Detalhes)", font=ctk.CTkFont(size=14, weight="bold"), text_color="white")
            lbl_title.pack(pady=10)
            lbl_title.bind("<Button-1>", lambda event: self.rotear_tela("historico_dados"))
            
            qtd_transacoes = stats_transacoes[0] if stats_transacoes else 0
            volume_movimentado = stats_transacoes[1] if stats_transacoes and stats_transacoes[1] else 0.0
            vol_str = "R$ ****" if self.modo_privacidade else f"R$ {volume_movimentado:,.2f}"
            
            lbl_qtd = ctk.CTkLabel(card_extrato, text=f"Total de Registros: {qtd_transacoes}", text_color=COR_TEXTO)
            lbl_qtd.pack(pady=2)
            lbl_qtd.bind("<Button-1>", lambda event: self.rotear_tela("historico_dados"))
            
            lbl_vol = ctk.CTkLabel(card_extrato, text=f"Volume Bruto: {vol_str}", text_color=COR_TEXTO)
            lbl_vol.pack(pady=2)
            lbl_vol.bind("<Button-1>", lambda event: self.rotear_tela("historico_dados"))

            # --- MOTOR DO GRÁFICO (LAZY LOADING) ---
            self.frame_grafico = ctk.CTkFrame(self.main_frame, fg_color="transparent")
            self.grafico_gerado = False

            def toggle_grafico():
                if self.modo_privacidade:
                    btn_toggle.configure(text="Desative o Modo Privacidade para plotar.", state="normal")
                    return

                if not self.grafico_gerado:
                    btn_toggle.configure(text="Carregando Motor Gráfico...", state="disabled")
                    self.update()
                    try:
                        query = """
                        SELECT c.tipo_fluxo, SUM(t.valor) as total
                        FROM tb_transacoes t JOIN tb_categorias c ON t.categoria_id = c.id
                        GROUP BY c.tipo_fluxo
                        """
                        cursor_grafico = self.db_conn.cursor()
                        cursor_grafico.execute(query)
                        colunas = [desc[0] for desc in cursor_grafico.description]
                        df_grafico = pd.DataFrame(cursor_grafico.fetchall(), columns=colunas)

                        if not df_grafico.empty:
                            fig = px.bar(df_grafico, x='tipo_fluxo', y='total', color='tipo_fluxo', 
                                         color_discrete_map={'RECEITA': COR_RECEITA, 'DESPESA': COR_DESPESA},
                                         text_auto='.2s')
                            
                            fig.update_layout(
                                xaxis_title=None, yaxis_title=None, showlegend=False,
                                margin=dict(l=0, r=0, t=20, b=0),
                                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=300
                            )
                            fig.update_xaxes(showgrid=False, tickfont=dict(size=14, color='white'))
                            fig.update_yaxes(visible=False, showgrid=False)
                            
                            img_bytes = fig.to_image(format="png", width=600, height=300)
                            imagem_pil = Image.open(io.BytesIO(img_bytes))
                            ctk_img = ctk.CTkImage(light_image=imagem_pil, dark_image=imagem_pil, size=(600, 300))
                            
                            ctk.CTkLabel(self.frame_grafico, image=ctk_img, text="").pack()
                            self.grafico_gerado = True
                    except Exception as e:
                        ctk.CTkLabel(self.frame_grafico, text=f"Erro na renderização: {e}", text_color="red").pack()
                        self.grafico_gerado = True

                if self.frame_grafico.winfo_ismapped():
                    self.frame_grafico.pack_forget()
                    btn_toggle.configure(text="Exibir Análise Gráfica ▼", state="normal")
                else:
                    self.frame_grafico.pack(pady=20, fill="x")
                    btn_toggle.configure(text="Ocultar Análise Gráfica ▲", state="normal")

            btn_toggle = ctk.CTkButton(self.main_frame, text="Exibir Análise Gráfica ▼", fg_color="transparent", border_width=1, command=toggle_grafico)
            btn_toggle.pack(pady=20)
            
        elif tela_destino == "historico_dados":
            btn_voltar = ctk.CTkButton(self.main_frame, text="← Voltar ao Dashboard", fg_color="transparent", border_width=1, command=lambda: self.rotear_tela("dash"))
            btn_voltar.pack(pady=(20, 0), padx=20, anchor="w")

            titulo = ctk.CTkLabel(self.main_frame, text="Livro-Razão (Histórico de Lançamentos)", font=ctk.CTkFont(size=24, weight="bold"))
            titulo.pack(pady=20, padx=20, anchor="w")

            scroll_frame = ctk.CTkScrollableFrame(self.main_frame, fg_color="transparent")
            scroll_frame.pack(fill="both", expand=True, padx=20, pady=10)

            try:
                cursor = self.db_conn.cursor()
                query = """
                SELECT t.data_transacao, t.descricao, t.valor, c.tipo_fluxo 
                FROM tb_transacoes t 
                JOIN tb_categorias c ON t.categoria_id = c.id 
                ORDER BY t.data_transacao DESC
                """
                cursor.execute(query)
                historico = cursor.fetchall()

                if not historico:
                    ctk.CTkLabel(scroll_frame, text="Nenhum registro encontrado no cofre.").pack(pady=20)
                else:
                    for data_t, desc, valor, tipo in historico:
                        cor_linha = COR_RECEITA if tipo == "RECEITA" else COR_DESPESA
                        linha_frame = ctk.CTkFrame(scroll_frame, fg_color=COR_CARD, corner_radius=5)
                        linha_frame.pack(fill="x", pady=5)
                        
                        ctk.CTkLabel(linha_frame, text=f"{data_t}", width=100, anchor="w").pack(side="left", padx=10, pady=10)
                        ctk.CTkLabel(linha_frame, text=f"{desc}", width=300, anchor="w").pack(side="left", padx=10, pady=10)
                        
                        val_display = "****" if self.modo_privacidade else f"R$ {valor:.2f}"
                        ctk.CTkLabel(linha_frame, text=val_display, text_color=cor_linha, font=ctk.CTkFont(weight="bold")).pack(side="right", padx=20, pady=10)

            except Exception as e:
                ctk.CTkLabel(scroll_frame, text=f"Erro de DB: {e}", text_color="red").pack()

        elif tela_destino == "lancamentos":
            titulo = ctk.CTkLabel(self.main_frame, text="Motor de Lançamentos", font=ctk.CTkFont(size=24, weight="bold"))
            titulo.pack(pady=20, padx=20, anchor="w")

            # MÓDULO I/O BATCH (CSV)
            frame_csv = ctk.CTkFrame(self.main_frame, corner_radius=10, fg_color=COR_CARD)
            frame_csv.pack(fill="x", padx=20, pady=10)
            ctk.CTkLabel(frame_csv, text="📁 Ingestão em Lote (CSV Bancário)", font=ctk.CTkFont(weight="bold")).pack(pady=10)
            
            def importar_csv_interno():
                caminho = filedialog.askopenfilename(filetypes=[("Arquivos CSV", "*.csv")])
                if not caminho: return
                try:
                    df = pd.read_csv(caminho, header=0, names=['Data', 'Descricao', 'Valor'])
                    df['Data'] = pd.to_datetime(df['Data'], format='%d/%m/%Y').dt.strftime('%Y-%m-%d')
                    
                    registros = []
                    for _, row in df.iterrows():
                        v = float(row['Valor'])
                        cat = 1 if v > 0 else 4
                        registros.append((1, cat, abs(v), row['Data'], row['Descricao']))
                    
                    cursor = self.db_conn.cursor()
                    cursor.executemany("INSERT INTO tb_transacoes (conta_id, categoria_id, valor, data_transacao, descricao) VALUES (?, ?, ?, ?, ?)", registros)
                    self.db_conn.commit()
                    ctk.CTkLabel(frame_csv, text=f"[+] {len(registros)} registros injetados no cofre.", text_color=COR_RECEITA).pack(pady=5)
                except Exception as e:
                    ctk.CTkLabel(frame_csv, text=f"[X] Falha no Parsing: {e}", text_color=COR_DESPESA).pack(pady=5)

            ctk.CTkButton(frame_csv, text="Selecionar Arquivo .CSV", fg_color="#2980b9", command=importar_csv_interno).pack(pady=10)

            # MÓDULO I/O MANUAL
            frame_manual = ctk.CTkFrame(self.main_frame, corner_radius=10, fg_color=COR_CARD)
            frame_manual.pack(fill="x", padx=20, pady=10)
            ctk.CTkLabel(frame_manual, text="✍️ Inserção Cirúrgica (Manual)", font=ctk.CTkFont(weight="bold")).pack(pady=10)

            form_grid = ctk.CTkFrame(frame_manual, fg_color="transparent")
            form_grid.pack(pady=10)

            ctk.CTkLabel(form_grid, text="Data (DD/MM/YYYY):").grid(row=0, column=0, padx=10, pady=5, sticky="e")
            entry_data = ctk.CTkEntry(form_grid, placeholder_text="Ex: 25/10/2026")
            entry_data.grid(row=0, column=1, padx=10, pady=5)

            ctk.CTkLabel(form_grid, text="Descrição:").grid(row=1, column=0, padx=10, pady=5, sticky="e")
            entry_desc = ctk.CTkEntry(form_grid, placeholder_text="Ex: Restaurante")
            entry_desc.grid(row=1, column=1, padx=10, pady=5)

            ctk.CTkLabel(form_grid, text="Valor Bruto (R$):").grid(row=2, column=0, padx=10, pady=5, sticky="e")
            entry_valor = ctk.CTkEntry(form_grid, placeholder_text="Ex: 150.00")
            entry_valor.grid(row=2, column=1, padx=10, pady=5)

            ctk.CTkLabel(form_grid, text="Natureza:").grid(row=3, column=0, padx=10, pady=5, sticky="e")
            combo_tipo = ctk.CTkOptionMenu(form_grid, values=["DESPESA", "RECEITA"], fg_color="#333333")
            combo_tipo.grid(row=3, column=1, padx=10, pady=5)

            def salvar_manual():
                try:
                    d_iso = pd.to_datetime(entry_data.get(), format='%d/%m/%Y').strftime('%Y-%m-%d')
                    v = float(entry_valor.get())
                    desc = entry_desc.get()
                    cat = 1 if combo_tipo.get() == "RECEITA" else 4
                    
                    cursor = self.db_conn.cursor()
                    cursor.execute("INSERT INTO tb_transacoes (conta_id, categoria_id, valor, data_transacao, descricao) VALUES (?, ?, ?, ?, ?)", (1, cat, abs(v), d_iso, desc))
                    self.db_conn.commit()
                    
                    entry_desc.delete(0, 'end')
                    entry_valor.delete(0, 'end')
                    ctk.CTkLabel(form_grid, text="[+] Transação gravada com sucesso.", text_color=COR_RECEITA).grid(row=4, column=0, columnspan=2, pady=5)
                except Exception as e:
                    ctk.CTkLabel(form_grid, text=f"[X] Erro de validação: {e}", text_color=COR_DESPESA).grid(row=4, column=0, columnspan=2, pady=5)

            ctk.CTkButton(form_grid, text="Gravar no Cofre", fg_color="#27ae60", hover_color="#2ecc71", command=salvar_manual).grid(row=5, column=0, columnspan=2, pady=15)

        elif tela_destino == "orcamento":
            titulo = ctk.CTkLabel(self.main_frame, text="Planejamento e Metas", font=ctk.CTkFont(size=24, weight="bold"))
            titulo.pack(pady=20, padx=20, anchor="w")
            
        elif tela_destino == "invest":
            titulo = ctk.CTkLabel(self.main_frame, text="Wealth Management & Ativos", font=ctk.CTkFont(size=24, weight="bold"))
            titulo.pack(pady=20, padx=20, anchor="w")

if __name__ == "__main__":
    app = PlataformaFinanceira()
    app.mainloop()
