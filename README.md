# Salu Imóveis - Painel Administrativo

Painel de administração para gerenciar propostas, visitas, contatos e corretores.

## Funcionalidades

- Aprovar/Rejeitar propostas de compra e aluguel
- Direcionar propostas para corretores
- Gerenciar visitas agendadas
- Gerenciar contatos
- Visualizar estatísticas

## Requisitos

- Python 3.11+
- PostgreSQL (mesmo banco do portal principal)

## Instalação

```bash
pip install -r requirements.txt
cp .env.example .env
# Configure DATABASE_URL no .env
python -m uvicorn app.main:app --reload --port 8001
```

## Variáveis de Ambiente

```
DATABASE_URL=postgresql://...
SECRET_KEY=sua-chave-secreta
ADMIN_EMAIL=admin@saluimoveis.com
ADMIN_PASSWORD=senha-inicial
```
