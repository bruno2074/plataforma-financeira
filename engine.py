# engine.py
import hashlib
import secrets
import time
import re
from datetime import datetime
from contextlib import contextmanager
 
# Tenta sqlcipher3 primeiro, fallback para sqlite3
try:
    import sqlcipher3.dbapi2 as sqlite3
    SQLCIPHER_DISPONIVEL = True
except ImportError:
    import sqlite3
    SQLCIPHER_DISPONIVEL = False
 
 
# ─────────────────────────────────────────────────────────────────────────────
#  VALIDADORES
# ─────────────────────────────────────────────────────────────────────────────
 
class Validador:
    """Validações de input — CPF, data de nascimento, força de senha."""
 
    @staticmethod
    def validar_cpf(cpf: str) -> tuple[bool, str]:
        """Valida CPF brasileiro usando algoritmo oficial dos dígitos verificadores."""
        cpf = re.sub(r'\D', '', cpf)
 
        if len(cpf) != 11:
            return False, "CPF deve ter 11 dígitos."
 
        # Rejeita sequências repetidas (ex: 111.111.111-11)
        if cpf == cpf[0] * 11:
            return False, "CPF inválido (sequência repetida)."
 
        # Cálculo do primeiro dígito verificador
        soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
        resto = (soma * 10) % 11
        d1 = 0 if resto >= 10 else resto
        if d1 != int(cpf[9]):
            return False, "CPF inválido (dígito verificador)."
 
        # Cálculo do segundo dígito verificador
        soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
        resto = (soma * 10) % 11
        d2 = 0 if resto >= 10 else resto
        if d2 != int(cpf[10]):
            return False, "CPF inválido (dígito verificador)."
 
        return True, "CPF válido."
 
    @staticmethod
    def formatar_cpf(cpf: str) -> str:
        """Retorna CPF formatado: XXX.XXX.XXX-XX"""
        cpf = re.sub(r'\D', '', cpf)
        if len(cpf) == 11:
            return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"
        return cpf
 
    @staticmethod
    def validar_data_nascimento(data: str) -> tuple[bool, str]:
        """Valida data no formato DD/MM/AAAA."""
        data = data.strip()
 
        # Verifica formato
        if not re.match(r'^\d{2}/\d{2}/\d{4}$', data):
            return False, "Use o formato DD/MM/AAAA."
 
        try:
            dt = datetime.strptime(data, "%d/%m/%Y")
        except ValueError:
            return False, "Data inexistente."
 
        # Data no futuro
        if dt > datetime.now():
            return False, "Data não pode ser no futuro."
 
        # Idade mínima 10 anos, máxima 120
        idade = (datetime.now() - dt).days / 365.25
        if idade < 10:
            return False, "Idade mínima: 10 anos."
        if idade > 120:
            return False, "Data implausível."
 
        return True, "Data válida."
 
    @staticmethod
    def validar_senha(senha: str) -> tuple[bool, str]:
        """Verifica força mínima da senha."""
        if len(senha) < 8:
            return False, "Mínimo 8 caracteres."
        if not re.search(r'[A-Z]', senha):
            return False, "Inclua ao menos 1 letra maiúscula."
        if not re.search(r'[a-z]', senha):
            return False, "Inclua ao menos 1 letra minúscula."
        if not re.search(r'\d', senha):
            return False, "Inclua ao menos 1 número."
        if not re.search(r'[!@#$%^&*(),.?\":{}|<>\-_=+\[\]\/\\~`]', senha):
            return False, "Inclua ao menos 1 caractere especial (!@#$%...)."
        return True, "Senha forte."
 
    @staticmethod
    def validar_usuario(usuario: str) -> tuple[bool, str]:
        """Valida nome de usuário."""
        usuario = usuario.strip()
        if len(usuario) < 3:
            return False, "Mínimo 3 caracteres."
        if len(usuario) > 30:
            return False, "Máximo 30 caracteres."
        if not re.match(r'^[a-zA-Z0-9._]+$', usuario):
            return False, "Use apenas letras, números, ponto e underscore."
        return True, "Usuário válido."
 
 
