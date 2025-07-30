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

st.set_page_config(page_title="Cadastro de Lotes", layout="wide")

def carregar_lotes_validade():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], scope)
    client = gspread.authorize(creds)
    planilha = client.open("Controle Lote e Val Rastreabilidade")
    aba = planilha.worksheet("Lotes")
    dados = aba.get_all_records()
    df = pd.DataFrame(dados)

    # 🔧 Forçando tipo string para evitar erro do Arrow
    df["Código do Produto"] = df["Código do Produto"].astype(str)
    df["LOTE"] = df["LOTE"].astype(str).apply(lambda x:f"'{x}")
    df["VALIDADE"] = df["VALIDADE"].astype(str)

    return df

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

#def ping_servidor():
   # while True:
        #print(f"🔄 Ping enviado às {time.strftime('%H:%M:%S')}")
       # time.sleep(60)  # ping a cada 60 segundos

# Garante que só uma thread seja iniciada
#if "ping_thread" not in globals():
    #ping_thread = threading.Thread(target=ping_servidor, daemon=True)
    #ping_thread.start()


# Configurações da API
APP_KEY = st.secrets["APP_KEY"]
APP_SECRET = st.secrets["APP_SECRET"]

# Função para consultar o pedido na API da Omie
def consultar_pedido(numero_pedido):
    url = "https://app.omie.com.br/api/v1/produtos/pedido/"
    payload = {
        "call": "ConsultarPedido",
        "app_key": APP_KEY,
        "app_secret": APP_SECRET,
        "param": [
            {"numero_pedido": numero_pedido}
        ]
    }
    response = requests.post(url, json=payload)
    return response.json()

    codigo_pedido = dados["pedido_venda_produto"][0].get("codigo_pedido", "")
    return dados, codigo_pedido

# Função para alterar o pedido na API da Omie
def alterar_pedido(codigo_pedido, novos_produtos, quantidade_caixas):
    url = "https://app.omie.com.br/api/v1/produtos/pedido/"
    payload = {
        "call": "AlterarPedidoVenda",
        "app_key": APP_KEY,
        "app_secret": APP_SECRET,
          "param": {
            "cabecalho": {
                "codigo_pedido": codigo_pedido,  # Agora o codigo_pedido está dentro de cabecalho
            },
            "frete":{
                "quantidade_volumes":quantidade_caixas,
                "especie_volumes":"CAIXAS"
            },
            "det": novos_produtos
        }
    }
    response = requests.post(url, json=payload)
    return response.json()
    #resultado = response.json()
    #st.write("🔍 Resposta da API Omie:", resultado)
    #return resultado

st.title("🔍 Cadastro de Rastreabilidade")

numero_pedido = st.text_input("Digite o número do pedido:")

