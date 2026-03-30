# database_core.py
import sqlcipher3.dbapi2 as sqlite3

def init_db(master_key):
    # Cria ou conecta ao banco de dados cifrado
    conn = sqlite3.connect('finance_core.db')
    cursor = conn.cursor()

    # 1. Destrava o banco com a chave criptográfica (AES-256)
    cursor.execute(f"PRAGMA key='{master_key}'")
    
    # 2. Força a integridade referencial das chaves estrangeiras
    cursor.execute("PRAGMA foreign_keys = ON;")

    # 3. DDL: Estruturação das Tabelas
    cursor.executescript('''
        -- Dimensão: Origem do Dinheiro
        CREATE TABLE IF NOT EXISTS tb_contas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            tipo TEXT NOT NULL,
            saldo_inicial REAL DEFAULT 0.0
        );

        -- Dimensão: Taxonomia
        CREATE TABLE IF NOT EXISTS tb_categorias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            tipo_fluxo TEXT CHECK(tipo_fluxo IN ('RECEITA', 'DESPESA')) NOT NULL
        );

        -- Fato: Movimentação Diária
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

        -- Fato: Orçamentos
        CREATE TABLE IF NOT EXISTS tb_orcamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            categoria_id INTEGER NOT NULL,
            teto_gasto REAL NOT NULL,
            mes_referencia TEXT NOT NULL, -- Formato YYYY-MM
            FOREIGN KEY (categoria_id) REFERENCES tb_categorias(id) ON DELETE CASCADE
        );

        -- Dimensão: Metas Financeiras (Com Ring-fencing opcional)
        CREATE TABLE IF NOT EXISTS tb_metas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conta_id INTEGER, -- Pode ser NULL se não for atrelado a uma conta física específica
            nome TEXT NOT NULL,
            valor_alvo REAL NOT NULL,
            prazo_data DATE,
            FOREIGN KEY (conta_id) REFERENCES tb_contas(id) ON DELETE SET NULL
        );

        -- Dimensão: Posição de Ativos
        CREATE TABLE IF NOT EXISTS tb_investimentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conta_id INTEGER NOT NULL, -- Ex: Conta Corretora X
            ticker TEXT NOT NULL UNIQUE,
            quantidade REAL NOT NULL,
            preco_medio REAL NOT NULL,
            FOREIGN KEY (conta_id) REFERENCES tb_contas(id) ON DELETE RESTRICT
        );

        -- Fato/Série Temporal: Histórico de Cotações (Estrutura Avançada)
        CREATE TABLE IF NOT EXISTS tb_historico_precos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            investimento_id INTEGER NOT NULL,
            data_cotacao DATE NOT NULL,
            preco_fechamento REAL NOT NULL,
            FOREIGN KEY (investimento_id) REFERENCES tb_investimentos(id) ON DELETE CASCADE
        );
    ''')

    conn.commit()
    conn.close()
    print("[+] Core Relacional e Criptografia inicializados com sucesso.")
