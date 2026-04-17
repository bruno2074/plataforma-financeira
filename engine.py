# engine.py
import sqlcipher3.dbapi2 as sqlite3
import hashlib
import secrets
from contextlib import contextmanager


class MasterManager:
    """Banco central não-criptografado que rastreia usuários registrados no dispositivo."""

    def __init__(self):
        self.db_path = "master_censo.db"
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS tb_usuarios (
                id       INTEGER PRIMARY KEY,
                username TEXT    UNIQUE NOT NULL,
                salt     TEXT    NOT NULL
            )
        """)
        self.conn.commit()

    def contar_usuarios(self) -> int:
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM tb_usuarios")
        return cur.fetchone()[0]

    def registrar_usuario(self, username: str, salt: str):
        if self.contar_usuarios() >= 3:
            raise Exception("Limite de 3 contas atingido neste dispositivo.")
        cur = self.conn.cursor()
        try:
            cur.execute(
                "INSERT INTO tb_usuarios (username, salt) VALUES (?, ?)",
                (username.strip().lower(), salt),
            )
            self.conn.commit()
        except sqlite3.IntegrityError:
            raise Exception("Este nome de usuário já existe.")

    def obter_salt(self, username: str):
        cur = self.conn.cursor()
        cur.execute(
            "SELECT salt FROM tb_usuarios WHERE username = ?",
            (username.strip().lower(),),
        )
        res = cur.fetchone()
        return res[0] if res else None

    def listar_usuarios(self):
        cur = self.conn.cursor()
        cur.execute("SELECT username FROM tb_usuarios ORDER BY id")
        return [r[0] for r in cur.fetchall()]


class SecurityManager:
    @staticmethod
    def gerar_salt() -> str:
        return secrets.token_hex(32)

    @staticmethod
    def derivar_chave(senha: str, salt: str) -> str:
        return hashlib.pbkdf2_hmac(
            "sha512", senha.encode("utf-8"), salt.encode("utf-8"), 210_000
        ).hex()


class DatabaseManager:
    """Cofre individual criptografado com AES-256 via SQLCipher."""

    def __init__(self, db_path: str, chave_hex: str):
        self.db_path  = db_path
        self.chave_hex = chave_hex
        self.conn = sqlite3.connect(db_path)
        self._configurar_db()

    def _configurar_db(self):
        cur = self.conn.cursor()
        cur.execute(f"PRAGMA key=\"x'{self.chave_hex}'\"")
        cur.execute("PRAGMA foreign_keys = ON;")
        cur.execute("PRAGMA journal_mode = WAL;")

        cur.executescript("""
            CREATE TABLE IF NOT EXISTS tb_contas (
                id     INTEGER PRIMARY KEY AUTOINCREMENT,
                nome   TEXT    NOT NULL,
                tipo   TEXT,
                saldo  REAL    DEFAULT 0.0
            );

            CREATE TABLE IF NOT EXISTS tb_categorias (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                nome       TEXT UNIQUE,
                tipo_fluxo TEXT
            );

            CREATE TABLE IF NOT EXISTS tb_transacoes (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                conta_id       INTEGER REFERENCES tb_contas(id),
                categoria_id   INTEGER REFERENCES tb_categorias(id),
                valor          REAL,
                data_transacao DATE,
                descricao      TEXT
            );

            CREATE TABLE IF NOT EXISTS tb_metas (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                nome            TEXT,
                valor_alvo      REAL,
                valor_acumulado REAL DEFAULT 0.0
            );

            CREATE TABLE IF NOT EXISTS tb_assinaturas (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                nome            TEXT,
                valor           REAL,
                dia_vencimento  INTEGER DEFAULT 1,
                status          TEXT DEFAULT 'ATIVA'
            );

            CREATE TABLE IF NOT EXISTS tb_perfil (
                id              INTEGER PRIMARY KEY,
                cpf             TEXT,
                data_nascimento TEXT
            );
        """)

        # Seed categorias e conta padrão
        cur.execute(
            "INSERT OR IGNORE INTO tb_categorias (id, nome, tipo_fluxo) VALUES (1,'Receitas','RECEITA'),(2,'Despesas','DESPESA')"
        )
        cur.execute(
            "INSERT OR IGNORE INTO tb_contas (id, nome, tipo) VALUES (1,'Carteira Principal','Corrente')"
        )
        self.conn.commit()

    @contextmanager
    def transacao(self):
        cur = self.conn.cursor()
        cur.execute(f"PRAGMA key=\"x'{self.chave_hex}'\"")
        try:
            yield cur
            self.conn.commit()
        except Exception as exc:
            self.conn.rollback()
            raise exc
        finally:
            cur.close()

    # ── helpers de leitura ────────────────────────────────────────────────────

    def resumo_financeiro(self) -> dict:
        with self.transacao() as c:
            c.execute("SELECT COALESCE(SUM(valor),0) FROM tb_transacoes WHERE categoria_id=1")
            receitas = c.fetchone()[0]
            c.execute("SELECT COALESCE(SUM(valor),0) FROM tb_transacoes WHERE categoria_id=2")
            despesas = c.fetchone()[0]
            c.execute("SELECT COALESCE(SUM(valor),0) FROM tb_assinaturas WHERE status='ATIVA'")
            ass_total = c.fetchone()[0]
        return {
            "receitas":   receitas,
            "despesas":   despesas + ass_total,
            "patrimonio": receitas - despesas - ass_total,
            "assinaturas": ass_total,
        }

    def transacoes_por_mes(self) -> list:
        """Retorna [(mes_label, receita, despesa), ...] dos últimos 6 meses."""
        with self.transacao() as c:
            c.execute("""
                SELECT strftime('%m/%Y', data_transacao) AS mes,
                       SUM(CASE WHEN categoria_id=1 THEN valor ELSE 0 END) AS rec,
                       SUM(CASE WHEN categoria_id=2 THEN ABS(valor) ELSE 0 END) AS desp
                FROM tb_transacoes
                WHERE data_transacao IS NOT NULL
                GROUP BY mes
                ORDER BY data_transacao DESC
                LIMIT 6
            """)
            rows = c.fetchall()
        return list(reversed(rows)) if rows else []

    def listar_transacoes(self, conta_id=None, tipo=None, data_inicio=None, data_fim=None, limit=200) -> list:
        sql = """
            SELECT t.data_transacao, t.descricao, t.valor, c.nome, cat.nome
            FROM   tb_transacoes t
            JOIN   tb_contas      c   ON c.id   = t.conta_id
            JOIN   tb_categorias  cat ON cat.id = t.categoria_id
            WHERE  1=1
        """
        params = []
        if conta_id:
            sql += " AND t.conta_id = ?"
            params.append(conta_id)
        if tipo == "RECEITA":
            sql += " AND t.categoria_id = 1"
        elif tipo == "DESPESA":
            sql += " AND t.categoria_id = 2"
        if data_inicio:
            sql += " AND t.data_transacao >= ?"
            params.append(data_inicio)
        if data_fim:
            sql += " AND t.data_transacao <= ?"
            params.append(data_fim)
        sql += f" ORDER BY t.id DESC LIMIT {limit}"
        with self.transacao() as c:
            c.execute(sql, params)
            return c.fetchall()

    def listar_contas(self) -> list:
        with self.transacao() as c:
            c.execute("SELECT id, nome, tipo FROM tb_contas")
            return c.fetchall()

    def listar_assinaturas(self) -> list:
        with self.transacao() as c:
            c.execute("SELECT id, nome, valor, dia_vencimento, status FROM tb_assinaturas ORDER BY id DESC")
            return c.fetchall()

    def listar_metas(self) -> list:
        with self.transacao() as c:
            c.execute("SELECT id, nome, valor_acumulado, valor_alvo FROM tb_metas ORDER BY id DESC")
            return c.fetchall()

    def atualizar_meta(self, meta_id: int, novo_acumulado: float):
        with self.transacao() as c:
            c.execute("UPDATE tb_metas SET valor_acumulado=? WHERE id=?", (novo_acumulado, meta_id))

    def cancelar_assinatura(self, ass_id: int):
        with self.transacao() as c:
            c.execute("UPDATE tb_assinaturas SET status='CANCELADA' WHERE id=?", (ass_id,))

    def deletar_transacao(self, trans_id: int):
        with self.transacao() as c:
            c.execute("DELETE FROM tb_transacoes WHERE id=?", (trans_id,))
