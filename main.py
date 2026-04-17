# main.py
import customtkinter as ctk
from customtkinter import filedialog
import pandas as pd
from datetime import datetime
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.patches import FancyBboxPatch
import numpy as np

from config import *
from engine import SecurityManager, DatabaseManager, MasterManager

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ─── Paleta matplotlib ────────────────────────────────────────────────────────
MPL_BG      = "#111113"
MPL_CARD    = "#1C1C1E"
MPL_TEXTO   = "#8E8E93"
MPL_BRANCO  = "#FFFFFF"
MPL_AZUL    = "#0A84FF"
MPL_VERDE   = "#30D158"
MPL_VERMELHO = "#FF453A"
MPL_ROXO    = "#BF5AF2"


# ─────────────────────────────────────────────────────────────────────────────
#  COMPONENTES REUTILIZÁVEIS
# ─────────────────────────────────────────────────────────────────────────────

class Card(ctk.CTkFrame):
    """Card iOS com label topo, valor grande e subtítulo."""
    def __init__(self, master, title: str, value: str, sub: str,
                 color=None, command=None, icon: str = "", **kwargs):
        super().__init__(
            master,
            fg_color=COR_CARD,
            corner_radius=20,
            border_width=1,
            border_color=COR_BORDAS,
            cursor="hand2" if command else "",
            **kwargs,
        )
        color = color or COR_TEXTO_FORTE

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=20, pady=(16, 0))

        if icon:
            ctk.CTkLabel(top, text=icon, font=("SF Pro Display", 18), text_color=color).pack(side="left")

        ctk.CTkLabel(top, text=title, font=FONT_SMALL, text_color=COR_TEXTO).pack(side="left", padx=(6, 0))

        ctk.CTkLabel(self, text=value, font=("SF Pro Display", 24, "bold"),
                     text_color=color).pack(anchor="w", padx=20, pady=(4, 2))
        ctk.CTkLabel(self, text=sub, font=FONT_SMALL,
                     text_color=COR_TEXTO).pack(anchor="w", padx=20, pady=(0, 16))

        if command:
            for w in self.winfo_children():
                w.bind("<Button-1>", lambda e: command())
                self.bind("<Button-1>", lambda e: command())


class Divider(ctk.CTkFrame):
    def __init__(self, master, **kw):
        super().__init__(master, height=1, fg_color=COR_BORDAS, **kw)


class SectionTitle(ctk.CTkLabel):
    def __init__(self, master, text, **kw):
        super().__init__(master, text=text, font=FONT_TITLE,
                         text_color=COR_TEXTO_FORTE, **kw)


class NavButton(ctk.CTkButton):
    def __init__(self, master, text, icon, tag, active=False, command=None, **kw):
        clr = COR_ATIVO if active else "transparent"
        txt = COR_TEXTO_FORTE if active else COR_TEXTO
        super().__init__(
            master,
            text=f"  {icon}  {text}",
            fg_color=clr,
            text_color=txt,
            hover_color=COR_ATIVO,
            anchor="w",
            font=FONT_REGULAR,
            height=44,
            corner_radius=12,
            command=command,
            **kw,
        )


# ─────────────────────────────────────────────────────────────────────────────
#  GRÁFICO MATPLOTLIB EMBEDADO
# ─────────────────────────────────────────────────────────────────────────────

def criar_grafico_barras(parent, dados: list, width_px=860, height_px=300):
    """
    dados: [(label, receita, despesa), ...]
    Retorna o widget tkinter do canvas.
    """
    fig, ax = plt.subplots(figsize=(width_px / 100, height_px / 100), dpi=100)
    fig.patch.set_facecolor(MPL_BG)
    ax.set_facecolor(MPL_BG)

    if not dados:
        ax.text(0.5, 0.5, "Sem dados de transações ainda.",
                ha="center", va="center", color=MPL_TEXTO,
                fontsize=13, transform=ax.transAxes)
        ax.axis("off")
    else:
        labels = [d[0] for d in dados]
        receitas = np.array([float(d[1] or 0) for d in dados])
        despesas = np.array([float(d[2] or 0) for d in dados])

        x = np.arange(len(labels))
        w = 0.35

        bars_r = ax.bar(x - w / 2, receitas, w,
                        color=MPL_VERDE, alpha=0.85,
                        zorder=3, label="Receitas")
        bars_d = ax.bar(x + w / 2, despesas, w,
                        color=MPL_VERMELHO, alpha=0.85,
                        zorder=3, label="Despesas")

        # Arredondar topo das barras (visual)
        for bar in [*bars_r, *bars_d]:
            bar.set_linewidth(0)

        # Hover tooltip simples via annotation
        annot = ax.annotate("", xy=(0, 0), xytext=(0, 10),
                            textcoords="offset points",
                            fontsize=10, color=MPL_BRANCO,
                            bbox=dict(boxstyle="round,pad=0.4",
                                      fc=MPL_CARD, ec="#3A3A3C", lw=1),
                            ha="center")
        annot.set_visible(False)

        all_bars = list(bars_r) + list(bars_d)
        all_vals = list(receitas) + list(despesas)

        def on_hover(event):
            vis = annot.get_visible()
            if event.inaxes == ax:
                for i, (bar, val) in enumerate(zip(all_bars, all_vals)):
                    cont, _ = bar.contains(event)
                    if cont:
                        x_b = bar.get_x() + bar.get_width() / 2
                        y_b = bar.get_height()
                        annot.xy = (x_b, y_b)
                        annot.set_text(f"R$ {val:,.2f}")
                        annot.set_visible(True)
                        fig.canvas.draw_idle()
                        return
                if vis:
                    annot.set_visible(False)
                    fig.canvas.draw_idle()

        fig.canvas.mpl_connect("motion_notify_event", on_hover)

        ax.set_xticks(x)
        ax.set_xticklabels(labels, color=MPL_TEXTO, fontsize=11)
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(
            lambda v, _: f"R$ {v:,.0f}"))
        ax.tick_params(colors=MPL_TEXTO, which="both", length=0)
        ax.spines[["top", "right", "left", "bottom"]].set_visible(False)
        ax.yaxis.label.set_color(MPL_TEXTO)
        ax.grid(axis="y", color="#2C2C2E", linewidth=0.8, linestyle="--", zorder=0)
        ax.legend(facecolor=MPL_CARD, edgecolor="#3A3A3C",
                  labelcolor=MPL_BRANCO, fontsize=10)

    plt.tight_layout(pad=1.2)

    canvas = FigureCanvasTkAgg(fig, master=parent)
    canvas.draw()
    widget = canvas.get_tk_widget()
    widget.configure(bg=MPL_BG)
    return widget


