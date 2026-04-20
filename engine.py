# main.py — Wealth Engine v3.0 (Cyan Tech UI)
import customtkinter as ctk
from customtkinter import filedialog
import pandas as pd
from datetime import datetime
import re
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.dates as mdates
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.collections import PolyCollection
import numpy as np

from config import *
from engine import (
    SecurityManager, DatabaseManager, MasterManager,
    BruteForceGuard, Validador, SQLCIPHER_DISPONIVEL,
)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


# ─────────────────────────────────────────────────────────────────────────────
#  COMPONENTES — Design System
# ─────────────────────────────────────────────────────────────────────────────

class GlowCard(ctk.CTkFrame):
    """Card com borda sutil e glow accent no topo."""
    def __init__(self, master, title="", value="", sub="",
                 accent=None, icon="", command=None, **kw):
        accent = accent or COR_PRIMARIA
        super().__init__(master, fg_color=COR_CARD, corner_radius=RADIUS_CARD,
                         border_width=1, border_color=COR_BORDAS,
                         cursor="hand2" if command else "", **kw)

        # Linha accent no topo do card
        accent_line = ctk.CTkFrame(self, fg_color=accent, height=3,
                                   corner_radius=2)
        accent_line.pack(fill="x", padx=16, pady=(12, 0))

        # Header
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=PAD_CARD, pady=(10, 0))
        if icon:
            ctk.CTkLabel(hdr, text=icon, font=("SF Pro Display", 16),
                         text_color=accent).pack(side="left")
        if title:
            ctk.CTkLabel(hdr, text=title.upper(), font=FONT_TINY,
                         text_color=COR_TEXTO_MUTED).pack(side="left", padx=(8, 0))

        # Valor grande
        if value:
            ctk.CTkLabel(self, text=value, font=FONT_MONO_BIG,
                         text_color=accent).pack(anchor="w", padx=PAD_CARD, pady=(6, 2))
        # Subtítulo
        if sub:
            ctk.CTkLabel(self, text=sub, font=FONT_TINY,
                         text_color=COR_TEXTO_MUTED).pack(anchor="w", padx=PAD_CARD, pady=(0, 14))

        if command:
            self._bind_recursive(self, command)

    def _bind_recursive(self, widget, cmd):
        widget.bind("<Button-1>", lambda e: cmd())
        for child in widget.winfo_children():
            self._bind_recursive(child, cmd)


class Divider(ctk.CTkFrame):
    def __init__(self, master, **kw):
        super().__init__(master, height=1, fg_color=COR_BORDAS, **kw)


class SidebarButton(ctk.CTkButton):
    def __init__(self, master, text, icon, active=False, command=None, **kw):
        bg = COR_ATIVO if active else "transparent"
        txt = COR_PRIMARIA if active else COR_TEXTO
        opts = dict(
            text=f"   {icon}   {text}",
            fg_color=bg, text_color=txt,
            hover_color=COR_ATIVO, anchor="w",
            font=FONT_BOLD if active else FONT_REGULAR,
            height=46, corner_radius=RADIUS_INPUT,
            command=command,
        )
        if active:
            opts["border_width"] = 1
            opts["border_color"] = COR_PRIMARIA
        else:
            opts["border_width"] = 0
        super().__init__(master, **opts, **kw)


# ─────────────────────────────────────────────────────────────────────────────
#  GRÁFICOS MATPLOTLIB — Estilo Tech Premium
# ─────────────────────────────────────────────────────────────────────────────

def _setup_ax(ax, fig):
    """Configuração base para todos os gráficos."""
    fig.patch.set_facecolor(MPL_BG)
    ax.set_facecolor(MPL_BG)
    ax.tick_params(colors=MPL_TEXTO, which="both", length=0, labelsize=10)
    ax.spines[["top", "right", "left", "bottom"]].set_visible(False)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(
        lambda v, _: f"R$ {v:,.0f}"))
    ax.grid(axis="y", color=MPL_GRID, linewidth=0.5, linestyle="--",
            alpha=0.6, zorder=0)


def criar_grafico_evolucao(parent, dados: list, w=820, h=300):
    """Gráfico de área com gradiente — eixo X=data, Y=valor."""
    fig, ax = plt.subplots(figsize=(w / 100, h / 100), dpi=100)
    _setup_ax(ax, fig)

    if not dados:
        ax.text(0.5, 0.5, "Adicione transações para ver a evolução.",
                ha="center", va="center", color=MPL_TEXTO,
                fontsize=13, transform=ax.transAxes, style="italic")
        ax.axis("off")
    else:
        dts, recs, desps = [], [], []
        for d in dados:
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
                try:
                    dt = datetime.strptime(str(d[0]).strip()[:10], fmt)
                    dts.append(dt)
                    recs.append(float(d[1] or 0))
                    desps.append(float(d[2] or 0))
                    break
                except ValueError:
                    continue

        if dts:
            # Receitas — linha + fill gradiente
            ax.plot(dts, recs, color=MPL_CYAN_LIGHT, linewidth=2.5,
                    marker="o", markersize=4, markerfacecolor=MPL_CYAN_LIGHT,
                    markeredgecolor=MPL_BG, markeredgewidth=1.5,
                    label="Receitas", zorder=4, alpha=0.95)
            ax.fill_between(dts, recs, alpha=0.12, color=MPL_CYAN_LIGHT, zorder=2)

            # Despesas — linha + fill gradiente
            ax.plot(dts, desps, color=MPL_ROSE, linewidth=2.5,
                    marker="D", markersize=4, markerfacecolor=MPL_ROSE,
                    markeredgecolor=MPL_BG, markeredgewidth=1.5,
                    label="Despesas", zorder=4, alpha=0.95)
            ax.fill_between(dts, desps, alpha=0.1, color=MPL_ROSE, zorder=2)

            ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
            ax.xaxis.set_major_locator(mdates.AutoDateLocator())
            fig.autofmt_xdate(rotation=30)

            # Hover
            annot = ax.annotate("", xy=(0, 0), xytext=(0, 14),
                                textcoords="offset points", fontsize=10,
                                color=MPL_BRANCO,
                                bbox=dict(boxstyle="round,pad=0.5",
                                          fc="#0F1D32", ec=MPL_CYAN, lw=1.5,
                                          alpha=0.95),
                                ha="center", zorder=10)
            annot.set_visible(False)

            def _hover(event):
                if event.inaxes != ax:
                    if annot.get_visible():
                        annot.set_visible(False)
                        fig.canvas.draw_idle()
                    return
                min_d, best = float("inf"), None
                for i, (dt, r, d) in enumerate(zip(dts, recs, desps)):
                    dx = mdates.date2num(dt) - event.xdata
                    for val, tp in [(r, "Receita"), (d, "Despesa")]:
                        if val > 0:
                            mx = max(max(recs + desps), 1)
                            dy = (val - event.ydata) / mx * 30
                            dist = dx**2 + dy**2
                            if dist < min_d:
                                min_d = dist
                                best = (dt, val, tp)
                if best and min_d < 3:
                    annot.xy = (mdates.date2num(best[0]), best[1])
                    annot.set_text(f"{best[2]}\nR$ {best[1]:,.2f}\n{best[0].strftime('%d/%m/%Y')}")
                    annot.set_visible(True)
                else:
                    annot.set_visible(False)
                fig.canvas.draw_idle()

            fig.canvas.mpl_connect("motion_notify_event", _hover)

            legend = ax.legend(facecolor=MPL_CARD, edgecolor=MPL_GRID,
                               labelcolor=MPL_BRANCO, fontsize=10,
                               loc="upper left", framealpha=0.9)
            legend.get_frame().set_linewidth(0.5)
        else:
            ax.text(0.5, 0.5, "Formato de datas não reconhecido.",
                    ha="center", va="center", color=MPL_TEXTO, fontsize=12,
                    transform=ax.transAxes)
            ax.axis("off")

    plt.tight_layout(pad=1.0)
    canvas = FigureCanvasTkAgg(fig, master=parent)
    canvas.draw()
    widget = canvas.get_tk_widget()
    widget.configure(bg=MPL_BG, highlightthickness=0)
    return widget