# ─────────────────────────────────────────────────────────────────────────────
#  PROTEÇÃO BRUTE FORCE
# ─────────────────────────────────────────────────────────────────────────────
 
class BruteForceGuard:
    """Rate limiter para tentativas de login em memória."""
 
    MAX_TENTATIVAS = 5
    LOCKOUT_SEGUNDOS = 300  # 5 minutos
 
    def __init__(self):
        # {username: {"tentativas": int, "lockout_ate": float}}
        self._registro: dict[str, dict] = {}
 
    def esta_bloqueado(self, username: str) -> tuple[bool, int]:
        """Retorna (bloqueado, segundos_restantes)."""
        username = username.strip().lower()
        reg = self._registro.get(username)
        if not reg:
            return False, 0
 
        if reg["lockout_ate"] and time.time() < reg["lockout_ate"]:
            restante = int(reg["lockout_ate"] - time.time())
            return True, restante
 
        # Se o lockout expirou, resetar
        if reg["lockout_ate"] and time.time() >= reg["lockout_ate"]:
            self._registro.pop(username, None)
            return False, 0
 
        return False, 0
 
    def registrar_falha(self, username: str) -> tuple[bool, int]:
        """Registra uma tentativa falha. Retorna (bloqueou_agora, tentativas_restantes)."""
        username = username.strip().lower()
        if username not in self._registro:
            self._registro[username] = {"tentativas": 0, "lockout_ate": None}
 
        self._registro[username]["tentativas"] += 1
        t = self._registro[username]["tentativas"]
 
        if t >= self.MAX_TENTATIVAS:
            self._registro[username]["lockout_ate"] = time.time() + self.LOCKOUT_SEGUNDOS
            return True, 0
 
        return False, self.MAX_TENTATIVAS - t
 
    def registrar_sucesso(self, username: str):
        """Limpa o registro após login bem-sucedido."""
        self._registro.pop(username.strip().lower(), None)
 
 
# ─────────────────────────────────────────────────────────────────────────────
#  MASTER MANAGER
# ─────────────────────────────────────────────────────────────────────────────
 