def criar_grafico_pizza(parent, receitas: float, despesas: float,
                         width_px=320, height_px=300):
    fig, ax = plt.subplots(figsize=(width_px / 100, height_px / 100), dpi=100)
    fig.patch.set_facecolor(MPL_BG)
    ax.set_facecolor(MPL_BG)

    total = receitas + despesas
    if total <= 0:
        ax.text(0.5, 0.5, "Sem dados", ha="center", va="center",
                color=MPL_TEXTO, fontsize=12, transform=ax.transAxes)
        ax.axis("off")
    else:
        sizes  = [receitas, despesas]
        colors = [MPL_VERDE, MPL_VERMELHO]
        wedges, texts, autotexts = ax.pie(
            sizes, colors=colors, startangle=90,
            wedgeprops=dict(width=0.6, edgecolor=MPL_BG, linewidth=3),
            autopct="%1.0f%%", pctdistance=0.75,
        )
        for at in autotexts:
            at.set_color(MPL_BRANCO)
            at.set_fontsize(11)
            at.set_fontweight("bold")
        ax.legend(["Receitas", "Despesas"],
                  facecolor=MPL_CARD, edgecolor="#3A3A3C",
                  labelcolor=MPL_BRANCO, fontsize=9, loc="lower center")

    plt.tight_layout(pad=0.5)
    canvas = FigureCanvasTkAgg(fig, master=parent)
    canvas.draw()
    w = canvas.get_tk_widget()
    w.configure(bg=MPL_BG)
    return w


# ─────────────────────────────────────────────────────────────────────────────
#  APLICAÇÃO PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