def criar_donut(parent, receitas: float, despesas: float, w=340, h=260):
    """Donut chart premium com saldo central."""
    fig, ax = plt.subplots(figsize=(w / 100, h / 100), dpi=100)
    fig.patch.set_facecolor(MPL_BG)
    ax.set_facecolor(MPL_BG)

    total = receitas + despesas
    if total <= 0:
        ax.text(0.5, 0.5, "Sem dados", ha="center", va="center",
                color=MPL_TEXTO, fontsize=13, transform=ax.transAxes)
        ax.axis("off")
    else:
        sizes = [receitas, despesas]
        colors = [MPL_CYAN_LIGHT, MPL_ROSE]

        wedges, texts, autos = ax.pie(
            sizes, colors=colors, startangle=90,
            wedgeprops=dict(width=0.5, edgecolor=MPL_BG, linewidth=5),
            autopct=lambda p: f"{p:.0f}%",
            pctdistance=0.76, explode=(0.02, 0.02),
        )
        for at in autos:
            at.set_color(MPL_BRANCO)
            at.set_fontsize(11)
            at.set_fontweight("bold")

        saldo = receitas - despesas
        cor_s = MPL_EMERALD if saldo >= 0 else MPL_ROSE
        ax.text(0, 0.06, f"R$ {abs(saldo):,.0f}",
                ha="center", va="center", fontsize=15,
                fontweight="bold", color=cor_s)
        ax.text(0, -0.12, "saldo" if saldo >= 0 else "déficit",
                ha="center", va="center", fontsize=9, color=MPL_TEXTO)

        legend = ax.legend(["Receitas", "Despesas"],
                          facecolor=MPL_CARD, edgecolor=MPL_GRID,
                          labelcolor=MPL_BRANCO, fontsize=9,
                          loc="lower center", framealpha=0.9)
        legend.get_frame().set_linewidth(0.5)

    plt.tight_layout(pad=0.3)
    canvas = FigureCanvasTkAgg(fig, master=parent)
    canvas.draw()
    widget = canvas.get_tk_widget()
    widget.configure(bg=MPL_BG, highlightthickness=0)
    return widget


# ─────────────────────────────────────────────────────────────────────────────
#  APP PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

