# Sistema de Rastreabilidade de Produtos (OMIE)

Este projeto tem como objetivo facilitar o registro de informações de **lote** e **validade** dos produtos associados a um **número de pedido** previamente emitido.

## Funcionalidades

- 🔍 Consulta de pedido por número
- 📦 Listagem automática de todos os itens do pedido
- 📝 Entrada dos campos de **lote** e **validade** para cada item
- ✅ Registro das informações ao final do processo

## 💡 Como funciona

1. O usuário insere o **número do pedido**.
2. O sistema consulta a API do ERP e retorna todos os itens vinculados ao pedido.
3. Para cada item retornado, o usuário é solicitado a preencher:
   - 📅 Data de validade
   - 🔢 Número do lote
   - Quantidade
     -Cada campo também já vem com o retorno da API caso esteja com o valor no Omie.
4. Ao final, o sistema pode:
   - Atualizar os dados diretamente no ERP via API

## 🛠️ Tecnologias utilizadas

- Python 3.12+
- Streamlit (interface)
- Requests (requisições HTTP)
- API REST do ERP

## ✅ Pré-requisitos

- Ter as **credenciais de acesso** da API configuradas (APP_KEY e APP_SECRET)
- Python instalado localmente