class WealthEngine(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Wealth Engine")
        self.geometry("1280x820")
        self.minsize(1100, 700)
        self.configure(fg_color=COR_FUNDO)

        self.db: DatabaseManager | None = None
        self.usuario_atual: str | None  = None
        self.master_db = MasterManager()
        self._tela_ativa = "dash"

        self._tela_login()

    # ── utilitários ──────────────────────────────────────────────────────────

    def _limpar(self):
        for w in self.winfo_children():
            w.destroy()

    def _toast(self, label: ctk.CTkLabel, msg: str, color=COR_RECEITA, delay=3000):
        label.configure(text=msg, text_color=color)
        self.after(delay, lambda: label.configure(text=""))

    # ── AUTENTICAÇÃO ─────────────────────────────────────────────────────────

    def _tela_login(self):
        self._limpar()
        self.db = None

        wrapper = ctk.CTkFrame(self, fg_color="transparent")
        wrapper.place(relx=0.5, rely=0.5, anchor="center")

        # Logo / título
        ctk.CTkLabel(wrapper, text="💰", font=("SF Pro Display", 52)).pack()
        ctk.CTkLabel(wrapper, text="Wealth Engine",
                     font=("SF Pro Display", 32, "bold"),
                     text_color=COR_TEXTO_FORTE).pack(pady=(4, 2))
        ctk.CTkLabel(wrapper, text="Seu cofre financeiro pessoal",
                     font=FONT_SMALL, text_color=COR_TEXTO).pack(pady=(0, 30))

        card = ctk.CTkFrame(wrapper, fg_color=COR_CARD, corner_radius=24,
                            border_width=1, border_color=COR_BORDAS)
        card.pack(ipadx=40, ipady=30)

        self._ent_user = ctk.CTkEntry(card, placeholder_text="Usuário",
                                      width=320, height=48, corner_radius=14,
                                      font=FONT_REGULAR)
        self._ent_user.pack(pady=(30, 10), padx=40)

        self._ent_pass = ctk.CTkEntry(card, placeholder_text="Senha Master",
                                      show="•", width=320, height=48,
                                      corner_radius=14, font=FONT_REGULAR)
        self._ent_pass.pack(pady=(0, 20), padx=40)
        self._ent_pass.bind("<Return>", lambda e: self._autenticar())

        ctk.CTkButton(card, text="Acessar Cofre", fg_color=COR_PRIMARIA,
                      width=320, height=48, corner_radius=14, font=FONT_BOLD,
                      command=self._autenticar).pack(pady=(0, 12), padx=40)

        ctk.CTkButton(card, text="Criar Nova Conta",
                      fg_color="transparent", text_color=COR_PRIMARIA,
                      hover_color=COR_CARD, width=320, height=40,
                      command=self._tela_registro).pack(padx=40)

        self._lbl_login_status = ctk.CTkLabel(
            card, text=f"Contas no dispositivo: {self.master_db.contar_usuarios()}/3",
            font=FONT_SMALL, text_color=COR_TEXTO)
        self._lbl_login_status.pack(pady=(12, 20))

    def _tela_registro(self):
        self._limpar()

        wrapper = ctk.CTkFrame(self, fg_color="transparent")
        wrapper.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(wrapper, text="🔐", font=("SF Pro Display", 48)).pack()
        ctk.CTkLabel(wrapper, text="Criar Conta Blindada",
                     font=("SF Pro Display", 28, "bold")).pack(pady=(4, 24))

        card = ctk.CTkFrame(wrapper, fg_color=COR_CARD, corner_radius=24,
                            border_width=1, border_color=COR_BORDAS)
        card.pack(ipadx=40, ipady=20)

        campos = {}
        specs = [
            ("usuario",   "Usuário",                     ""),
            ("senha",     "Senha Master",                "•"),
            ("cpf",       "CPF (apenas números)",        ""),
            ("nascimento","Data de Nascimento DD/MM/AAAA",""),
        ]
        for key, ph, show in specs:
            e = ctk.CTkEntry(card, placeholder_text=ph, width=340, height=46,
                             corner_radius=14, show=show, font=FONT_REGULAR)
            e.pack(pady=6, padx=40)
            campos[key] = e

        self._lbl_reg_status = ctk.CTkLabel(card, text="", font=FONT_SMALL,
                                             text_color=COR_DESPESA)
        self._lbl_reg_status.pack(pady=(8, 0))

        ctk.CTkButton(card, text="Registrar & Criptografar",
                      fg_color=COR_RECEITA, text_color="#000",
                      width=340, height=48, corner_radius=14, font=FONT_BOLD,
                      command=lambda: self._confirmar_registro(campos)).pack(
                          pady=(14, 8), padx=40)
        ctk.CTkButton(card, text="Voltar ao Login",
                      fg_color="transparent", text_color=COR_TEXTO,
                      hover_color=COR_CARD, width=340, height=38,
                      command=self._tela_login).pack(padx=40, pady=(0, 20))

    def _confirmar_registro(self, campos: dict):
        u = campos["usuario"].get().strip()
        p = campos["senha"].get()
        c = campos["cpf"].get().strip()
        n = campos["nascimento"].get().strip()

        if not all([u, p, c, n]):
            self._lbl_reg_status.configure(text="⚠ Preencha todos os campos.")
            return
        try:
            salt  = SecurityManager.gerar_salt()
            self.master_db.registrar_usuario(u, salt)
            chave = SecurityManager.derivar_chave(p, salt)
            tmp   = DatabaseManager(f"vault_{u.lower()}.db", chave)
            with tmp.transacao() as cur:
                cur.execute(
                    "INSERT OR REPLACE INTO tb_perfil (id, cpf, data_nascimento) VALUES (1,?,?)",
                    (c, n)
                )
            self._tela_login()
        except Exception as exc:
            self._lbl_reg_status.configure(text=f"⚠ {exc}")

    def _autenticar(self):
        user = self._ent_user.get().strip()
        pw   = self._ent_pass.get()
        if not user or not pw:
            return
        salt = self.master_db.obter_salt(user)
        if not salt:
            self._lbl_login_status.configure(
                text="⚠ Usuário não encontrado.", text_color=COR_DESPESA)
            return
        try:
            self.db = DatabaseManager(
                f"vault_{user.lower()}.db",
                SecurityManager.derivar_chave(pw, salt)
            )
            # Testa leitura para confirmar senha correta
            self.db.resumo_financeiro()
            self.usuario_atual = user
            self._limpar()
            self._setup_main_ui()
        except Exception:
            self._lbl_login_status.configure(
                text="⚠ Senha incorreta ou cofre corrompido.",
                text_color=COR_DESPESA)

    # ── ESTRUTURA PRINCIPAL ───────────────────────────────────────────────────

    def _setup_main_ui(self):
        # Sidebar fixa
        self._sidebar = ctk.CTkFrame(self, width=230, fg_color=COR_SIDEBAR,
                                     corner_radius=0)
        self._sidebar.pack(side="left", fill="y")
        self._sidebar.pack_propagate(False)

        # Área de conteúdo
        self._content_area = ctk.CTkFrame(self, fg_color=COR_FUNDO,
                                          corner_radius=0)
        self._content_area.pack(side="right", fill="both", expand=True)

        self._build_sidebar()
        self._navegar("dash")

    def _build_sidebar(self, ativo="dash"):
        for w in self._sidebar.winfo_children():
            w.destroy()

        # Logo
        logo_frame = ctk.CTkFrame(self._sidebar, fg_color="transparent")
        logo_frame.pack(fill="x", padx=20, pady=(32, 24))
        ctk.CTkLabel(logo_frame, text="💰", font=("SF Pro Display", 28)).pack(side="left")
        ctk.CTkLabel(logo_frame, text="Wealth",
                     font=("SF Pro Display", 20, "bold"),
                     text_color=COR_TEXTO_FORTE).pack(side="left", padx=8)

        Divider(self._sidebar).pack(fill="x", padx=16, pady=(0, 16))

        nav_items = [
            ("Visão Geral",  "📊", "dash"),
            ("Bancos",       "🏦", "bancos"),
            ("Transações",   "💸", "trans"),
            ("Assinaturas",  "🔁", "assinaturas"),
            ("Planejamento", "🎯", "plan"),
        ]
        for label, icon, tag in nav_items:
            btn = NavButton(
                self._sidebar, label, icon, tag,
                active=(tag == ativo),
                command=lambda t=tag: self._navegar(t),
            )
            btn.pack(fill="x", padx=12, pady=3)

        # Footer sidebar
        ctk.CTkFrame(self._sidebar, fg_color="transparent").pack(
            fill="both", expand=True)

        Divider(self._sidebar).pack(fill="x", padx=16, pady=8)
        ctk.CTkLabel(self._sidebar,
                     text=f"👤  {self.usuario_atual}",
                     font=FONT_SMALL, text_color=COR_TEXTO).pack(
                         anchor="w", padx=20, pady=(0, 8))
        ctk.CTkButton(
            self._sidebar, text="  🔒  Trancar Cofre",
            fg_color="transparent", text_color=COR_DESPESA,
            hover_color="#1A0A0A", anchor="w", height=40, font=FONT_SMALL,
            command=self._tela_login,
        ).pack(fill="x", padx=12, pady=(0, 24))

    def _navegar(self, tela: str):
        self._tela_ativa = tela
        self._build_sidebar(ativo=tela)
        for w in self._content_area.winfo_children():
            w.destroy()

        scroll = ctk.CTkScrollableFrame(
            self._content_area, fg_color="transparent",
            scrollbar_button_color=COR_BORDAS)
        scroll.pack(fill="both", expand=True, padx=0, pady=0)

        dispatch = {
            "dash":        self._render_dashboard,
            "bancos":      self._render_bancos,
            "trans":       self._render_transacoes,
            "assinaturas": self._render_assinaturas,
            "plan":        self._render_planejamento,
        }
        dispatch.get(tela, self._render_dashboard)(scroll)

    # ── DASHBOARD ─────────────────────────────────────────────────────────────

    def _render_dashboard(self, parent):
        pad = dict(padx=36, pady=8)

        ctk.CTkLabel(parent, text="Visão Geral",
                     font=("SF Pro Display", 28, "bold"),
                     text_color=COR_TEXTO_FORTE).pack(anchor="w", padx=36, pady=(32, 4))

        now_str = datetime.now().strftime("%A, %d de %B de %Y")
        ctk.CTkLabel(parent, text=now_str,
                     font=FONT_SMALL, text_color=COR_TEXTO).pack(anchor="w", padx=36, pady=(0, 20))

        resumo = self.db.resumo_financeiro()

        # KPI cards
        kpi = ctk.CTkFrame(parent, fg_color="transparent")
        kpi.pack(fill="x", **pad)
        kpi.columnconfigure((0, 1, 2), weight=1, uniform="kpi")

        def fmt(v): return f"R$ {v:,.2f}"

        cards_data = [
            ("Patrimônio Líquido", fmt(resumo["patrimonio"]),
             "receitas − despesas",
             COR_PRIMARIA, "💼", "trans"),
            ("Total de Entradas", fmt(resumo["receitas"]),
             "receitas acumuladas",
             COR_RECEITA, "📈", "trans"),
            ("Total de Saídas", fmt(resumo["despesas"]),
             "despesas + assinaturas",
             COR_DESPESA, "📉", "trans"),
        ]
        for col, (title, value, sub, color, icon, tela) in enumerate(cards_data):
            c = Card(kpi, title, value, sub, color=color, icon=icon,
                     command=lambda t=tela: self._navegar(t))
            c.grid(row=0, column=col, sticky="nsew",
                   padx=6, pady=4)

        # Gráfico de barras (histórico mensal)
        ctk.CTkLabel(parent, text="Histórico Mensal",
                     font=FONT_BOLD,
                     text_color=COR_TEXTO_FORTE).pack(anchor="w", padx=36, pady=(28, 8))

        graph_outer = ctk.CTkFrame(parent, fg_color=MPL_BG, corner_radius=20,
                                   border_width=1, border_color=COR_BORDAS)
        graph_outer.pack(fill="x", padx=36, pady=(0, 16))

        dados = self.db.transacoes_por_mes()
        g = criar_grafico_barras(graph_outer, dados, width_px=820, height_px=280)
        g.pack(padx=12, pady=12)

        # Pizza + Assinaturas side-by-side
        row2 = ctk.CTkFrame(parent, fg_color="transparent")
        row2.pack(fill="x", padx=36, pady=8)
        row2.columnconfigure(0, weight=1)
        row2.columnconfigure(1, weight=1)

        pizza_frame = ctk.CTkFrame(row2, fg_color=MPL_BG, corner_radius=20,
                                   border_width=1, border_color=COR_BORDAS)
        pizza_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        ctk.CTkLabel(pizza_frame, text="Distribuição",
                     font=FONT_BOLD, text_color=COR_TEXTO_FORTE).pack(
                         anchor="w", padx=16, pady=(14, 0))
        pg = criar_grafico_pizza(
            pizza_frame, resumo["receitas"], resumo["despesas"],
            width_px=340, height_px=240)
        pg.pack(padx=12, pady=(0, 12))

        # Mini painel assinaturas
        ass_frame = ctk.CTkFrame(row2, fg_color=COR_CARD, corner_radius=20,
                                 border_width=1, border_color=COR_BORDAS)
        ass_frame.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        ctk.CTkLabel(ass_frame, text="🔁  Assinaturas Ativas",
                     font=FONT_BOLD, text_color=COR_TEXTO_FORTE).pack(
                         anchor="w", padx=20, pady=(16, 8))

        assinaturas = self.db.listar_assinaturas()
        ativas = [a for a in assinaturas if a[4] == "ATIVA"]
        if not ativas:
            ctk.CTkLabel(ass_frame, text="Nenhuma assinatura ativa.",
                         font=FONT_SMALL, text_color=COR_TEXTO).pack(pady=40)
        else:
            for a in ativas[:6]:
                row = ctk.CTkFrame(ass_frame, fg_color="transparent")
                row.pack(fill="x", padx=20, pady=3)
                ctk.CTkLabel(row, text=a[1],
                             font=FONT_REGULAR, text_color=COR_TEXTO_FORTE).pack(side="left")
                ctk.CTkLabel(row, text=f"R$ {a[2]:.2f}",
                             font=FONT_CAPTION, text_color=COR_ROXO).pack(side="right")

        total_ass = resumo["assinaturas"]
        Divider(ass_frame).pack(fill="x", padx=20, pady=8)
        total_row = ctk.CTkFrame(ass_frame, fg_color="transparent")
        total_row.pack(fill="x", padx=20, pady=(0, 16))
        ctk.CTkLabel(total_row, text="Total / mês",
                     font=FONT_SMALL, text_color=COR_TEXTO).pack(side="left")
        ctk.CTkLabel(total_row, text=f"R$ {total_ass:,.2f}",
                     font=FONT_BOLD, text_color=COR_DESPESA).pack(side="right")

    # ── BANCOS ────────────────────────────────────────────────────────────────

    def _render_bancos(self, parent):
        ctk.CTkLabel(parent, text="Contas Bancárias",
                     font=("SF Pro Display", 28, "bold"),
                     text_color=COR_TEXTO_FORTE).pack(anchor="w", padx=36, pady=(32, 20))

        # Formulário de cadastro
        form = ctk.CTkFrame(parent, fg_color=COR_CARD, corner_radius=20,
                            border_width=1, border_color=COR_BORDAS)
        form.pack(fill="x", padx=36, pady=(0, 24))

        ctk.CTkLabel(form, text="Adicionar Conta",
                     font=FONT_BOLD, text_color=COR_TEXTO_FORTE).pack(
                         anchor="w", padx=24, pady=(20, 12))

        fields_row = ctk.CTkFrame(form, fg_color="transparent")
        fields_row.pack(fill="x", padx=24, pady=(0, 16))

        ent_nome = ctk.CTkEntry(fields_row, placeholder_text="Nome do banco ou conta",
                                height=46, corner_radius=14, font=FONT_REGULAR)
        ent_nome.pack(side="left", fill="x", expand=True, padx=(0, 12))

        opt_tipo = ctk.CTkOptionMenu(fields_row,
                                     values=["Corrente", "Poupança", "Investimentos", "Digital"],
                                     height=46, corner_radius=14, font=FONT_REGULAR,
                                     fg_color=COR_BORDAS, button_color=COR_PRIMARIA,
                                     width=180)
        opt_tipo.pack(side="left", padx=(0, 12))

        lbl_banco_status = ctk.CTkLabel(form, text="", font=FONT_SMALL)
        lbl_banco_status.pack()

        def salvar_banco():
            nome = ent_nome.get().strip()
            if not nome:
                self._toast(lbl_banco_status, "⚠ Informe o nome do banco.", COR_DESPESA)
                return
            with self.db.transacao() as c:
                c.execute("INSERT INTO tb_contas (nome, tipo) VALUES (?,?)",
                          (nome, opt_tipo.get()))
            ent_nome.delete(0, "end")
            self._toast(lbl_banco_status, "✓ Conta registrada!", COR_RECEITA)
            _refresh_lista()

        ctk.CTkButton(fields_row, text="Registrar", fg_color=COR_PRIMARIA,
                      height=46, corner_radius=14, font=FONT_BOLD,
                      width=130, command=salvar_banco).pack(side="left")

        lbl_banco_status.pack(anchor="w", padx=24, pady=(0, 16))

        # Lista de bancos
        lista_wrapper = ctk.CTkFrame(parent, fg_color="transparent")
        lista_wrapper.pack(fill="x", padx=36)

        def _refresh_lista():
            for w in lista_wrapper.winfo_children():
                w.destroy()

            contas = self.db.listar_contas()
            icon_map = {"Corrente": "🏦", "Poupança": "💰",
                        "Investimentos": "📈", "Digital": "📱"}

            for cid, nome, tipo in contas:
                row = ctk.CTkFrame(lista_wrapper, fg_color=COR_CARD,
                                   corner_radius=16, border_width=1,
                                   border_color=COR_BORDAS)
                row.pack(fill="x", pady=5)

                icone = icon_map.get(tipo, "💳")
                left = ctk.CTkFrame(row, fg_color="transparent")
                left.pack(side="left", padx=20, pady=16)
                ctk.CTkLabel(left, text=icone,
                             font=("SF Pro Display", 22)).pack(side="left")
                info = ctk.CTkFrame(left, fg_color="transparent")
                info.pack(side="left", padx=12)
                ctk.CTkLabel(info, text=nome,
                             font=FONT_BOLD, text_color=COR_TEXTO_FORTE).pack(anchor="w")
                ctk.CTkLabel(info, text=tipo,
                             font=FONT_SMALL, text_color=COR_TEXTO).pack(anchor="w")

        _refresh_lista()

    # ── TRANSAÇÕES ────────────────────────────────────────────────────────────

    def _render_transacoes(self, parent):
        ctk.CTkLabel(parent, text="Transações & Extratos",
                     font=("SF Pro Display", 28, "bold"),
                     text_color=COR_TEXTO_FORTE).pack(anchor="w", padx=36, pady=(32, 20))

        # Box importação CSV
        box_csv = ctk.CTkFrame(parent, fg_color=COR_CARD, corner_radius=20,
                               border_width=1, border_color=COR_BORDAS)
        box_csv.pack(fill="x", padx=36, pady=(0, 24))

        csv_inner = ctk.CTkFrame(box_csv, fg_color="transparent")
        csv_inner.pack(fill="x", padx=24, pady=20)

        left_csv = ctk.CTkFrame(csv_inner, fg_color="transparent")
        left_csv.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(left_csv, text="📂  Importar Extrato Bancário (.csv)",
                     font=FONT_BOLD, text_color=COR_TEXTO_FORTE).pack(anchor="w")
        ctk.CTkLabel(left_csv,
                     text="O arquivo deve ter colunas contendo: data, descrição e valor.",
                     font=FONT_SMALL, text_color=COR_TEXTO).pack(anchor="w", pady=(4, 0))

        self._lbl_csv = ctk.CTkLabel(csv_inner, text="", font=FONT_SMALL)
        self._lbl_csv.pack(side="right", padx=16)

        ctk.CTkButton(csv_inner, text="Selecionar Arquivo CSV",
                      fg_color=COR_PRIMARIA, height=44, corner_radius=14,
                      font=FONT_BOLD, command=lambda: self._importar_csv(parent)).pack(side="right")

        # Filtros
        filtro_frame = ctk.CTkFrame(parent, fg_color=COR_CARD, corner_radius=20,
                                    border_width=1, border_color=COR_BORDAS)
        filtro_frame.pack(fill="x", padx=36, pady=(0, 16))

        ctk.CTkLabel(filtro_frame, text="Filtros",
                     font=FONT_BOLD, text_color=COR_TEXTO_FORTE).pack(
                         anchor="w", padx=24, pady=(16, 8))

        filtros_row = ctk.CTkFrame(filtro_frame, fg_color="transparent")
        filtros_row.pack(fill="x", padx=24, pady=(0, 16))

        contas = self.db.listar_contas()
        nomes_contas = ["Todas as contas"] + [c[1] for c in contas]
        ids_contas   = [None] + [c[0] for c in contas]

        cmb_conta = ctk.CTkComboBox(filtros_row, values=nomes_contas,
                                    width=200, height=40, corner_radius=12,
                                    font=FONT_REGULAR,
                                    button_color=COR_PRIMARIA)
        cmb_conta.pack(side="left", padx=(0, 12))

        cmb_tipo = ctk.CTkComboBox(filtros_row,
                                   values=["Todos", "RECEITA", "DESPESA"],
                                   width=160, height=40, corner_radius=12,
                                   font=FONT_REGULAR,
                                   button_color=COR_PRIMARIA)
        cmb_tipo.pack(side="left", padx=(0, 12))

        ent_data_ini = ctk.CTkEntry(filtros_row, placeholder_text="Início YYYY-MM-DD",
                                    width=180, height=40, corner_radius=12,
                                    font=FONT_REGULAR)
        ent_data_ini.pack(side="left", padx=(0, 12))

        ent_data_fim = ctk.CTkEntry(filtros_row, placeholder_text="Fim YYYY-MM-DD",
                                    width=180, height=40, corner_radius=12,
                                    font=FONT_REGULAR)
        ent_data_fim.pack(side="left", padx=(0, 12))

        ctk.CTkButton(filtros_row, text="Filtrar",
                      fg_color=COR_PRIMARIA, height=40, corner_radius=12,
                      font=FONT_BOLD, width=100,
                      command=lambda: _refresh_lista()).pack(side="left")

        ctk.CTkButton(filtros_row, text="Limpar",
                      fg_color="transparent", text_color=COR_TEXTO,
                      hover_color=COR_CARD, height=40, corner_radius=12,
                      font=FONT_SMALL, width=80,
                      command=lambda: [
                          cmb_conta.set(nomes_contas[0]),
                          cmb_tipo.set("Todos"),
                          ent_data_ini.delete(0, "end"),
                          ent_data_fim.delete(0, "end"),
                          _refresh_lista(),
                      ]).pack(side="left")

        # Tabela de transações
        box_lista = ctk.CTkFrame(parent, fg_color=COR_CARD, corner_radius=20,
                                 border_width=1, border_color=COR_BORDAS)
        box_lista.pack(fill="both", expand=True, padx=36, pady=(0, 32))

        # Cabeçalho da tabela
        header = ctk.CTkFrame(box_lista, fg_color=COR_BORDAS, corner_radius=0,
                              height=40)
        header.pack(fill="x", padx=0, pady=(0, 0))
        for txt, w_ in [("Data", 120), ("Descrição", 300),
                          ("Conta", 160), ("Tipo", 100), ("Valor", 120)]:
            ctk.CTkLabel(header, text=txt, font=FONT_CAPTION,
                         text_color=COR_TEXTO, width=w_).pack(
                             side="left", padx=8, pady=8)

        lista_inner = ctk.CTkScrollableFrame(box_lista, fg_color="transparent",
                                             height=420)
        lista_inner.pack(fill="both", expand=True)

        def _refresh_lista():
            for w in lista_inner.winfo_children():
                w.destroy()

            idx_conta = nomes_contas.index(cmb_conta.get())
            cid = ids_contas[idx_conta]
            tipo_sel = cmb_tipo.get()
            tipo = None if tipo_sel == "Todos" else tipo_sel
            di = ent_data_ini.get().strip() or None
            df_ = ent_data_fim.get().strip() or None

            rows = self.db.listar_transacoes(
                conta_id=cid, tipo=tipo,
                data_inicio=di, data_fim=df_)

            if not rows:
                ctk.CTkLabel(lista_inner,
                             text="Nenhuma transação encontrada.",
                             font=FONT_SMALL,
                             text_color=COR_TEXTO).pack(pady=40)
                return

            for data, desc, valor, conta_nome, cat_nome in rows:
                cor_val = COR_RECEITA if valor >= 0 else COR_DESPESA
                sinal   = "+" if valor >= 0 else ""
                row_f   = ctk.CTkFrame(lista_inner, fg_color="transparent",
                                       height=44)
                row_f.pack(fill="x", padx=8)
                row_f.pack_propagate(False)

                ctk.CTkLabel(row_f, text=str(data)[:10],
                             font=FONT_CAPTION, text_color=COR_TEXTO,
                             width=120).pack(side="left", padx=8)
                ctk.CTkLabel(row_f,
                             text=str(desc)[:50] if desc else "—",
                             font=FONT_CAPTION, text_color=COR_TEXTO_FORTE,
                             width=300, anchor="w").pack(side="left", padx=8)
                ctk.CTkLabel(row_f, text=conta_nome,
                             font=FONT_SMALL, text_color=COR_TEXTO,
                             width=160).pack(side="left", padx=8)
                ctk.CTkLabel(row_f, text=cat_nome,
                             font=FONT_SMALL, text_color=COR_TEXTO,
                             width=100).pack(side="left", padx=8)
                ctk.CTkLabel(row_f,
                             text=f"{sinal}R$ {abs(valor):,.2f}",
                             font=FONT_BOLD, text_color=cor_val,
                             width=120).pack(side="left", padx=8)

                Divider(lista_inner).pack(fill="x", padx=8)

        _refresh_lista()

    def _importar_csv(self, parent):
        caminho = filedialog.askopenfilename(
            title="Selecione o extrato",
            filetypes=[("CSV", "*.csv"), ("Todos", "*.*")]
        )
        if not caminho:
            return
        try:
            # Tentativas com diferentes separadores
            for sep in [",", ";", "\t"]:
                try:
                    df = pd.read_csv(caminho, sep=sep, encoding="utf-8")
                    if len(df.columns) >= 3:
                        break
                except Exception:
                    continue
            else:
                df = pd.read_csv(caminho, encoding="latin-1")

            # Detecção inteligente de colunas
            col_data = next(
                (c for c in df.columns if any(k in c.lower()
                 for k in ["data", "date", "dt"])), df.columns[0])
            col_desc = next(
                (c for c in df.columns if any(k in c.lower()
                 for k in ["desc", "hist", "memo", "narrat"])), df.columns[1])
            col_val  = next(
                (c for c in df.columns if any(k in c.lower()
                 for k in ["valor", "value", "amount", "montant", "quantia"])), df.columns[2])

            inseridos = 0
            with self.db.transacao() as cur:
                for _, row in df.iterrows():
                    raw_val = str(row[col_val]).strip().replace(".", "").replace(",", ".")
                    try:
                        val = float(raw_val)
                    except ValueError:
                        continue
                    cat = 1 if val > 0 else 2
                    cur.execute(
                        """INSERT INTO tb_transacoes
                           (conta_id, categoria_id, valor, data_transacao, descricao)
                           VALUES (1, ?, ?, ?, ?)""",
                        (cat, val, str(row[col_data]), str(row[col_desc]))
                    )
                    inseridos += 1

            self._toast(self._lbl_csv,
                        f"✓ {inseridos} transações importadas!",
                        COR_RECEITA, delay=5000)
            self._navegar("trans")
        except Exception as exc:
            self._toast(self._lbl_csv, f"⚠ Erro: {exc}", COR_DESPESA, delay=8000)

    # ── ASSINATURAS ───────────────────────────────────────────────────────────

    def _render_assinaturas(self, parent):
        ctk.CTkLabel(parent, text="Assinaturas Fixas",
                     font=("SF Pro Display", 28, "bold"),
                     text_color=COR_TEXTO_FORTE).pack(anchor="w", padx=36, pady=(32, 20))

        form = ctk.CTkFrame(parent, fg_color=COR_CARD, corner_radius=20,
                            border_width=1, border_color=COR_BORDAS)
        form.pack(fill="x", padx=36, pady=(0, 24))

        ctk.CTkLabel(form, text="Nova Assinatura",
                     font=FONT_BOLD, text_color=COR_TEXTO_FORTE).pack(
                         anchor="w", padx=24, pady=(20, 12))

        row_f = ctk.CTkFrame(form, fg_color="transparent")
        row_f.pack(fill="x", padx=24, pady=(0, 12))

        ent_nome_a = ctk.CTkEntry(row_f, placeholder_text="Serviço (ex: Netflix)",
                                  height=46, corner_radius=14, font=FONT_REGULAR)
        ent_nome_a.pack(side="left", fill="x", expand=True, padx=(0, 12))

        ent_val_a = ctk.CTkEntry(row_f, placeholder_text="Valor R$",
                                 height=46, corner_radius=14, font=FONT_REGULAR,
                                 width=140)
        ent_val_a.pack(side="left", padx=(0, 12))

        ent_dia_a = ctk.CTkEntry(row_f, placeholder_text="Dia venc.",
                                 height=46, corner_radius=14, font=FONT_REGULAR,
                                 width=110)
        ent_dia_a.pack(side="left", padx=(0, 12))

        lbl_ass_status = ctk.CTkLabel(form, text="", font=FONT_SMALL)
        lbl_ass_status.pack(anchor="w", padx=24, pady=(0, 4))

        def salvar_ass():
            nome = ent_nome_a.get().strip()
            try:
                val  = float(ent_val_a.get().replace(",", "."))
                dia  = int(ent_dia_a.get() or 1)
            except ValueError:
                self._toast(lbl_ass_status, "⚠ Valor ou dia inválido.", COR_DESPESA)
                return
            if not nome:
                self._toast(lbl_ass_status, "⚠ Informe o nome do serviço.", COR_DESPESA)
                return
            with self.db.transacao() as c:
                c.execute(
                    "INSERT INTO tb_assinaturas (nome, valor, dia_vencimento) VALUES (?,?,?)",
                    (nome, val, dia)
                )
            ent_nome_a.delete(0, "end")
            ent_val_a.delete(0, "end")
            ent_dia_a.delete(0, "end")
            self._toast(lbl_ass_status, "✓ Assinatura adicionada!", COR_RECEITA)
            _refresh_ass()

        ctk.CTkButton(row_f, text="Adicionar",
                      fg_color=COR_ROXO, height=46, corner_radius=14,
                      font=FONT_BOLD, width=130,
                      command=salvar_ass).pack(side="left")

        # Lista
        lista_ass_frame = ctk.CTkFrame(parent, fg_color="transparent")
        lista_ass_frame.pack(fill="x", padx=36)

        def _refresh_ass():
            for w in lista_ass_frame.winfo_children():
                w.destroy()

            assinaturas = self.db.listar_assinaturas()
            if not assinaturas:
                ctk.CTkLabel(lista_ass_frame,
                             text="Nenhuma assinatura cadastrada.",
                             font=FONT_SMALL, text_color=COR_TEXTO).pack(pady=30)
                return

            total = 0.0
            for aid, nome, valor, dia, status in assinaturas:
                is_ativa = (status == "ATIVA")
                alfa_cor  = COR_TEXTO_FORTE if is_ativa else COR_TEXTO
                card_ass  = ctk.CTkFrame(lista_ass_frame, fg_color=COR_CARD,
                                         corner_radius=16, border_width=1,
                                         border_color=COR_BORDAS)
                card_ass.pack(fill="x", pady=5)

                left_a = ctk.CTkFrame(card_ass, fg_color="transparent")
                left_a.pack(side="left", padx=20, pady=16, fill="x", expand=True)

                badge_cor = COR_RECEITA if is_ativa else COR_TEXTO
                ctk.CTkLabel(left_a,
                             text="● ATIVA" if is_ativa else "● CANCELADA",
                             font=("SF Pro Display", 10, "bold"),
                             text_color=badge_cor).pack(anchor="w")
                ctk.CTkLabel(left_a, text=nome,
                             font=FONT_BOLD, text_color=alfa_cor).pack(anchor="w")
                ctk.CTkLabel(left_a,
                             text=f"Vence todo dia {dia}",
                             font=FONT_SMALL, text_color=COR_TEXTO).pack(anchor="w")

                right_a = ctk.CTkFrame(card_ass, fg_color="transparent")
                right_a.pack(side="right", padx=20)

                ctk.CTkLabel(right_a, text=f"R$ {valor:,.2f}",
                             font=("SF Pro Display", 20, "bold"),
                             text_color=COR_ROXO).pack(anchor="e")

                if is_ativa:
                    ctk.CTkButton(right_a, text="Cancelar",
                                  fg_color="transparent",
                                  text_color=COR_DESPESA,
                                  hover_color="#1A0808",
                                  height=30, font=FONT_SMALL,
                                  command=lambda i=aid: [
                                      self.db.cancelar_assinatura(i),
                                      _refresh_ass()
                                  ]).pack(anchor="e", pady=(4, 0))

                if is_ativa:
                    total += valor

            # Rodapé total
            Divider(lista_ass_frame).pack(fill="x", pady=8)
            rod = ctk.CTkFrame(lista_ass_frame, fg_color="transparent")
            rod.pack(fill="x", padx=4)
            ctk.CTkLabel(rod, text="Total mensal (ativas):",
                         font=FONT_BOLD, text_color=COR_TEXTO).pack(side="left")
            ctk.CTkLabel(rod, text=f"R$ {total:,.2f}",
                         font=FONT_BOLD, text_color=COR_DESPESA).pack(side="right")

        _refresh_ass()

    # ── PLANEJAMENTO ──────────────────────────────────────────────────────────

    def _render_planejamento(self, parent):
        ctk.CTkLabel(parent, text="Metas & Planejamento",
                     font=("SF Pro Display", 28, "bold"),
                     text_color=COR_TEXTO_FORTE).pack(anchor="w", padx=36, pady=(32, 20))

        form = ctk.CTkFrame(parent, fg_color=COR_CARD, corner_radius=20,
                            border_width=1, border_color=COR_BORDAS)
        form.pack(fill="x", padx=36, pady=(0, 24))

        ctk.CTkLabel(form, text="Novo Objetivo",
                     font=FONT_BOLD, text_color=COR_TEXTO_FORTE).pack(
                         anchor="w", padx=24, pady=(20, 12))

        row_f = ctk.CTkFrame(form, fg_color="transparent")
        row_f.pack(fill="x", padx=24, pady=(0, 12))

        ent_meta_nome = ctk.CTkEntry(row_f, placeholder_text="Nome do objetivo",
                                     height=46, corner_radius=14,
                                     font=FONT_REGULAR)
        ent_meta_nome.pack(side="left", fill="x", expand=True, padx=(0, 12))

        ent_alvo = ctk.CTkEntry(row_f, placeholder_text="Valor Alvo R$",
                                height=46, corner_radius=14,
                                font=FONT_REGULAR, width=160)
        ent_alvo.pack(side="left", padx=(0, 12))

        ent_acumulado = ctk.CTkEntry(row_f, placeholder_text="Guardado R$",
                                     height=46, corner_radius=14,
                                     font=FONT_REGULAR, width=160)
        ent_acumulado.pack(side="left", padx=(0, 12))

        lbl_meta_status = ctk.CTkLabel(form, text="", font=FONT_SMALL)
        lbl_meta_status.pack(anchor="w", padx=24, pady=(0, 4))

        metas_frame = ctk.CTkFrame(parent, fg_color="transparent")
        metas_frame.pack(fill="x", padx=36)
        metas_frame.columnconfigure((0, 1), weight=1, uniform="meta")

        def _refresh_metas():
            for w in metas_frame.winfo_children():
                w.destroy()

            metas = self.db.listar_metas()
            if not metas:
                ctk.CTkLabel(metas_frame,
                             text="Nenhuma meta cadastrada.",
                             font=FONT_SMALL, text_color=COR_TEXTO).pack(pady=30)
                return

            for idx, (mid, nome, acumulado, alvo) in enumerate(metas):
                perc = min(acumulado / alvo, 1.0) if alvo > 0 else 0
                pct_int = int(perc * 100)

                card_m = ctk.CTkFrame(metas_frame, fg_color=COR_CARD,
                                      corner_radius=20, border_width=1,
                                      border_color=COR_BORDAS)
                col = idx % 2
                row_idx = idx // 2
                card_m.grid(row=row_idx, column=col, sticky="nsew",
                            padx=6, pady=6)

                ctk.CTkLabel(card_m, text=nome,
                             font=FONT_BOLD, text_color=COR_TEXTO_FORTE).pack(
                                 anchor="w", padx=20, pady=(20, 4))

                prog_row = ctk.CTkFrame(card_m, fg_color="transparent")
                prog_row.pack(fill="x", padx=20, pady=(0, 8))
                ctk.CTkLabel(prog_row,
                             text=f"R$ {acumulado:,.2f}",
                             font=FONT_REGULAR, text_color=COR_RECEITA).pack(side="left")
                ctk.CTkLabel(prog_row,
                             text=f"/ R$ {alvo:,.2f}",
                             font=FONT_SMALL, text_color=COR_TEXTO).pack(side="left", padx=6)
                ctk.CTkLabel(prog_row,
                             text=f"{pct_int}%",
                             font=FONT_BOLD, text_color=COR_PRIMARIA).pack(side="right")

                barra_cor = COR_RECEITA if perc >= 1.0 else COR_PRIMARIA
                barra = ctk.CTkProgressBar(card_m, progress_color=barra_cor,
                                           fg_color=COR_BORDAS, height=10,
                                           corner_radius=5)
                barra.pack(fill="x", padx=20, pady=(0, 12))
                barra.set(perc)

                # Aportar valor
                aporte_row = ctk.CTkFrame(card_m, fg_color="transparent")
                aporte_row.pack(fill="x", padx=20, pady=(0, 16))
                ent_aporte = ctk.CTkEntry(aporte_row,
                                          placeholder_text="Aportar R$",
                                          height=36, corner_radius=10,
                                          font=FONT_SMALL)
                ent_aporte.pack(side="left", fill="x", expand=True, padx=(0, 8))
                ctk.CTkButton(aporte_row, text="Aportar",
                              fg_color=COR_RECEITA, text_color="#000",
                              height=36, corner_radius=10,
                              font=FONT_SMALL, width=80,
                              command=lambda m=mid, a=acumulado, e=ent_aporte: [
                                  self.db.atualizar_meta(
                                      m,
                                      a + float(e.get().replace(",", ".") or 0)
                                  ),
                                  _refresh_metas()
                              ]).pack(side="left")

        def salvar_meta():
            nome = ent_meta_nome.get().strip()
            try:
                alvo = float(ent_alvo.get().replace(",", "."))
                acu  = float(ent_acumulado.get().replace(",", ".") or 0)
            except ValueError:
                self._toast(lbl_meta_status, "⚠ Valores inválidos.", COR_DESPESA)
                return
            if not nome:
                self._toast(lbl_meta_status, "⚠ Informe um nome.", COR_DESPESA)
                return
            with self.db.transacao() as c:
                c.execute(
                    "INSERT INTO tb_metas (nome, valor_alvo, valor_acumulado) VALUES (?,?,?)",
                    (nome, alvo, acu)
                )
            ent_meta_nome.delete(0, "end")
            ent_alvo.delete(0, "end")
            ent_acumulado.delete(0, "end")
            self._toast(lbl_meta_status, "✓ Objetivo criado!", COR_RECEITA)
            _refresh_metas()

        ctk.CTkButton(row_f, text="Criar Objetivo",
                      fg_color=COR_RECEITA, text_color="#000",
                      height=46, corner_radius=14, font=FONT_BOLD, width=150,
                      command=salvar_meta).pack(side="left")

        _refresh_metas()


# ─────────────────────────────────────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = WealthEngine()
    app.mainloop()