if numero_pedido:
    with st.spinner("Consultando pedido..."):
        dados = consultar_pedido(numero_pedido)
        cabecalho = dados.get("pedido_venda_produto", {}).get("cabecalho",{})
        etapa = cabecalho.get("etapa","")
        
    if etapa =="60" or etapa=="70":
            st.warning("Este pedido já foi faturado e não pode ser alterado!")
            st.stop()
            st.spinner()
    else:
    
        if "pedido_venda_produto" in dados:
            pedido = dados["pedido_venda_produto"]
            itens = pedido.get("det", [])
            codigo_pedido = pedido.get("cabecalho", {}).get("codigo_pedido")  # 👈 Aqui está o código que precisamos
    
    
            st.markdown(f"### Pedido Nº {numero_pedido} — {len(itens)} item(ns)")
            st.markdown("""<div style="background-color: rgb(23 45 67); color: rgb(176 235 255);padding: 12px;border-radius: 6px;border-left: 5px solid #0288d1;font-size: 16px;">
                   🚨 O campo de <b>Validade</b> está no padrão ISO - Ano/Mês/Dia.</div> <br>""",unsafe_allow_html=True)

            # Ordena os itens pela descrição do produto (A → Z)
            itens = sorted(itens, key=lambda x: x.get("produto", {}).get("descricao", "").lower())
            
            with st.form("form_lotes"):
                valores_digitados = {}
                excluir_itens = []

                for idx, item in enumerate(itens):
                    produto = item.get("produto", {})
                    descricao = produto.get("descricao", "")
                    codigo = produto.get("codigo", "")
                    quantidade = produto.get("quantidade", 0)
    
                    rastreabilidade = item.get("rastreabilidade",{})
                    lote = rastreabilidade.get("numeroLote","")
                    validade = rastreabilidade.get("dataValidadeLote","")
                    fabricacao = rastreabilidade.get("dataFabricacaoLote","")
                    
                    # Filtro por código
                    codigo_str = str(codigo).strip()
                    df_filtrado = df_lotes[df_lotes["Código do Produto"] == codigo_str]

                    # Teste de resultado
                    #st.write("🔍 Código do item:", codigo_str)
                    #st.write("📌 Resultado do filtro:", df_filtrado)
            

                    # Abre automaticamente se lote ou validade estiverem vazios
                    expandir = (lote == "" or validade == "")
                    
                    with st.expander(f"{descricao} ({codigo})", expanded=expandir):
                        col1, col2, col3, col4, col5, = st.columns([4, 3, 3, 2, 1])
                        with col1:
                            st.text("")
                            st.text("")
                            st.text(f"{descricao} ({codigo})")
                        with col2:
                            try:
                                filtro_lote = df_lotes.loc[df_lotes["Código do Produto"] == codigo, "LOTE"]
                                if not filtro_lote.empty:
                                    lote_apostrofo = filtro_lote.values[0]
                                else:
                                    lote_apostrofo = ""
                                lote_sel = lote_apostrofo[1:]
                                lote_input = st.text_input("Lote", value=lote_sel, key=f"lote_sel_{idx}")
                                valores_digitados[f"lote_{idx}"] = lote_sel
                            except (ValueError, AttributeError):
                                lote_input = st.text_input("Lote", key=f"lote_sel_{idx}")
                                valores_digitados[f"lote_{idx}"] = lote_sel

                        with col3:
                            try:
                                filtro_vazio = df_lotes.loc[df_lotes["Código do Produto"] == codigo, "VALIDADE"]    

                                if not filtro_vazio.empty:
                                    filtro_validade = df_lotes.loc[df_lotes["Código do Produto"] == codigo, "VALIDADE"].values[0]
                                    opcoes_validade = [filtro_validade,"INDEFINIDO"]

                                    escolha_validade = st.selectbox("Validade", options=opcoes_validade,key=f"validade_opcao_{idx}")

                                    if escolha_validade == "INDEFINIDO":
                                        valores_digitados[f"validade_{idx}"] = escolha_validade

                                    else:
                                        validade_sel = filtro_validade
                                        # Se for no formato MM/YY ou MM/YYYY
                                        mes, ano = validade_sel.split("/")
                                        mes = int(mes)
                                        ano = int(ano)
                                        if ano < 100:
                                            ano += 2000

                                        ultimo_dia = calendar.monthrange(ano, mes)[1]
                                        validade_convertida = date(ano, mes, ultimo_dia)
                                        validade_input = st.date_input("Validade", value=validade_convertida, key=f"validade_input_{idx}")

                                        valores_digitados[f"validade_{idx}"] = validade_input

                                else:
                                    valores_digitados[f"validade_{idx}"] = "INDEFINIDO"

                            except Exception as e:
                                st.warning(f"Erro ao tratar validade do produto {codigo}: {e}")

                            
                            #print(validade)
                            #print(valores_digitados[f"validade_{idx}"].strftime("%d/%m/%Y"))

                        with col4:
                            valores_digitados[f"qtd_{idx}"] = st.number_input("Qtd", value=quantidade, key=f"qtd_{idx}")
                        with col5:
                            st.text("Excluir")
                            excluir_itens.append(
                                st.checkbox("❌", key=f"excluir_{idx}")
                            )

                    st.markdown("<hr style='border: none; height: 1px; background-color: #5e5e5e;'>", unsafe_allow_html=True)
                
                frete = pedido.get("frete",{})
                qtt_caixas = frete.get("quantidade_volumes")
                quantidade_caixas = st.number_input("Quantidade de caixas", value=qtt_caixas, step=1)
    
                if st.form_submit_button("💾 Salvar Dados"):
                    novos_produtos = []
                    for idx, item in enumerate(itens):
                            produto = item.get("produto", {})
                            ide = item.get("ide", {})

                            ide_final = {
                                "codigo_item": ide.get("codigo_item"),
                                "simples_nacional": ide.get("simples_nacional"),
                            }

                            if excluir_itens[idx]:
                                ide_final["acao_item"] = "E"
        
                            validade = valores_digitados.get(f"validade_{idx}")

                            if validade == "INDEFINIDO":

                                novos_produtos.append({
                                "ide": ide_final,
                                "produto": produto,
                                "rastreabilidade": {
                                    "numeroLote": valores_digitados[f"lote_{idx}"],
                                    "qtdeProdutoLote": valores_digitados[f"qtd_{idx}"]
                                }
                            })

                            else:    
                                validade_str = validade.strftime("%d/%m/%Y")
                                fabricacao_str = date(validade.year - 3, validade.month,1).strftime("%d/%m/%Y")

                                novos_produtos.append({
                                    "ide": ide_final,
                                    "produto": produto,
                                    "rastreabilidade": {
                                        "numeroLote": valores_digitados[f"lote_{idx}"],
                                        "qtdeProdutoLote": valores_digitados[f"qtd_{idx}"],
                                        "dataFabricacaoLote": fabricacao_str,
                                        "dataValidadeLote": validade_str
                                    }
                                })
    
                    resultado = alterar_pedido(codigo_pedido, novos_produtos, quantidade_caixas)
                    if resultado.get("faultstring"):
                        st.error(f"Erro ao alterar pedido: {resultado['faultstring']}")
                    else:
                        st.success("Pedido alterado com sucesso!")
        else:
            st.error("Pedido não encontrado ou resposta inválida da API.")
