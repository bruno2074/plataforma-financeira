# plataforma-financeira

expansões necessárias --> 
customtkinter
pandas
matplotlib
sqlcipher3-wheels
platly 5.24.1 
kaleido 0.2.1

code extensions necessárias  --> sudo snap install code --classic
code --install-extension ms-python.python
code --install-extension ms-python.vscode-pylance
code --install-extension qwtel.sqlite-viewer
code --install-extension charliermarsh.ruff

# 🛡️ Wealth Engine (Elliot.OS) - Plataforma Financeira Criptografada

## 🔭 Visão Geral
O **Wealth Engine** é uma plataforma de gestão de patrimônio (*Wealth Management*) nativa para desktop, construída em Python. Diferente de aplicações web baseadas em nuvem, este software foi arquitetado sob a premissa do **Data Locality** e do **Zero-Knowledge**. Seus dados financeiros não transitam por APIs de terceiros e não são armazenados em texto plano. A plataforma integra um motor de ingestão de dados (ETL), um banco de dados relacional cifrado e visualização de dados em alta performance estritamente na memória RAM.

## ⚙️ Arquitetura e Decisões de Engenharia

* **Segurança (Zero-Knowledge & AES-256):** O banco de dados SQLite é criptografado em repouso utilizando o driver C++ `sqlcipher3`. A chave mestre (*Master Key*) nunca é salva no disco físico ou no código-fonte; ela reside apenas na memória volátil durante a sessão do usuário.
* **Pipeline ETL Resiliente:** Ingestão automatizada de extratos bancários (.CSV) via `Pandas`. O motor implementa *Input Sanitization* (bypass de BOM e Whitespaces invisíveis) e *Exception Handling* rigoroso para evitar *Information Disclosure* em caso de falha de parsing.
* **Interface SPA (Single Page Application) Nativa:** Construída com `CustomTkinter`, a navegação utiliza o conceito de *State Routing*, destruindo e recriando matrizes visuais (*Grid System*) na mesma janela, otimizando o consumo de RAM e evitando o overhead de múltiplas janelas do SO.
* **Rasterização Gráfica Isolada:** Os dashboards interativos não dependem de *Headless Browsers* (que conflitam com o sandboxing do Linux/Ubuntu). O motor utiliza `Plotly` renderizado em um motor C++ estático (`Kaleido 0.2.1`), convertendo vetores HTML/JS em matrizes de pixels em tempo real, garantindo que o dado financeiro nunca saia do escopo da aplicação.

## 🛠️ Stack Tecnológica
* **Core:** Python 3.12
* **Persistência & AppSec:** SQLite3 + SQLCipher (AES-256)
* **Engenharia de Dados (ETL):** Pandas
* **Interface Gráfica (GUI):** CustomTkinter
* **Visualização de Dados:** Plotly + Kaleido (C++ Engine) + Pillow (PIL)

## 📂 Estrutura de Módulos
- `database_core.py`: Motor de inicialização do DDL e injeção do PRAGMA criptográfico.
- `etl_engine.py`: Pipeline autônomo de Extração, Transformação e Carga de dados massivos.
- `app.py`: Camada de Apresentação (View) e Controlador de Roteamento de Estados.

## 🚀 Como Executar (Ambiente Linux/Ubuntu)

1. **Clone o repositório:**
   ```bash
   git clone [https://github.com/SEU_USUARIO/wealth-engine.git](https://github.com/SEU_USUARIO/wealth-engine.git)
   cd wealth-engine
2. Crie e ative o ambiente virtual (Isolamento de SO):

Bash
python3 -m venv .venv
source .venv/bin/activate

3. Injete as dependências (Version Pinning estrito aplicado):

Bash
pip install customtkinter pandas sqlcipher3-wheels Pillow plotly==5.24.1 kaleido==0.2.1

4. Inicie a Plataforma:
Bash
python app.py

