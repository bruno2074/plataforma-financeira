# app.py
import customtkinter as ctk
import sqlcipher3.dbapi2 as sqlite3
import os
import pandas as pd
import plotly.express as px
import io
from PIL import Image
from database_core import init_db


# Configuração global de design minimalista
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

class PlataformaFinanceira(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Wealth Engine - Plataforma Financeira Pessoal")
        self.geometry("400x300")
        self.resizable(False, False)
        
        # Variável para segurar a conexão após o login
        self.db_conn = None 

        self.construir_tela_login()

    def construir_tela_login(self):
        # Container centralizado
        self.frame_login = ctk.CTkFrame(self)
        self.frame_login.pack(pady=40, padx=40, fill="both", expand=True)

        self.label_titulo = ctk.CTkLabel(self.frame_login, text="Cofre Criptográfico", font=ctk.CTkFont(size=20, weight="bold"))
        self.label_titulo.pack(pady=(20, 10))

        # Campo ofuscado para a senha
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
            # 1. Se o banco não existe, vamos criá-lo agora usando a senha digitada
            if not os.path.exists('finance_core.db'):
                # Precisamos modificar a init_db para aceitar a senha dinâmica
                init_db(senha_digitada) 

            # 2. Tenta conectar e ler uma tabela básica para validar a chave
            conn = sqlite3.connect('finance_core.db')
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA key='{senha_digitada}'")
            
            # Se a senha for errada, o SQLCipher só acusa erro quando tentamos LER o dado
            cursor.execute("SELECT count(*) FROM sqlite_master;") 
            cursor.fetchone()
            
            self.db_conn = conn # Salva a conexão autorizada
            self.label_status.configure(text="Acesso Concedido!", text_color="green")
            
            # AQUI: Destruir tela de login e carregar Dashboard
            self.after(1, self.carregar_dashboard)

        except sqlite3.DatabaseError:
            self.label_status.configure(text="Erro: Chave Incorreta ou DB Corrompido.")
            if 'conn' in locals():
                conn.close()

    def carregar_dashboard(self):
        # 1. Transição de Estado da Janela
        self.frame_login.destroy() # Remove a tela de login
        self.geometry("1100x700") # Redimensiona para o dashboard
        self.title("Wealth.Core - Command Center")
        self.resizable(True, True)
        # 2. Configuração do Motor de Geometria (Master Grid)
        self.grid_rowconfigure(0, weight=1)    # Linha única expande 100% da altura
        self.grid_columnconfigure(1, weight=1) # Coluna 1 (Main) expande na largura; Coluna 0 (Sidebar) fica fixa

        # 3. Construção da Sidebar (Menu Lateral)
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(5, weight=1) # Espaçador invisível empurra o fundo

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="Wealth.Core", font=ctk.CTkFont(size=22, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 30))

        # Botões de Navegação com injeção de função Lambda para Roteamento
        self.btn_nav_dash = ctk.CTkButton(self.sidebar_frame, text="Visão Geral", command=lambda: self.rotear_tela("dash"))
        self.btn_nav_dash.grid(row=1, column=0, padx=20, pady=10)

        self.btn_nav_orcamento = ctk.CTkButton(self.sidebar_frame, text="Orçamentos", command=lambda: self.rotear_tela("orcamento"))
        self.btn_nav_orcamento.grid(row=2, column=0, padx=20, pady=10)

        self.btn_nav_invest = ctk.CTkButton(self.sidebar_frame, text="Investimentos", command=lambda: self.rotear_tela("invest"))
        self.btn_nav_invest.grid(row=3, column=0, padx=20, pady=10)

        # 4. Construção da Área Principal de Renderização
        self.main_frame = ctk.CTkFrame(self, corner_radius=10)
        self.main_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        
        # 5. Boot Automático: Injeta a primeira tela
        self.rotear_tela("dash")

    def rotear_tela(self, tela_destino):
        # Limpeza de Memória Visual: Destrói tudo que estiver dentro do main_frame
        for widget in self.main_frame.winfo_children():
            widget.destroy()
            
        # Motor de Renderização Condicional
      # Motor de Renderização Condicional
     # Motor de Renderização Condicional
        if tela_destino == "dash":
            # 1. TÍTULO
            titulo = ctk.CTkLabel(self.main_frame, text="Visão Geral Financeira", font=ctk.CTkFont(size=24, weight="bold"))
            titulo.pack(pady=20, padx=20, anchor="w")
            
            # 2. EXTRAÇÃO DE DADOS BÁSICOS (CARDS)
            try:
                cursor = self.db_conn.cursor()
                cursor.execute("SELECT nome, tipo FROM tb_contas")
                contas_db = cursor.fetchall()
                
                cursor.execute("SELECT COUNT(*), SUM(valor) FROM tb_transacoes")
                stats_transacoes = cursor.fetchone()
            except Exception as e:
                ctk.CTkLabel(self.main_frame, text=f"Erro de DB: {e}", text_color="red").pack()
                return

            # 3. RENDERIZAÇÃO DOS CARDS
            painel_cards = ctk.CTkFrame(self.main_frame, fg_color="transparent")
            painel_cards.pack(fill="x", padx=20, pady=10)
            painel_cards.grid_columnconfigure((0, 1), weight=1)

            card_contas = ctk.CTkFrame(painel_cards, corner_radius=10)
            card_contas.grid(row=0, column=0, padx=10, sticky="nsew")
            ctk.CTkLabel(card_contas, text="🏦 Suas Contas", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
            if contas_db:
                for nome, tipo in contas_db:
                    ctk.CTkLabel(card_contas, text=f"{nome} ({tipo})").pack(pady=2)
            else:
                ctk.CTkLabel(card_contas, text="Nenhuma conta cadastrada.").pack(pady=2)

            card_extrato = ctk.CTkFrame(painel_cards, corner_radius=10)
            card_extrato.grid(row=0, column=1, padx=10, sticky="nsew")
            ctk.CTkLabel(card_extrato, text="📊 Dados Ingeridos (ETL)", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
            qtd_transacoes = stats_transacoes[0] if stats_transacoes else 0
            volume_movimentado = stats_transacoes[1] if stats_transacoes and stats_transacoes[1] else 0.0
            ctk.CTkLabel(card_extrato, text=f"Transações no Banco: {qtd_transacoes}").pack(pady=2)
            ctk.CTkLabel(card_extrato, text=f"Volume Bruto: R$ {volume_movimentado:.2f}").pack(pady=2)

            # 4. MOTOR DO GRÁFICO (LAZY LOADING)
            self.frame_grafico = ctk.CTkFrame(self.main_frame, fg_color="transparent")
            self.grafico_gerado = False

            def toggle_grafico():
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
                            fig = px.bar(df_grafico, x='tipo_fluxo', y='total', color='tipo_fluxo', title="Fluxo de Caixa Consolidado", color_discrete_map={'RECEITA': '#2ecc71', 'DESPESA': '#e74c3c'}, template="plotly_dark")
                            fig.update_layout(margin=dict(l=20, r=20, t=40, b=20), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=300)
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
            
        elif tela_destino == "orcamento":
            titulo = ctk.CTkLabel(self.main_frame, text="Planejamento e Metas", font=ctk.CTkFont(size=24, weight="bold"))
            titulo.pack(pady=20, padx=20, anchor="w")
            
        elif tela_destino == "invest":
            titulo = ctk.CTkLabel(self.main_frame, text="Wealth Management & Ativos", font=ctk.CTkFont(size=24, weight="bold"))
            titulo.pack(pady=20, padx=20, anchor="w")

if __name__ == "__main__":
    app = PlataformaFinanceira()
    app.mainloop()
