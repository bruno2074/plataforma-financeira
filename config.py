# config.py — Wealth Engine Design System v3 (Cyan Tech)

# ── BACKGROUNDS ──────────────────────────────────────────────────────────────
COR_FUNDO        = "#030B15"
COR_CARD         = "#0A1628"
COR_CARD_HOVER   = "#0F1D32"
COR_BORDAS       = "#1A2744"
COR_SIDEBAR      = "#04091A"
COR_ATIVO        = "#0C1A30"
COR_INPUT_BG     = "#0D1B2A"

# ── TEXTO ────────────────────────────────────────────────────────────────────
COR_TEXTO        = "#64748B"
COR_TEXTO_FORTE  = "#E2E8F0"
COR_TEXTO_MUTED  = "#475569"

# ── ACCENT COLORS ────────────────────────────────────────────────────────────
COR_PRIMARIA     = "#06B6D4"
COR_PRIMARIA_DIM = "#0891B2"
COR_SECUNDARIA   = "#8B5CF6"
COR_RECEITA      = "#22D3EE"
COR_DESPESA      = "#F43F5E"
COR_ROXO         = "#A78BFA"
COR_AMARELO      = "#FBBF24"
COR_SUCESSO      = "#34D399"

# ── GLOW ─────────────────────────────────────────────────────────────────────
COR_GLOW_CYAN    = "#06B6D4"

# ── TIPOGRAFIA ───────────────────────────────────────────────────────────────
FONT_HERO        = ("SF Pro Display", 32, "bold")
FONT_TITLE       = ("SF Pro Display", 24, "bold")
FONT_SUBTITLE    = ("SF Pro Display", 18, "bold")
FONT_BOLD        = ("SF Pro Display", 14, "bold")
FONT_REGULAR     = ("SF Pro Display", 13)
FONT_SMALL       = ("SF Pro Display", 11)
FONT_TINY        = ("SF Pro Display", 10)
FONT_MONO        = ("SF Mono", 12)
FONT_MONO_BIG    = ("SF Mono", 22, "bold")

# ── MATPLOTLIB ───────────────────────────────────────────────────────────────
MPL_BG           = "#030B15"
MPL_CARD         = "#0A1628"
MPL_GRID         = "#1A2744"
MPL_TEXTO        = "#64748B"
MPL_BRANCO       = "#E2E8F0"
MPL_CYAN         = "#06B6D4"
MPL_CYAN_LIGHT   = "#22D3EE"
MPL_ROSE         = "#F43F5E"
MPL_VIOLET       = "#8B5CF6"
MPL_EMERALD      = "#34D399"

# ── ESPAÇAMENTO ──────────────────────────────────────────────────────────────
PAD_PAGE         = 40
PAD_SECTION      = 24
PAD_CARD         = 20
RADIUS_CARD      = 16
RADIUS_INPUT     = 12
RADIUS_BUTTON    = 12

# ── BANCOS BRASILEIROS ───────────────────────────────────────────────────────
BANCOS_BR = [
    ("001", "Banco do Brasil"), ("033", "Santander"),
    ("104", "Caixa Econômica Federal"), ("237", "Bradesco"),
    ("341", "Itaú Unibanco"), ("260", "Nubank"),
    ("077", "Banco Inter"), ("336", "C6 Bank"),
    ("290", "PagSeguro / PagBank"), ("380", "PicPay"),
    ("212", "Banco Original"), ("756", "Sicoob"),
    ("748", "Sicredi"), ("422", "Safra"),
    ("633", "Rendimento"), ("655", "Neon / Votorantim"),
    ("070", "BRB"), ("246", "ABC Brasil"),
    ("745", "Citibank"), ("208", "BTG Pactual"),
    ("041", "Banrisul"), ("389", "Mercado Pago"),
    ("403", "Cora"), ("332", "Acesso Soluções"),
    ("197", "Stone"), ("000", "Outro"),
]
BANCOS_NOMES = [f"{cod} - {nome}" for cod, nome in BANCOS_BR]
    