class MasterManager:
    """Banco central que rastreia usuários registrados no dispositivo.
    Armazena salt + hash de verificação da senha (NÃO a senha em si)."""
 
    def __init__(self):
        self.db_path = "master_censo.db"
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS tb_usuarios (
                id          INTEGER PRIMARY KEY,
                username    TEXT    UNIQUE NOT NULL,
                salt        TEXT    NOT NULL,
                senha_hash  TEXT    NOT NULL
            )
        """)
        self.conn.commit()
        self._migrar_se_necessario()
 
    def _migrar_se_necessario(self):
        """Adiciona coluna senha_hash se não existir (migração de versão anterior)."""
        cur = self.conn.cursor()
        cur.execute("PRAGMA table_info(tb_usuarios)")
        colunas = [row[1] for row in cur.fetchall()]
        if "senha_hash" not in colunas:
            cur.execute("ALTER TABLE tb_usuarios ADD COLUMN senha_hash TEXT DEFAULT ''")
            self.conn.commit()
 
    def contar_usuarios(self) -> int:
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM tb_usuarios")
        return cur.fetchone()[0]
 
    def registrar_usuario(self, username: str, salt: str, senha_hash: str):
        if self.contar_usuarios() >= 3:
            raise Exception("Limite de 3 contas atingido neste dispositivo.")
        cur = self.conn.cursor()
        try:
            cur.execute(
                "INSERT INTO tb_usuarios (username, salt, senha_hash) VALUES (?, ?, ?)",
                (username.strip().lower(), salt, senha_hash),
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
 
    def obter_senha_hash(self, username: str):
        cur = self.conn.cursor()
        cur.execute(
            "SELECT senha_hash FROM tb_usuarios WHERE username = ?",
            (username.strip().lower(),),
        )
        res = cur.fetchone()
        return res[0] if res else None
 
    def verificar_senha(self, username: str, senha: str) -> bool:
        """Verifica se a senha digitada corresponde ao hash armazenado."""
        salt = self.obter_salt(username)
        if not salt:
            return False
 
        hash_armazenado = self.obter_senha_hash(username)
        if not hash_armazenado:
            return False
 
        chave_derivada = SecurityManager.derivar_chave(senha, salt)
        hash_tentativa = hashlib.sha256(chave_derivada.encode()).hexdigest()
 
        # Comparação em tempo constante (anti-timing attack)
        return secrets.compare_digest(hash_tentativa, hash_armazenado)
 
    def listar_usuarios(self):
        cur = self.conn.cursor()
        cur.execute("SELECT username FROM tb_usuarios ORDER BY id")
        return [r[0] for r in cur.fetchall()]
 
 
# ─────────────────────────────────────────────────────────────────────────────
#  SECURITY MANAGER
# ─────────────────────────────────────────────────────────────────────────────
 
class SecurityManager:
    @staticmethod
    def gerar_salt() -> str:
        return secrets.token_hex(32)
 
    @staticmethod
    def derivar_chave(senha: str, salt: str) -> str:
        return hashlib.pbkdf2_hmac(
            "sha512", senha.encode("utf-8"), salt.encode("utf-8"), 210_000
        ).hex()
 
    @staticmethod
    def gerar_hash_verificacao(chave_derivada: str) -> str:
        """Gera hash SHA-256 da chave derivada para armazenar como verificação."""
        return hashlib.sha256(chave_derivada.encode()).hexdigest()
 
 
# ─────────────────────────────────────────────────────────────────────────────
#  DATABASE MANAGER
# ─────────────────────────────────────────────────────────────────────────────
 
class DatabaseManager:
    """Cofre individual do usuário. Se sqlcipher3 estiver disponível,
    usa criptografia AES-256. Caso contrário, usa sqlite3 padrão."""
 
    def __init__(self, db_path: str, chave_hex: str):
        self.db_path   = db_path
        self.chave_hex = chave_hex
        self.conn = sqlite3.connect(db_path)
        self._configurar_db()
 
    def _configurar_db(self):
        cur = self.conn.cursor()
        if SQLCIPHER_DISPONIVEL:
            cur.execute(f"PRAGMA key=\"x'{self.chave_hex}'\"")
        cur.execute("PRAGMA foreign_keys = ON;")
        cur.execute("PRAGMA journal_mode = WAL;")
 
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS tb_contas (
                id     INTEGER PRIMARY KEY AUTOINCREMENT,
                nome   TEXT    NOT NULL,
                codigo TEXT    DEFAULT '',
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
                data_transacao TEXT,
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
 
        cur.execute(
            "INSERT OR IGNORE INTO tb_categorias (id, nome, tipo_fluxo) "
            "VALUES (1,'Receitas','RECEITA'),(2,'Despesas','DESPESA')"
        )
        cur.execute(
            "INSERT OR IGNORE INTO tb_contas (id, nome, codigo, tipo) "
            "VALUES (1,'Carteira Principal','000','Corrente')"
        )
        self.conn.commit()
 
    @contextmanager
    def transacao(self):
        cur = self.conn.cursor()
        if SQLCIPHER_DISPONIVEL:
            cur.execute(f"PRAGMA key=\"x'{self.chave_hex}'\"")
        try:
            yield cur
            self.conn.commit()
        except Exception as exc:
            self.conn.rollback()
            raise exc
        finally:
            cur.close()
 
    # ── Helpers de leitura ────────────────────────────────────────────────────
 
    def resumo_financeiro(self) -> dict:
        with self.transacao() as c:
            c.execute("SELECT COALESCE(SUM(valor),0) FROM tb_transacoes WHERE categoria_id=1")
            receitas = c.fetchone()[0]
            c.execute("SELECT COALESCE(SUM(valor),0) FROM tb_transacoes WHERE categoria_id=2")
            despesas = c.fetchone()[0]
            c.execute("SELECT COALESCE(SUM(valor),0) FROM tb_assinaturas WHERE status='ATIVA'")
            ass_total = c.fetchone()[0]
        return {
            "receitas":    receitas,
            "despesas":    abs(despesas) + ass_total,
            "patrimonio":  receitas - abs(despesas) - ass_total,
            "assinaturas": ass_total,
        }
 
    def transacoes_agrupadas(self) -> list:
        """Retorna [(data_str, receita, despesa), ...] agrupados por dia."""
        with self.transacao() as c:
            c.execute("""
                SELECT data_transacao,
                       SUM(CASE WHEN categoria_id=1 THEN valor ELSE 0 END) AS rec,
                       SUM(CASE WHEN categoria_id=2 THEN ABS(valor) ELSE 0 END) AS desp
                FROM tb_transacoes
                WHERE data_transacao IS NOT NULL AND data_transacao != ''
                GROUP BY data_transacao
                ORDER BY data_transacao ASC
            """)
            return c.fetchall()
 
    def listar_transacoes(self, conta_id=None, tipo=None,
                          data_inicio=None, data_fim=None, limit=500) -> list:
        sql = """
            SELECT t.id, t.data_transacao, t.descricao, t.valor, c.nome, cat.nome
            FROM   tb_transacoes t
            LEFT JOIN tb_contas      c   ON c.id   = t.conta_id
            LEFT JOIN tb_categorias  cat ON cat.id = t.categoria_id
            WHERE  1=1
        """
        params: list = []
        if conta_id and conta_id != 0:
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
        sql += f" ORDER BY t.id DESC LIMIT ?"
        params.append(limit)
        with self.transacao() as c:
            c.execute(sql, params)
            return c.fetchall()
 
    def inserir_transacao(self, conta_id: int, categoria_id: int,
                          valor: float, data: str, descricao: str):
        with self.transacao() as c:
            c.execute(
                "INSERT INTO tb_transacoes "
                "(conta_id, categoria_id, valor, data_transacao, descricao) "
                "VALUES (?,?,?,?,?)",
                (conta_id, categoria_id, valor, data, descricao)
            )
 
    def listar_contas(self) -> list:
        with self.transacao() as c:
            c.execute("SELECT id, nome, tipo, codigo FROM tb_contas ORDER BY id")
            return c.fetchall()
 
    def listar_assinaturas(self) -> list:
        with self.transacao() as c:
            c.execute("SELECT id, nome, valor, dia_vencimento, status "
                      "FROM tb_assinaturas ORDER BY id DESC")
            return c.fetchall()
 
    def listar_metas(self) -> list:
        with self.transacao() as c:
            c.execute("SELECT id, nome, valor_acumulado, valor_alvo "
                      "FROM tb_metas ORDER BY id DESC")
            return c.fetchall()
 
    def atualizar_meta(self, meta_id: int, novo_acumulado: float):
        with self.transacao() as c:
            c.execute("UPDATE tb_metas SET valor_acumulado=? WHERE id=?",
                      (novo_acumulado, meta_id))
 
    def cancelar_assinatura(self, ass_id: int):
        with self.transacao() as c:
            c.execute("UPDATE tb_assinaturas SET status='CANCELADA' WHERE id=?",
                      (ass_id,))
 
    def deletar_transacao(self, trans_id: int):
        with self.transacao() as c:
            c.execute("DELETE FROM tb_transacoes WHERE id=?", (trans_id,))
 
    def obter_transacoes_por_tipo(self, tipo: str) -> list:
        """Retorna transações filtradas por tipo (RECEITA ou DESPESA)."""
        cat_id = 1 if tipo == "RECEITA" else 2
        with self.transacao() as c:
            c.execute(
                "SELECT t.id, t.data_transacao, t.descricao, t.valor, c.nome "
                "FROM tb_transacoes t "
                "LEFT JOIN tb_contas c ON c.id = t.conta_id "
                "WHERE t.categoria_id = ? ORDER BY t.id DESC",
                (cat_id,)
            )
            return c.fetchall()
 
