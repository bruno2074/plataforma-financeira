# etl_engine.py
import pandas as pd
import sqlcipher3.dbapi2 as sqlite3
import os

class PipelineETL:
    def __init__(self, master_key, db_path='finance_core.db'):
        self.master_key = master_key
        self.db_path = db_path
        self.conn = self._conectar_cofre()

    def _conectar_cofre(self):
        """Estabelece a conexão cifrada em RAM."""
        if not os.path.exists(self.db_path):
            raise FileNotFoundError("Banco de dados não encontrado. Execute o app.py primeiro.")
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA key='{self.master_key}'")
        cursor.execute("PRAGMA foreign_keys = ON;") # Trava de segurança relacional
        return conn

    def _preparar_dimensoes_base(self):
        """Garante que existam contas e categorias para satisfazer as Foreign Keys."""
        cursor = self.conn.cursor()
        
        # Injeta Conta Padrão se não existir
        cursor.execute('''INSERT OR IGNORE INTO tb_contas (id, nome, tipo, saldo_inicial) 
                          VALUES (1, 'Conta Corrente Principal', 'CORRENTE', 0.0)''')
        
        # Injeta Categorias Genéricas
        categorias = [
            (1, 'Renda Principal', 'RECEITA'),
            (2, 'Alimentação', 'DESPESA'),
            (3, 'Despesas Fixas', 'DESPESA'),
            (4, 'Outros', 'DESPESA') # Categoria de fallback
        ]
        cursor.executemany('''INSERT OR IGNORE INTO tb_categorias (id, nome, tipo_fluxo) 
                              VALUES (?, ?, ?)''', categorias)
        self.conn.commit()

    def ingerir_csv(self, caminho_csv):
        """Processo Principal: Extract, Transform, Load."""
        print(f"[*] Iniciando ingestão do arquivo: {caminho_csv}")
        self._preparar_dimensoes_base()
        
        # 1. Extract
        df = pd.read_csv(caminho_csv)
        
        # 2. Transform
        # Converte a data para o formato nativo de banco (YYYY-MM-DD)
        df['Data'] = pd.to_datetime(df['Data'], format='%d/%m/%Y').dt.strftime('%Y-%m-%d')
        
        registros_preparados = []
        for index, row in df.iterrows():
            valor = float(row['Valor'])
            # Lógica simples de classificação para satisfazer as regras de negócio
            if valor > 0:
                categoria_id = 1 # Renda Principal
            else:
                categoria_id = 4 # Outros (Necessita refinamento via IA/Regras no futuro)
                
            registros_preparados.append((
                1, # conta_id (Sempre atrela à Conta Principal por enquanto)
                categoria_id,
                abs(valor), # O banco salva o valor absoluto, o "sinal" é dado pelo tipo de categoria
                row['Data'],
                row['Descricao']
            ))

        # 3. Load (Bulk Insert para máxima performance)
        cursor = self.conn.cursor()
        cursor.executemany('''
            INSERT INTO tb_transacoes (conta_id, categoria_id, valor, data_transacao, descricao)
            VALUES (?, ?, ?, ?, ?)
        ''', registros_preparados)
        
        self.conn.commit()
        print(f"[+] Ingestão concluída. {len(registros_preparados)} transações gravadas.")

# --- Bloco de Teste Isolado ---
if __name__ == '__main__':
    senha = input("Digite a Master Key do Banco para executar o ETL: ")
    etl = PipelineETL(master_key=senha)
    etl.ingerir_csv('extrato_teste.csv')