class WealthEngine(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Wealth Engine")
        self.geometry("1340x860")
        self.minsize(1100, 700)
        self.configure(fg_color=COR_FUNDO)

        self.db: DatabaseManager | None = None
        self.usuario_atual: str | None = None
        self.master_db = MasterManager()
        self.brute_guard = BruteForceGuard()
        self._tela_ativa = "dash"

        self._tela_login()

    # ── Utilitários ──────────────────────────────────────────────────────────

    def _limpar(self):
        for w in self.winfo_children():
            w.destroy()

    def _toast(self, lbl, msg, color=None, delay=3000):
        if color is None:
            color = COR_SUCESSO
        try:
            lbl.configure(text=msg, text_color=color)
            self.after(delay, lambda: lbl.configure(text=""))
        except Exception:
            pass

    # ── LOGIN ─────────────────────────────────────────────────────────────────

    def _tela_login(self):
        self._limpar()
        self.db = None

        wrapper = ctk.CTkFrame(self, fg_color="transparent")
        wrapper.place(relx=0.5, rely=0.5, anchor="center")

        # Logo
        logo_frame = ctk.CTkFrame(wrapper, fg_color="transparent")
        logo_frame.pack(pady=(0, 32))
        ctk.CTkLabel(logo_frame, text="◈",
                     font=("SF Pro Display", 48),
                     text_color=COR_PRIMARIA).pack(side="left")
        ctk.CTkLabel(logo_frame, text="WEALTH ENGINE",
                     font=("SF Pro Display", 28, "bold"),
                     text_color=COR_TEXTO_FORTE).pack(side="left", padx=(12, 0))

        ctk.CTkLabel(wrapper, text="Acesse seu cofre financeiro criptografado",
                     font=FONT_SMALL, text_color=COR_TEXTO).pack(pady=(0, 28))

        card = ctk.CTkFrame(wrapper, fg_color=COR_CARD, corner_radius=20,
                            border_width=1, border_color=COR_BORDAS)
        card.pack(ipadx=48, ipady=32)

        self._ent_user = ctk.CTkEntry(
            card, placeholder_text="Usuário", width=340, height=50,
            corner_radius=RADIUS_INPUT, font=FONT_REGULAR,
            fg_color=COR_INPUT_BG, border_color=COR_BORDAS, border_width=1)
        self._ent_user.pack(pady=(28, 10), padx=48)

        self._ent_pass = ctk.CTkEntry(
            card, placeholder_text="Senha Master", show="•",
            width=340, height=50, corner_radius=RADIUS_INPUT,
            font=FONT_REGULAR, fg_color=COR_INPUT_BG,
            border_color=COR_BORDAS, border_width=1)
        self._ent_pass.pack(pady=(0, 24), padx=48)
        self._ent_pass.bind("<Return>", lambda e: self._autenticar())

        ctk.CTkButton(
            card, text="Acessar Cofre", fg_color=COR_PRIMARIA,
            hover_color=COR_PRIMARIA_DIM, text_color="#000",
            width=340, height=50, corner_radius=RADIUS_BUTTON,
            font=FONT_BOLD, command=self._autenticar).pack(pady=(0, 12), padx=48)

        ctk.CTkButton(
            card, text="Criar Nova Conta", fg_color="transparent",
            text_color=COR_PRIMARIA, hover_color=COR_CARD_HOVER,
            width=340, height=42, command=self._tela_registro).pack(padx=48)

        crypto = "◈  SQLCipher AES-256" if SQLCIPHER_DISPONIVEL else "⚠  Sem criptografia"
        crypto_c = COR_PRIMARIA if SQLCIPHER_DISPONIVEL else COR_AMARELO

        self._lbl_login_status = ctk.CTkLabel(
            card, text=f"Contas: {self.master_db.contar_usuarios()}/3   •   {crypto}",
            font=FONT_TINY, text_color=crypto_c)
        self._lbl_login_status.pack(pady=(16, 24))

    # ── REGISTRO ──────────────────────────────────────────────────────────────

    def _tela_registro(self):
        self._limpar()

        wrapper = ctk.CTkFrame(self, fg_color="transparent")
        wrapper.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(wrapper, text="◈  Criar Conta Blindada",
                     font=FONT_TITLE, text_color=COR_TEXTO_FORTE).pack(pady=(0, 24))

        card = ctk.CTkFrame(wrapper, fg_color=COR_CARD, corner_radius=20,
                            border_width=1, border_color=COR_BORDAS)
        card.pack(ipadx=48, ipady=24)

        def _input(parent, ph, show=""):
            e = ctk.CTkEntry(parent, placeholder_text=ph, width=360, height=48,
                             corner_radius=RADIUS_INPUT, show=show,
                             font=FONT_REGULAR, fg_color=COR_INPUT_BG,
                             border_color=COR_BORDAS, border_width=1)
            e.pack(pady=5, padx=48)
            return e

        ent_user = _input(card, "Usuário (letras, números, . ou _)")
        ent_pass = _input(card, "Senha (mín. 8, A-z, 0-9, !@#)", "•")

        lbl_forca = ctk.CTkLabel(card, text="", font=FONT_TINY)
        lbl_forca.pack(anchor="w", padx=52)

        def _check(*_):
            s = ent_pass.get()
            if not s:
                lbl_forca.configure(text="")
                return
            ok, msg = Validador.validar_senha(s)
            lbl_forca.configure(
                text=f"{'✓' if ok else '✗'} {msg}",
                text_color=COR_SUCESSO if ok else COR_DESPESA)
        ent_pass.bind("<KeyRelease>", _check)

        ent_cpf = _input(card, "CPF (000.000.000-00)")
        def _fmt_cpf(*_):
            raw = re.sub(r'\D', '', ent_cpf.get())[:11]
            out = ""
            for i, c in enumerate(raw):
                if i in (3, 6): out += "."
                elif i == 9:    out += "-"
                out += c
            ent_cpf.delete(0, "end")
            ent_cpf.insert(0, out)
        ent_cpf.bind("<KeyRelease>", _fmt_cpf)

        ent_nasc = _input(card, "Nascimento (DD/MM/AAAA)")
        def _fmt_dt(*_):
            raw = re.sub(r'\D', '', ent_nasc.get())[:8]
            out = ""
            for i, c in enumerate(raw):
                if i in (2, 4): out += "/"
                out += c
            ent_nasc.delete(0, "end")
            ent_nasc.insert(0, out)
        ent_nasc.bind("<KeyRelease>", _fmt_dt)

        self._lbl_reg_status = ctk.CTkLabel(card, text="", font=FONT_SMALL,
                                             text_color=COR_DESPESA)
        self._lbl_reg_status.pack(pady=(8, 0))

        campos = {"usuario": ent_user, "senha": ent_pass,
                  "cpf": ent_cpf, "nascimento": ent_nasc}

        ctk.CTkButton(card, text="Registrar & Criptografar",
                      fg_color=COR_SUCESSO, hover_color="#2AB585",
                      text_color="#000", width=360, height=50,
                      corner_radius=RADIUS_BUTTON, font=FONT_BOLD,
                      command=lambda: self._confirmar_registro(campos)).pack(
                          pady=(16, 8), padx=48)
        ctk.CTkButton(card, text="← Voltar ao Login",
                      fg_color="transparent", text_color=COR_TEXTO,
                      hover_color=COR_CARD_HOVER, width=360, height=38,
                      command=self._tela_login).pack(padx=48, pady=(0, 24))

    def _confirmar_registro(self, campos):
        u = campos["usuario"].get().strip()
        p = campos["senha"].get()
        c = campos["cpf"].get().strip()
        n = campos["nascimento"].get().strip()

        if not all([u, p, c, n]):
            self._lbl_reg_status.configure(text="⚠ Preencha todos os campos.")
            return
        for validator, val, label in [
            (Validador.validar_usuario, u, "Usuário"),
            (Validador.validar_senha, p, "Senha"),
            (Validador.validar_cpf, re.sub(r'\D', '', c), "CPF"),
            (Validador.validar_data_nascimento, n, "Data"),
        ]:
            ok, msg = validator(val)
            if not ok:
                self._lbl_reg_status.configure(text=f"⚠ {label}: {msg}")
                return
        try:
            salt = SecurityManager.gerar_salt()
            chave = SecurityManager.derivar_chave(p, salt)
            senha_hash = SecurityManager.gerar_hash_verificacao(chave)
            self.master_db.registrar_usuario(u, salt, senha_hash)
            tmp = DatabaseManager(f"vault_{u.lower()}.db", chave)
            with tmp.transacao() as cur:
                cur.execute("INSERT OR REPLACE INTO tb_perfil (id,cpf,data_nascimento) VALUES (1,?,?)",
                            (re.sub(r'\D', '', c), n))
            self._tela_login()
        except Exception as exc:
            self._lbl_reg_status.configure(text=f"⚠ {exc}")

    # ── AUTENTICAÇÃO ──────────────────────────────────────────────────────────

    def _autenticar(self):
        user = self._ent_user.get().strip()
        pw = self._ent_pass.get()
        if not user or not pw:
            self._lbl_login_status.configure(text="⚠ Preencha usuário e senha.",
                                              text_color=COR_DESPESA)
            return
        bloq, seg = self.brute_guard.esta_bloqueado(user)
        if bloq:
            self._lbl_login_status.configure(
                text=f"🔒 Bloqueado. Aguarde {seg}s.", text_color=COR_DESPESA)
            return
        salt = self.master_db.obter_salt(user)
        if not salt:
            self._lbl_login_status.configure(text="⚠ Usuário não encontrado.",
                                              text_color=COR_DESPESA)
            return
        if not self.master_db.verificar_senha(user, pw):
            travou, rest = self.brute_guard.registrar_falha(user)
            msg = f"🔒 Bloqueado por 5 minutos." if travou else f"⚠ Senha incorreta. {rest} tentativas."
            self._lbl_login_status.configure(text=msg, text_color=COR_DESPESA)
            return
        try:
            chave = SecurityManager.derivar_chave(pw, salt)
            self.db = DatabaseManager(f"vault_{user.lower()}.db", chave)
            self.db.resumo_financeiro()
            self.usuario_atual = user
            self.brute_guard.registrar_sucesso(user)
            self._limpar()
            self._setup_main()
        except Exception:
            self._lbl_login_status.configure(text="⚠ Erro ao abrir cofre.",
                                              text_color=COR_DESPESA)

    # ── MAIN LAYOUT ───────────────────────────────────────────────────────────

    def _setup_main(self):
        self._sidebar = ctk.CTkFrame(self, width=240, fg_color=COR_SIDEBAR,
                                     corner_radius=0)
        self._sidebar.pack(side="left", fill="y")
        self._sidebar.pack_propagate(False)

        self._content = ctk.CTkFrame(self, fg_color=COR_FUNDO, corner_radius=0)
        self._content.pack(side="right", fill="both", expand=True)

        self._build_sidebar()
        self._navegar("dash")

    def _build_sidebar(self, ativo="dash"):
        for w in self._sidebar.winfo_children():
            w.destroy()

        # Logo compacta
        logo = ctk.CTkFrame(self._sidebar, fg_color="transparent")
        logo.pack(fill="x", padx=20, pady=(28, 8))
        ctk.CTkLabel(logo, text="◈", font=("SF Pro Display", 24),
                     text_color=COR_PRIMARIA).pack(side="left")
        ctk.CTkLabel(logo, text="WEALTH",
                     font=("SF Pro Display", 18, "bold"),
                     text_color=COR_TEXTO_FORTE).pack(side="left", padx=(10, 0))

        ctk.CTkLabel(self._sidebar, text="ENGINE",
                     font=FONT_TINY, text_color=COR_TEXTO_MUTED).pack(
                         anchor="w", padx=56, pady=(0, 20))

        Divider(self._sidebar).pack(fill="x", padx=20, pady=(0, 16))

        for label, icon, tag in [
            ("Visão Geral",  "◇", "dash"),
            ("Bancos",       "◆", "bancos"),
            ("Transações",   "⬡", "trans"),
            ("Assinaturas",  "○", "assinaturas"),
            ("Planejamento", "△", "plan"),
        ]:
            SidebarButton(self._sidebar, label, icon,
                          active=(tag == ativo),
                          command=lambda t=tag: self._navegar(t),
                          ).pack(fill="x", padx=14, pady=2)

        # Spacer
        ctk.CTkFrame(self._sidebar, fg_color="transparent").pack(fill="both", expand=True)

        Divider(self._sidebar).pack(fill="x", padx=20, pady=8)
        ctk.CTkLabel(self._sidebar, text=f"◈  {self.usuario_atual}",
                     font=FONT_SMALL, text_color=COR_TEXTO).pack(
                         anchor="w", padx=24, pady=(4, 6))
        ctk.CTkButton(self._sidebar, text="   🔒  Trancar Cofre",
                      fg_color="transparent", text_color=COR_DESPESA,
                      hover_color="#1A0A14", anchor="w", height=38,
                      font=FONT_SMALL, corner_radius=RADIUS_INPUT,
                      command=self._tela_login).pack(
                          fill="x", padx=14, pady=(0, 24))

    def _navegar(self, tela):
        self._tela_ativa = tela
        self._build_sidebar(ativo=tela)
        for w in self._content.winfo_children():
            w.destroy()

        scroll = ctk.CTkScrollableFrame(
            self._content, fg_color="transparent",
            scrollbar_button_color=COR_BORDAS,
            scrollbar_button_hover_color=COR_PRIMARIA)
        scroll.pack(fill="both", expand=True)

        {"dash": self._pg_dash, "bancos": self._pg_bancos,
         "trans": self._pg_trans, "assinaturas": self._pg_ass,
         "plan": self._pg_plan}.get(tela, self._pg_dash)(scroll)

    # ── JANELA DETALHE ────────────────────────────────────────────────────────

    def _detalhe(self, titulo, tipo):
        win = ctk.CTkToplevel(self)
        win.title(f"Wealth Engine — {titulo}")
        win.geometry("720x520")
        win.configure(fg_color=COR_FUNDO)
        win.grab_set()

        ctk.CTkLabel(win, text=titulo, font=FONT_TITLE,
                     text_color=COR_TEXTO_FORTE).pack(anchor="w", padx=24, pady=(20, 12))

        scroll = ctk.CTkScrollableFrame(win, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        if tipo == "PATRIMONIO":
            res = self.db.resumo_financeiro()
            for lb, v, c in [("Receitas", res["receitas"], COR_RECEITA),
                             ("Despesas", res["despesas"], COR_DESPESA),
                             ("Assinaturas", res["assinaturas"], COR_ROXO),
                             ("Patrimônio", res["patrimonio"], COR_PRIMARIA)]:
                r = ctk.CTkFrame(scroll, fg_color=COR_CARD, corner_radius=12)
                r.pack(fill="x", pady=3, padx=8)
                ctk.CTkLabel(r, text=lb, font=FONT_REGULAR,
                             text_color=COR_TEXTO).pack(side="left", padx=16, pady=14)
                ctk.CTkLabel(r, text=f"R$ {v:,.2f}", font=FONT_BOLD,
                             text_color=c).pack(side="right", padx=16, pady=14)
        else:
            rows = self.db.obter_transacoes_por_tipo(tipo)
            if not rows:
                ctk.CTkLabel(scroll, text="Nenhuma transação.",
                             font=FONT_SMALL, text_color=COR_TEXTO).pack(pady=40)
            else:
                for _, data, desc, val, conta in rows:
                    cor = COR_RECEITA if tipo == "RECEITA" else COR_DESPESA
                    f = ctk.CTkFrame(scroll, fg_color=COR_CARD, corner_radius=10)
                    f.pack(fill="x", pady=2, padx=8)
                    ctk.CTkLabel(f, text=str(data)[:10], font=FONT_TINY,
                                 text_color=COR_TEXTO).pack(side="left", padx=12, pady=10)
                    ctk.CTkLabel(f, text=str(desc)[:40] if desc else "—",
                                 font=FONT_REGULAR, text_color=COR_TEXTO_FORTE).pack(
                                     side="left", padx=8, pady=10)
                    ctk.CTkLabel(f, text=f"R$ {abs(val):,.2f}", font=FONT_BOLD,
                                 text_color=cor).pack(side="right", padx=12, pady=10)

    # ── DASHBOARD ─────────────────────────────────────────────────────────────

    def _pg_dash(self, p):
        # Header
        hdr = ctk.CTkFrame(p, fg_color="transparent")
        hdr.pack(fill="x", padx=PAD_PAGE, pady=(32, 4))
        ctk.CTkLabel(hdr, text="Visão Geral", font=FONT_TITLE,
                     text_color=COR_TEXTO_FORTE).pack(side="left")
        ctk.CTkLabel(hdr, text=datetime.now().strftime("%d/%m/%Y"),
                     font=FONT_SMALL, text_color=COR_TEXTO).pack(side="right")

        Divider(p).pack(fill="x", padx=PAD_PAGE, pady=(8, 20))

        res = self.db.resumo_financeiro()
        fmt = lambda v: f"R$ {v:,.2f}"

        # KPI cards
        kpi = ctk.CTkFrame(p, fg_color="transparent")
        kpi.pack(fill="x", padx=PAD_PAGE, pady=(0, PAD_SECTION))
        kpi.columnconfigure((0, 1, 2), weight=1, uniform="k")

        GlowCard(kpi, "Patrimônio Líquido", fmt(res["patrimonio"]),
                 "clique para detalhes", accent=COR_PRIMARIA, icon="◈",
                 command=lambda: self._detalhe("Patrimônio", "PATRIMONIO")
                 ).grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=0)

        GlowCard(kpi, "Total de Entradas", fmt(res["receitas"]),
                 "receitas acumuladas", accent=COR_RECEITA, icon="↑",
                 command=lambda: self._detalhe("Entradas", "RECEITA")
                 ).grid(row=0, column=1, sticky="nsew", padx=4, pady=0)

        GlowCard(kpi, "Total de Saídas", fmt(res["despesas"]),
                 "despesas + assinaturas", accent=COR_DESPESA, icon="↓",
                 command=lambda: self._detalhe("Saídas", "DESPESA")
                 ).grid(row=0, column=2, sticky="nsew", padx=(8, 0), pady=0)

        # Gráfico evolução
        ctk.CTkLabel(p, text="Evolução Financeira", font=FONT_SUBTITLE,
                     text_color=COR_TEXTO_FORTE).pack(anchor="w", padx=PAD_PAGE, pady=(0, 8))

        gbox = ctk.CTkFrame(p, fg_color=MPL_CARD, corner_radius=RADIUS_CARD,
                            border_width=1, border_color=COR_BORDAS)
        gbox.pack(fill="x", padx=PAD_PAGE, pady=(0, PAD_SECTION))

        dados = self.db.transacoes_agrupadas()
        g = criar_grafico_evolucao(gbox, dados, w=820, h=280)
        g.pack(padx=8, pady=8)

        # Donut + Assinaturas
        row2 = ctk.CTkFrame(p, fg_color="transparent")
        row2.pack(fill="x", padx=PAD_PAGE, pady=(0, 32))
        row2.columnconfigure(0, weight=1)
        row2.columnconfigure(1, weight=1)

        # Donut
        d_frame = ctk.CTkFrame(row2, fg_color=MPL_CARD, corner_radius=RADIUS_CARD,
                               border_width=1, border_color=COR_BORDAS)
        d_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        ctk.CTkLabel(d_frame, text="Distribuição", font=FONT_BOLD,
                     text_color=COR_TEXTO_FORTE).pack(anchor="w", padx=16, pady=(14, 0))
        criar_donut(d_frame, res["receitas"], res["despesas"],
                    w=360, h=250).pack(padx=8, pady=(0, 8))

        # Assinaturas resumo
        a_frame = ctk.CTkFrame(row2, fg_color=COR_CARD, corner_radius=RADIUS_CARD,
                               border_width=1, border_color=COR_BORDAS)
        a_frame.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        ctk.CTkLabel(a_frame, text="○  Assinaturas Ativas", font=FONT_BOLD,
                     text_color=COR_TEXTO_FORTE).pack(anchor="w", padx=PAD_CARD, pady=(16, 8))

        ativas = [a for a in self.db.listar_assinaturas() if a[4] == "ATIVA"]
        if not ativas:
            ctk.CTkLabel(a_frame, text="Nenhuma assinatura ativa.",
                         font=FONT_SMALL, text_color=COR_TEXTO).pack(pady=40)
        else:
            for a in ativas[:6]:
                r = ctk.CTkFrame(a_frame, fg_color="transparent")
                r.pack(fill="x", padx=PAD_CARD, pady=3)
                ctk.CTkLabel(r, text=a[1], font=FONT_REGULAR,
                             text_color=COR_TEXTO_FORTE).pack(side="left")
                ctk.CTkLabel(r, text=f"R$ {a[2]:.2f}", font=FONT_MONO,
                             text_color=COR_ROXO).pack(side="right")

        Divider(a_frame).pack(fill="x", padx=PAD_CARD, pady=8)
        tf = ctk.CTkFrame(a_frame, fg_color="transparent")
        tf.pack(fill="x", padx=PAD_CARD, pady=(0, 16))
        ctk.CTkLabel(tf, text="Total / mês", font=FONT_SMALL,
                     text_color=COR_TEXTO).pack(side="left")
        ctk.CTkLabel(tf, text=f"R$ {res['assinaturas']:,.2f}",
                     font=FONT_BOLD, text_color=COR_DESPESA).pack(side="right")

    # ── BANCOS ────────────────────────────────────────────────────────────────

    def _pg_bancos(self, p):
        ctk.CTkLabel(p, text="Contas Bancárias", font=FONT_TITLE,
                     text_color=COR_TEXTO_FORTE).pack(anchor="w", padx=PAD_PAGE, pady=(32, 4))
        Divider(p).pack(fill="x", padx=PAD_PAGE, pady=(8, 20))

        form = ctk.CTkFrame(p, fg_color=COR_CARD, corner_radius=RADIUS_CARD,
                            border_width=1, border_color=COR_BORDAS)
        form.pack(fill="x", padx=PAD_PAGE, pady=(0, PAD_SECTION))

        ctk.CTkLabel(form, text="Adicionar Conta", font=FONT_BOLD,
                     text_color=COR_TEXTO_FORTE).pack(anchor="w", padx=PAD_CARD, pady=(PAD_CARD, 12))

        row = ctk.CTkFrame(form, fg_color="transparent")
        row.pack(fill="x", padx=PAD_CARD, pady=(0, PAD_CARD))

        cmb = ctk.CTkComboBox(row, values=BANCOS_NOMES, width=320, height=46,
                              corner_radius=RADIUS_INPUT, font=FONT_REGULAR,
                              button_color=COR_PRIMARIA, fg_color=COR_INPUT_BG,
                              border_color=COR_BORDAS, border_width=1)
        cmb.set(BANCOS_NOMES[0])
        cmb.pack(side="left", padx=(0, 10))

        opt = ctk.CTkOptionMenu(row, values=["Corrente", "Poupança", "Investimentos", "Digital"],
                                height=46, corner_radius=RADIUS_INPUT, font=FONT_REGULAR,
                                fg_color=COR_BORDAS, button_color=COR_PRIMARIA, width=180)
        opt.pack(side="left", padx=(0, 10))

        lbl_s = ctk.CTkLabel(form, text="", font=FONT_SMALL)
        lbl_s.pack(anchor="w", padx=PAD_CARD, pady=(0, 8))

        lista = ctk.CTkFrame(p, fg_color="transparent")
        lista.pack(fill="x", padx=PAD_PAGE)

        def _refresh():
            for w in lista.winfo_children(): w.destroy()
            icon_map = {"Corrente": "◆", "Poupança": "◇", "Investimentos": "△", "Digital": "○"}
            for cid, nome, tipo, *rest in self.db.listar_contas():
                cod = rest[0] if rest else ""
                card = ctk.CTkFrame(lista, fg_color=COR_CARD, corner_radius=RADIUS_CARD,
                                    border_width=1, border_color=COR_BORDAS)
                card.pack(fill="x", pady=4)
                lf = ctk.CTkFrame(card, fg_color="transparent")
                lf.pack(side="left", padx=PAD_CARD, pady=16)
                ctk.CTkLabel(lf, text=icon_map.get(tipo, "◈"),
                             font=("SF Pro Display", 20), text_color=COR_PRIMARIA).pack(side="left")
                inf = ctk.CTkFrame(lf, fg_color="transparent")
                inf.pack(side="left", padx=12)
                ctk.CTkLabel(inf, text=nome, font=FONT_BOLD,
                             text_color=COR_TEXTO_FORTE).pack(anchor="w")
                ctk.CTkLabel(inf, text=f"{tipo}  •  Cód. {cod}",
                             font=FONT_TINY, text_color=COR_TEXTO).pack(anchor="w")

        def _save():
            sel = cmb.get()
            if sel not in BANCOS_NOMES:
                self._toast(lbl_s, "⚠ Selecione um banco.", COR_DESPESA)
                return
            idx = BANCOS_NOMES.index(sel)
            cod, nome = BANCOS_BR[idx]
            with self.db.transacao() as c:
                c.execute("INSERT INTO tb_contas (nome,codigo,tipo) VALUES (?,?,?)",
                          (nome, cod, opt.get()))
            self._toast(lbl_s, f"✓ {nome} registrado!")
            _refresh()

        ctk.CTkButton(row, text="Registrar", fg_color=COR_PRIMARIA,
                      hover_color=COR_PRIMARIA_DIM, text_color="#000",
                      height=46, corner_radius=RADIUS_BUTTON, font=FONT_BOLD,
                      width=130, command=_save).pack(side="left")
        _refresh()

    # ── TRANSAÇÕES ────────────────────────────────────────────────────────────

    def _pg_trans(self, p):
        ctk.CTkLabel(p, text="Transações & Extratos", font=FONT_TITLE,
                     text_color=COR_TEXTO_FORTE).pack(anchor="w", padx=PAD_PAGE, pady=(32, 4))
        Divider(p).pack(fill="x", padx=PAD_PAGE, pady=(8, 20))

        # ── Manual entry ──
        box_m = ctk.CTkFrame(p, fg_color=COR_CARD, corner_radius=RADIUS_CARD,
                             border_width=1, border_color=COR_BORDAS)
        box_m.pack(fill="x", padx=PAD_PAGE, pady=(0, 12))
        ctk.CTkLabel(box_m, text="⬡  Inserir Transação", font=FONT_BOLD,
                     text_color=COR_TEXTO_FORTE).pack(anchor="w", padx=PAD_CARD, pady=(PAD_CARD, 8))

        rm = ctk.CTkFrame(box_m, fg_color="transparent")
        rm.pack(fill="x", padx=PAD_CARD, pady=(0, 6))

        def _ent(parent, ph, w=0):
            e = ctk.CTkEntry(parent, placeholder_text=ph, height=42,
                             corner_radius=RADIUS_INPUT, font=FONT_REGULAR,
                             fg_color=COR_INPUT_BG, border_color=COR_BORDAS, border_width=1)
            if w: e.configure(width=w)
            return e

        ed = _ent(rm, "Descrição"); ed.pack(side="left", fill="x", expand=True, padx=(0, 6))
        ev = _ent(rm, "Valor R$", 120); ev.pack(side="left", padx=(0, 6))
        edt = _ent(rm, "DD/MM/AAAA", 120); edt.pack(side="left", padx=(0, 6))
        def _fdt(*_):
            raw = re.sub(r'\D', '', edt.get())[:8]
            out = ""
            for i, c in enumerate(raw):
                if i in (2, 4): out += "/"
                out += c
            edt.delete(0, "end"); edt.insert(0, out)
        edt.bind("<KeyRelease>", _fdt)

        cmb_tp = ctk.CTkOptionMenu(rm, values=["Receita", "Despesa"],
                                   height=42, corner_radius=RADIUS_INPUT, width=110,
                                   fg_color=COR_BORDAS, button_color=COR_PRIMARIA)
        cmb_tp.pack(side="left", padx=(0, 6))

        contas = self.db.listar_contas()
        nc = [c[1] for c in contas]; ic = [c[0] for c in contas]

        cmb_ct = ctk.CTkOptionMenu(rm, values=nc if nc else ["—"],
                                   height=42, corner_radius=RADIUS_INPUT, width=170,
                                   fg_color=COR_BORDAS, button_color=COR_PRIMARIA)
        cmb_ct.pack(side="left", padx=(0, 6))

        lbl_ms = ctk.CTkLabel(box_m, text="", font=FONT_SMALL)
        lbl_ms.pack(anchor="w", padx=PAD_CARD, pady=(0, 12))

        def _save_manual():
            d, dt_s, v_s = ed.get().strip(), edt.get().strip(), ev.get().strip()
            if not all([d, dt_s, v_s]):
                self._toast(lbl_ms, "⚠ Preencha todos os campos.", COR_DESPESA); return
            try: dt = datetime.strptime(dt_s, "%d/%m/%Y"); di = dt.strftime("%Y-%m-%d")
            except: self._toast(lbl_ms, "⚠ Data inválida.", COR_DESPESA); return
            try: val = float(v_s.replace(",", "."))
            except: self._toast(lbl_ms, "⚠ Valor inválido.", COR_DESPESA); return
            cat = 1 if cmb_tp.get() == "Receita" else 2
            if cat == 2: val = -abs(val)
            cid = ic[nc.index(cmb_ct.get())] if cmb_ct.get() in nc else 1
            self.db.inserir_transacao(cid, cat, val, di, d)
            ed.delete(0, "end"); ev.delete(0, "end"); edt.delete(0, "end")
            self._toast(lbl_ms, "✓ Transação registrada!")
            _refresh()

        ctk.CTkButton(rm, text="Salvar", fg_color=COR_SUCESSO,
                      hover_color="#2AB585", text_color="#000",
                      height=42, corner_radius=RADIUS_BUTTON, font=FONT_BOLD,
                      width=90, command=_save_manual).pack(side="left")

        # ── CSV ──
        box_csv = ctk.CTkFrame(p, fg_color=COR_CARD, corner_radius=RADIUS_CARD,
                               border_width=1, border_color=COR_BORDAS)
        box_csv.pack(fill="x", padx=PAD_PAGE, pady=(0, 12))
        ci = ctk.CTkFrame(box_csv, fg_color="transparent")
        ci.pack(fill="x", padx=PAD_CARD, pady=14)
        lc = ctk.CTkFrame(ci, fg_color="transparent")
        lc.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(lc, text="⬡  Importar Extrato (.csv)", font=FONT_BOLD,
                     text_color=COR_TEXTO_FORTE).pack(anchor="w")
        ctk.CTkLabel(lc, text="Detecta separadores, encodings e formatos de valor automaticamente.",
                     font=FONT_TINY, text_color=COR_TEXTO).pack(anchor="w", pady=(2, 0))
        lbl_csv = ctk.CTkLabel(ci, text="", font=FONT_SMALL)
        lbl_csv.pack(side="right", padx=12)
        ctk.CTkButton(ci, text="Selecionar CSV", fg_color=COR_PRIMARIA,
                      hover_color=COR_PRIMARIA_DIM, text_color="#000",
                      height=42, corner_radius=RADIUS_BUTTON, font=FONT_BOLD,
                      width=160, command=lambda: self._importar_csv(lbl_csv, _refresh)
                      ).pack(side="right")

        # ── Filtros ──
        ff = ctk.CTkFrame(p, fg_color=COR_CARD, corner_radius=RADIUS_CARD,
                          border_width=1, border_color=COR_BORDAS)
        ff.pack(fill="x", padx=PAD_PAGE, pady=(0, 12))
        ctk.CTkLabel(ff, text="Filtros", font=FONT_BOLD,
                     text_color=COR_TEXTO_FORTE).pack(anchor="w", padx=PAD_CARD, pady=(14, 8))
        fr = ctk.CTkFrame(ff, fg_color="transparent")
        fr.pack(fill="x", padx=PAD_CARD, pady=(0, 14))

        fn = ["Todas"] + nc; fi = [0] + ic
        cmb_fc = ctk.CTkComboBox(fr, values=fn, width=190, height=40,
                                 corner_radius=RADIUS_INPUT, font=FONT_REGULAR,
                                 button_color=COR_PRIMARIA, fg_color=COR_INPUT_BG,
                                 border_color=COR_BORDAS, border_width=1)
        cmb_fc.set(fn[0]); cmb_fc.pack(side="left", padx=(0, 6))
        cmb_ft = ctk.CTkComboBox(fr, values=["Todos", "RECEITA", "DESPESA"],
                                 width=130, height=40, corner_radius=RADIUS_INPUT,
                                 font=FONT_REGULAR, button_color=COR_PRIMARIA,
                                 fg_color=COR_INPUT_BG, border_color=COR_BORDAS, border_width=1)
        cmb_ft.set("Todos"); cmb_ft.pack(side="left", padx=(0, 6))
        edi = _ent(fr, "De DD/MM/AAAA", 140); edi.pack(side="left", padx=(0, 6))
        edf = _ent(fr, "Até DD/MM/AAAA", 140); edf.pack(side="left", padx=(0, 6))
        ctk.CTkButton(fr, text="Filtrar", fg_color=COR_PRIMARIA,
                      hover_color=COR_PRIMARIA_DIM, text_color="#000",
                      height=40, corner_radius=RADIUS_BUTTON, font=FONT_BOLD,
                      width=85, command=lambda: _refresh()).pack(side="left", padx=(0, 6))
        ctk.CTkButton(fr, text="Limpar", fg_color="transparent",
                      text_color=COR_TEXTO, hover_color=COR_CARD_HOVER,
                      height=40, corner_radius=RADIUS_BUTTON, font=FONT_SMALL,
                      width=70, command=lambda: [cmb_fc.set(fn[0]), cmb_ft.set("Todos"),
                                                  edi.delete(0, "end"), edf.delete(0, "end"),
                                                  _refresh()]).pack(side="left")

        # ── Tabela ──
        tbl = ctk.CTkFrame(p, fg_color=COR_CARD, corner_radius=RADIUS_CARD,
                           border_width=1, border_color=COR_BORDAS)
        tbl.pack(fill="both", expand=True, padx=PAD_PAGE, pady=(0, 32))

        hdr = ctk.CTkFrame(tbl, fg_color=COR_BORDAS, corner_radius=0, height=38)
        hdr.pack(fill="x")
        for txt, w_ in [("Data", 100), ("Descrição", 260), ("Conta", 140), ("Tipo", 80), ("Valor", 130)]:
            ctk.CTkLabel(hdr, text=txt, font=FONT_TINY, text_color=COR_TEXTO_MUTED,
                         width=w_).pack(side="left", padx=8, pady=8)

        li = ctk.CTkScrollableFrame(tbl, fg_color="transparent", height=380)
        li.pack(fill="both", expand=True)

        def _refresh():
            for w in li.winfo_children(): w.destroy()
            sel_c = cmb_fc.get()
            cid = fi[fn.index(sel_c)] if sel_c in fn else 0
            tp = None if cmb_ft.get() == "Todos" else cmb_ft.get()
            di_sql = df_sql = None
            for raw, ref in [(edi.get().strip(), "di"), (edf.get().strip(), "df")]:
                if raw:
                    try:
                        v = datetime.strptime(raw, "%d/%m/%Y").strftime("%Y-%m-%d")
                        if ref == "di": di_sql = v
                        else: df_sql = v
                    except: pass
            rows = self.db.listar_transacoes(conta_id=cid or None, tipo=tp,
                                             data_inicio=di_sql, data_fim=df_sql)
            if not rows:
                ctk.CTkLabel(li, text="Nenhuma transação encontrada.",
                             font=FONT_SMALL, text_color=COR_TEXTO).pack(pady=40)
                return
            for tid, data, desc, valor, conta_n, cat_n in rows:
                cor = COR_RECEITA if valor and valor >= 0 else COR_DESPESA
                sinal = "+" if valor and valor >= 0 else ""
                rf = ctk.CTkFrame(li, fg_color="transparent", height=40)
                rf.pack(fill="x", padx=6); rf.pack_propagate(False)
                de = str(data)[:10] if data else "—"
                try: de = datetime.strptime(de, "%Y-%m-%d").strftime("%d/%m/%Y")
                except: pass
                ctk.CTkLabel(rf, text=de, font=FONT_TINY, text_color=COR_TEXTO,
                             width=100).pack(side="left", padx=8)
                ctk.CTkLabel(rf, text=str(desc)[:40] if desc else "—", font=FONT_REGULAR,
                             text_color=COR_TEXTO_FORTE, width=260, anchor="w").pack(side="left", padx=8)
                ctk.CTkLabel(rf, text=conta_n or "—", font=FONT_TINY,
                             text_color=COR_TEXTO, width=140).pack(side="left", padx=8)
                ctk.CTkLabel(rf, text=cat_n or "—", font=FONT_TINY,
                             text_color=COR_TEXTO, width=80).pack(side="left", padx=8)
                ctk.CTkLabel(rf, text=f"{sinal}R$ {abs(valor or 0):,.2f}", font=FONT_BOLD,
                             text_color=cor, width=130).pack(side="left", padx=8)
                Divider(li).pack(fill="x", padx=8)
        _refresh()

    def _importar_csv(self, lbl, refresh_fn):
        cam = filedialog.askopenfilename(title="Selecione extrato",
                                         filetypes=[("CSV", "*.csv"), ("Todos", "*.*")])
        if not cam: return
        try:
            df = None
            for enc in ["utf-8", "latin-1", "cp1252"]:
                for sep in [",", ";", "\t", "|"]:
                    try:
                        df = pd.read_csv(cam, sep=sep, encoding=enc, dtype=str,
                                         keep_default_na=False)
                        if len(df.columns) >= 3: break
                    except: continue
                if df is not None and len(df.columns) >= 3: break
            if df is None or len(df.columns) < 3:
                self._toast(lbl, "⚠ CSV não reconhecido.", COR_DESPESA); return

            def _fc(kws, fb):
                for c in df.columns:
                    if any(k in c.lower() for k in kws): return c
                return df.columns[fb] if fb < len(df.columns) else None

            cd = _fc(["data", "date", "dt"], 0)
            cdsc = _fc(["desc", "hist", "memo", "narrat", "detalhe"], 1)
            cv = _fc(["valor", "value", "amount", "vlr", "quantia"], 2)
            if not all([cd, cdsc, cv]):
                self._toast(lbl, "⚠ Colunas não identificadas.", COR_DESPESA); return

            ins = 0
            with self.db.transacao() as cur:
                for _, row in df.iterrows():
                    rv = str(row[cv]).strip()
                    if "," in rv and "." in rv: rv = rv.replace(".", "").replace(",", ".")
                    elif "," in rv: rv = rv.replace(",", ".")
                    rv = re.sub(r'[R$\s]', '', rv)
                    try: val = float(rv)
                    except: continue
                    rd = str(row[cd]).strip()
                    diso = rd
                    for f in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%m/%d/%Y", "%d/%m/%y"):
                        try: diso = datetime.strptime(rd[:10], f).strftime("%Y-%m-%d"); break
                        except: continue
                    cat = 1 if val > 0 else 2
                    cur.execute("INSERT INTO tb_transacoes (conta_id,categoria_id,valor,data_transacao,descricao) VALUES (1,?,?,?,?)",
                                (cat, val, diso, str(row[cdsc]).strip()))
                    ins += 1
            self._toast(lbl, f"✓ {ins} transações importadas!", COR_SUCESSO, 6000)
            refresh_fn()
        except Exception as e:
            self._toast(lbl, f"⚠ {e}", COR_DESPESA, 8000)

    # ── ASSINATURAS ───────────────────────────────────────────────────────────

    def _pg_ass(self, p):
        ctk.CTkLabel(p, text="Assinaturas Fixas", font=FONT_TITLE,
                     text_color=COR_TEXTO_FORTE).pack(anchor="w", padx=PAD_PAGE, pady=(32, 4))
        Divider(p).pack(fill="x", padx=PAD_PAGE, pady=(8, 20))

        form = ctk.CTkFrame(p, fg_color=COR_CARD, corner_radius=RADIUS_CARD,
                            border_width=1, border_color=COR_BORDAS)
        form.pack(fill="x", padx=PAD_PAGE, pady=(0, PAD_SECTION))
        ctk.CTkLabel(form, text="Nova Assinatura", font=FONT_BOLD,
                     text_color=COR_TEXTO_FORTE).pack(anchor="w", padx=PAD_CARD, pady=(PAD_CARD, 12))

        rf = ctk.CTkFrame(form, fg_color="transparent")
        rf.pack(fill="x", padx=PAD_CARD, pady=(0, 8))

        def _ent(parent, ph, w=0):
            e = ctk.CTkEntry(parent, placeholder_text=ph, height=46,
                             corner_radius=RADIUS_INPUT, font=FONT_REGULAR,
                             fg_color=COR_INPUT_BG, border_color=COR_BORDAS, border_width=1)
            if w: e.configure(width=w)
            return e

        en = _ent(rf, "Serviço (ex: Netflix)"); en.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ev = _ent(rf, "Valor R$", 130); ev.pack(side="left", padx=(0, 8))
        edia = _ent(rf, "Dia venc.", 100); edia.pack(side="left", padx=(0, 8))

        lbl_as = ctk.CTkLabel(form, text="", font=FONT_SMALL)
        lbl_as.pack(anchor="w", padx=PAD_CARD, pady=(0, 12))

        lista = ctk.CTkFrame(p, fg_color="transparent")
        lista.pack(fill="x", padx=PAD_PAGE)

        def _refresh():
            for w in lista.winfo_children(): w.destroy()
            ass = self.db.listar_assinaturas()
            if not ass:
                ctk.CTkLabel(lista, text="Nenhuma assinatura.", font=FONT_SMALL,
                             text_color=COR_TEXTO).pack(pady=30); return
            total = 0.0
            for aid, nome, valor, dia, status in ass:
                ativa = status == "ATIVA"
                card = ctk.CTkFrame(lista, fg_color=COR_CARD, corner_radius=RADIUS_CARD,
                                    border_width=1, border_color=COR_BORDAS)
                card.pack(fill="x", pady=4)
                lf = ctk.CTkFrame(card, fg_color="transparent")
                lf.pack(side="left", padx=PAD_CARD, pady=14, fill="x", expand=True)
                badge_c = COR_SUCESSO if ativa else COR_TEXTO_MUTED
                ctk.CTkLabel(lf, text="● ATIVA" if ativa else "● CANCELADA",
                             font=FONT_TINY, text_color=badge_c).pack(anchor="w")
                ctk.CTkLabel(lf, text=nome, font=FONT_BOLD,
                             text_color=COR_TEXTO_FORTE if ativa else COR_TEXTO).pack(anchor="w")
                ctk.CTkLabel(lf, text=f"Vence dia {dia}",
                             font=FONT_TINY, text_color=COR_TEXTO).pack(anchor="w")
                rg = ctk.CTkFrame(card, fg_color="transparent")
                rg.pack(side="right", padx=PAD_CARD)
                ctk.CTkLabel(rg, text=f"R$ {valor:,.2f}", font=FONT_MONO_BIG,
                             text_color=COR_ROXO).pack(anchor="e")
                if ativa:
                    ctk.CTkButton(rg, text="Cancelar", fg_color="transparent",
                                  text_color=COR_DESPESA, hover_color="#1A0A14",
                                  height=28, font=FONT_TINY,
                                  command=lambda i=aid: [self.db.cancelar_assinatura(i), _refresh()]
                                  ).pack(anchor="e", pady=(4, 0))
                    total += valor
            Divider(lista).pack(fill="x", pady=8)
            rod = ctk.CTkFrame(lista, fg_color="transparent")
            rod.pack(fill="x", padx=4)
            ctk.CTkLabel(rod, text="Total mensal:", font=FONT_BOLD,
                         text_color=COR_TEXTO).pack(side="left")
            ctk.CTkLabel(rod, text=f"R$ {total:,.2f}", font=FONT_BOLD,
                         text_color=COR_DESPESA).pack(side="right")

        def _save():
            n = en.get().strip()
            try: v = float(ev.get().replace(",", ".")); d = int(edia.get() or 1)
            except: self._toast(lbl_as, "⚠ Valor/dia inválido.", COR_DESPESA); return
            if not n: self._toast(lbl_as, "⚠ Nome obrigatório.", COR_DESPESA); return
            if d < 1 or d > 31: self._toast(lbl_as, "⚠ Dia entre 1 e 31.", COR_DESPESA); return
            with self.db.transacao() as c:
                c.execute("INSERT INTO tb_assinaturas (nome,valor,dia_vencimento) VALUES (?,?,?)", (n, v, d))
            en.delete(0, "end"); ev.delete(0, "end"); edia.delete(0, "end")
            self._toast(lbl_as, "✓ Assinatura adicionada!")
            _refresh()

        ctk.CTkButton(rf, text="Adicionar", fg_color=COR_ROXO,
                      hover_color="#9366E0", text_color="#000",
                      height=46, corner_radius=RADIUS_BUTTON, font=FONT_BOLD,
                      width=120, command=_save).pack(side="left")
        _refresh()

    # ── PLANEJAMENTO ──────────────────────────────────────────────────────────

    def _pg_plan(self, p):
        ctk.CTkLabel(p, text="Metas & Planejamento", font=FONT_TITLE,
                     text_color=COR_TEXTO_FORTE).pack(anchor="w", padx=PAD_PAGE, pady=(32, 4))
        Divider(p).pack(fill="x", padx=PAD_PAGE, pady=(8, 20))

        form = ctk.CTkFrame(p, fg_color=COR_CARD, corner_radius=RADIUS_CARD,
                            border_width=1, border_color=COR_BORDAS)
        form.pack(fill="x", padx=PAD_PAGE, pady=(0, PAD_SECTION))
        ctk.CTkLabel(form, text="Novo Objetivo", font=FONT_BOLD,
                     text_color=COR_TEXTO_FORTE).pack(anchor="w", padx=PAD_CARD, pady=(PAD_CARD, 12))

        rf = ctk.CTkFrame(form, fg_color="transparent")
        rf.pack(fill="x", padx=PAD_CARD, pady=(0, 8))

        def _ent(parent, ph, w=0):
            e = ctk.CTkEntry(parent, placeholder_text=ph, height=46,
                             corner_radius=RADIUS_INPUT, font=FONT_REGULAR,
                             fg_color=COR_INPUT_BG, border_color=COR_BORDAS, border_width=1)
            if w: e.configure(width=w)
            return e

        enm = _ent(rf, "Nome do objetivo"); enm.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ea = _ent(rf, "Alvo R$", 150); ea.pack(side="left", padx=(0, 8))
        eac = _ent(rf, "Guardado R$", 150); eac.pack(side="left", padx=(0, 8))

        lbl_ms = ctk.CTkLabel(form, text="", font=FONT_SMALL)
        lbl_ms.pack(anchor="w", padx=PAD_CARD, pady=(0, 12))

        grid = ctk.CTkFrame(p, fg_color="transparent")
        grid.pack(fill="x", padx=PAD_PAGE)
        grid.columnconfigure((0, 1), weight=1, uniform="m")

        def _refresh():
            for w in grid.winfo_children(): w.destroy()
            metas = self.db.listar_metas()
            if not metas:
                ctk.CTkLabel(grid, text="Nenhuma meta.", font=FONT_SMALL,
                             text_color=COR_TEXTO).pack(pady=30); return
            for idx, (mid, nome, acu, alvo) in enumerate(metas):
                pct = min(acu / alvo, 1.0) if alvo > 0 else 0
                card = ctk.CTkFrame(grid, fg_color=COR_CARD, corner_radius=RADIUS_CARD,
                                    border_width=1, border_color=COR_BORDAS)
                card.grid(row=idx // 2, column=idx % 2, sticky="nsew", padx=6, pady=6)

                # Accent line
                bar_c = COR_SUCESSO if pct >= 1.0 else COR_PRIMARIA
                ctk.CTkFrame(card, fg_color=bar_c, height=3,
                             corner_radius=2).pack(fill="x", padx=16, pady=(12, 0))

                ctk.CTkLabel(card, text=nome, font=FONT_BOLD,
                             text_color=COR_TEXTO_FORTE).pack(anchor="w", padx=PAD_CARD, pady=(10, 4))
                pr = ctk.CTkFrame(card, fg_color="transparent")
                pr.pack(fill="x", padx=PAD_CARD, pady=(0, 6))
                ctk.CTkLabel(pr, text=f"R$ {acu:,.2f}", font=FONT_MONO,
                             text_color=COR_RECEITA).pack(side="left")
                ctk.CTkLabel(pr, text=f"/ R$ {alvo:,.2f}", font=FONT_TINY,
                             text_color=COR_TEXTO).pack(side="left", padx=6)
                ctk.CTkLabel(pr, text=f"{int(pct * 100)}%", font=FONT_BOLD,
                             text_color=bar_c).pack(side="right")

                barra = ctk.CTkProgressBar(card, progress_color=bar_c,
                                           fg_color=COR_BORDAS, height=8,
                                           corner_radius=4)
                barra.pack(fill="x", padx=PAD_CARD, pady=(0, 10))
                barra.set(pct)

                ar = ctk.CTkFrame(card, fg_color="transparent")
                ar.pack(fill="x", padx=PAD_CARD, pady=(0, 16))
                ea2 = _ent(ar, "Aportar R$")
                ea2.configure(height=34)
                ea2.pack(side="left", fill="x", expand=True, padx=(0, 6))
                ctk.CTkButton(ar, text="Aportar", fg_color=COR_SUCESSO,
                              hover_color="#2AB585", text_color="#000",
                              height=34, corner_radius=10, font=FONT_SMALL, width=80,
                              command=lambda m=mid, a=acu, e=ea2: [
                                  self.db.atualizar_meta(m, a + float(e.get().replace(",", ".") or 0)),
                                  _refresh()]).pack(side="left")

        def _save():
            n = enm.get().strip()
            try: alvo = float(ea.get().replace(",", ".")); ac = float(eac.get().replace(",", ".") or 0)
            except: self._toast(lbl_ms, "⚠ Valores inválidos.", COR_DESPESA); return
            if not n: self._toast(lbl_ms, "⚠ Nome obrigatório.", COR_DESPESA); return
            with self.db.transacao() as c:
                c.execute("INSERT INTO tb_metas (nome,valor_alvo,valor_acumulado) VALUES (?,?,?)", (n, alvo, ac))
            enm.delete(0, "end"); ea.delete(0, "end"); eac.delete(0, "end")
            self._toast(lbl_ms, "✓ Objetivo criado!")
            _refresh()

        ctk.CTkButton(rf, text="Criar Objetivo", fg_color=COR_SUCESSO,
                      hover_color="#2AB585", text_color="#000",
                      height=46, corner_radius=RADIUS_BUTTON, font=FONT_BOLD,
                      width=150, command=_save).pack(side="left")
        _refresh()


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = WealthEngine()
    app.mainloop()
