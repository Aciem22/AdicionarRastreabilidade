import calendar
import re
import sys
import requests
import streamlit as st
from datetime import date, datetime
import threading
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import tempfile
import pandas as pd
from utils.api_omie import consultar_pedido, alterar_pedido
from utils.sheets import carregar_lotes_validade

st.set_page_config(page_title="Cadastro de Lotes", layout="wide")

# Se ainda não carregou a planilha, carrega uma vez
if "df_lotes" not in st.session_state:
    st.session_state.df_lotes = carregar_lotes_validade()

# Botão manual para recarregar a planilha
if st.button("🔄 Recarregar Planilha"):
    st.session_state.df_lotes = carregar_lotes_validade()
    st.success("Planilha recarregada com sucesso!")

# Usa os dados sempre do session_state
df_lotes = st.session_state.df_lotes

# Carrega os dados da planilha uma vez só
df_lotes = carregar_lotes_validade()

st.title("🔍 Cadastro de Rastreabilidade")

numero_pedido = st.text_input("Digite o número do pedido:")

if numero_pedido:
    # Evita duplicação usando session_state
    if "dados_pedido" not in st.session_state or st.session_state.get("pedido_atual") != numero_pedido:
        with st.spinner("Consultando pedido..."):
            st.session_state["dados_pedido"] = consultar_pedido(numero_pedido)
            st.session_state["pedido_atual"] = numero_pedido

    dados = st.session_state["dados_pedido"]

    # Mostra retorno no terminal
    print("===== RETORNO DA API =====")
    print(json.dumps(dados, indent=2, ensure_ascii=False))
    print("===========================")

    cabecalho = dados.get("pedido_venda_produto", {}).get("cabecalho", {})
    etapa = cabecalho.get("etapa", "")

    if etapa in ["60", "70"]:
        st.warning("Este pedido já foi faturado e não pode ser alterado!")
        st.stop()

    itens = dados.get("pedido_venda_produto", {}).get("det", [])
    codigo_pedido = cabecalho.get("codigo_pedido", "")

    st.markdown(f"### Pedido Nº {numero_pedido} — {len(itens)} item(ns)")
    st.markdown("""<div style="background-color: rgb(23 45 67); color: rgb(176 235 255);padding: 12px;border-radius: 6px;border-left: 5px solid #0288d1;font-size: 16px;">
        🚨 O campo de <b>Validade</b> está no padrão ISO - Ano/Mês/Dia.</div> <br>""", unsafe_allow_html=True)

    # Ordena apenas para exibição
    itens_com_indices = list(enumerate(itens))
    itens_exibir = sorted(itens_com_indices, key=lambda x: x[1].get("produto", {}).get("descricao", "").lower())

    with st.form("form_lotes"):
        valores_digitados = {}
        excluir_itens = []

        for idx_visual, (idx_real, item) in enumerate(itens_exibir):
            produto = item.get("produto", {})
            descricao = produto.get("descricao", "")
            codigo = produto.get("codigo", "")
            quantidade = produto.get("quantidade", 0)

            rastreabilidade = item.get("rastreabilidade", {})
            lote = rastreabilidade.get("numeroLote", "")
            validade = rastreabilidade.get("dataValidadeLote", "")

            expandir = (lote == "" or validade == "")

            with st.expander(f"{descricao} ({codigo})", expanded=expandir):
                col1, col2, col3, col4, col5 = st.columns([4,3,3,2,1])
                with col1:
                    st.text(f"{descricao} ({codigo})")
                with col2:
                    try:
                        filtro_lote = df_lotes.loc[df_lotes["Código do Produto"] == codigo, "LOTE"]
                        lote_apostrofo = filtro_lote.values[0] if not filtro_lote.empty else ""
                        lote_sel = lote_apostrofo[1:] if lote_apostrofo else ""
                        lote_input = st.text_input("Lote", value=lote_sel, key=f"lote_sel_{idx_real}")
                        valores_digitados[f"lote_{idx_real}"] = lote_input
                    except (ValueError, AttributeError):
                        lote_input = st.text_input("Lote", key=f"lote_sel_{idx_real}")
                        valores_digitados[f"lote_{idx_real}"] = ""

                with col3:
                    try:
                        filtro_validade = df_lotes.loc[df_lotes["Código do Produto"] == codigo, "VALIDADE"]
                        if not filtro_validade.empty:
                            opcoes_validade = [filtro_validade.values[0], "INDEFINIDO", "NOVA DATA"]
                            escolha = st.selectbox("Validade", opcoes_validade, key=f"validade_opcao_{idx_real}")

                            if escolha in ["INDEFINIDO", "S/V", ""]:
                                valores_digitados[f"validade_{idx_real}"] = "INDEFINIDO"
                            elif escolha == "NOVA DATA":
                                nova = st.date_input("Digite nova data", key=f"validade_input_{idx_real}")
                                valores_digitados[f"validade_{idx_real}"] = nova if nova else None
                            else:
                                mes, ano = escolha.split("/")
                                mes = int(mes)
                                ano = int(ano)
                                if ano < 100: ano += 2000
                                ultimo_dia = calendar.monthrange(ano, mes)[1]
                                valores_digitados[f"validade_{idx_real}"] = date(ano, mes, ultimo_dia)
                        else:
                            valores_digitados[f"validade_{idx_real}"] = "INDEFINIDO"
                    except Exception as e:
                        st.warning(f"Erro ao tratar validade do produto {codigo}: {e}")

                with col4:
                    valores_digitados[f"qtd_{idx_real}"] = st.number_input("Qtd", value=quantidade, key=f"qtd_{idx_real}")
                with col5:
                    excluir = st.checkbox("❌", key=f"excluir_{idx_real}")
                    excluir_itens.append(excluir)

        st.markdown("<hr style='border: none; height: 1px; background-color: #5e5e5e;'>", unsafe_allow_html=True)

        frete = cabecalho.get("frete", {})
        quantidade_caixas = st.number_input("Quantidade de caixas", value=frete.get("quantidade_volumes", 0), step=1)

        if st.form_submit_button("💾 Salvar Dados"):
            # Monta novos_produtos usando indices corretos
            novos_produtos = []
            for idx_visual, (idx_real, item) in enumerate(itens_exibir):
                produto = item.get("produto", {})
                ide = item.get("ide", {})

                ide_final = {
                    "codigo_item": ide.get("codigo_item"),
                    "simples_nacional": ide.get("simples_nacional"),
                }
                if excluir_itens[idx_visual]:
                    ide_final["acao_item"] = "E"

                validade = valores_digitados.get(f"validade_{idx_real}")
                if validade in [None, "", "INDEFINIDO"]:
                    rastreabilidade = {
                        "qtdeProdutoLote": valores_digitados.get(f"qtd_{idx_real}", 0)
                    }
                else:
                    validade_str = validade.strftime("%d/%m/%Y")
                    fabricacao_str = date(validade.year - 3, validade.month, 1).strftime("%d/%m/%Y")
                    rastreabilidade = {
                        "numeroLote": valores_digitados.get(f"lote_{idx_real}", ""),
                        "qtdeProdutoLote": valores_digitados.get(f"qtd_{idx_real}", 0),
                        "dataFabricacaoLote": fabricacao_str,
                        "dataValidadeLote": validade_str
                    }

                novos_produtos.append({
                    "ide": ide_final,
                    "produto": produto,
                    "rastreabilidade": rastreabilidade
                })

            # 🔹 Mostra o JSON completo apenas uma vez no terminal
            payload = {
                "cabecalho": {"codigo_pedido": codigo_pedido},
                "frete": {"quantidade_volumes": quantidade_caixas, "especie_volumes": "CAIXAS"},
                "det": novos_produtos
            }

            # Chama a função da API
            resultado = alterar_pedido(codigo_pedido, novos_produtos, quantidade_caixas)

            if resultado.get("faultstring"):
                st.error(f"Erro ao alterar pedido: {resultado['faultstring']}")
            else:
                st.success("Pedido alterado com sucesso!")
else:
    st.error("Pedido não encontrado ou resposta inválida da API.")

                    
