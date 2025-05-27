import requests
import streamlit as st
from datetime import date, datetime

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

st.set_page_config(page_title="Cadastro de Lotes", layout="wide")
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
                   🚨 Os campos <b>Validade</b> e <b>Fabricação</b> estão no padrão ISO - Ano/Mês/Dia.</div> <br>""",unsafe_allow_html=True)
    
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

                    # VALIDADE
                    if validade == "":
                        val = date(2029, 1, 30)
                    elif isinstance(validade, str):
                        try:
                            # tenta primeiro como dd/mm/yyyy
                            val = datetime.strptime(validade, "%d/%m/%Y").date()
                        except ValueError:
                            # se der erro, tenta yyyy-mm-dd
                            val = datetime.strptime(validade, "%Y-%m-%d").date()
                    else:
                        val = validade      
                    
                    if (fabricacao == ""):
                        fab = date(2022,1,1)

                    else:
                        fab = datetime.strptime(fabricacao,"%d/%m/%Y").date() if isinstance(fabricacao,str) else fabricacao
    
                    col1, col2, col3, col4, col5, col6 = st.columns([4, 2, 2, 2, 2, 1])
                    with col1:
                        st.text("")                        
                        st.text("")
                        st.text(f"{descricao} ({codigo})")
                    with col2:
                        valores_digitados[f"lote_{idx}"] = st.text_input("Lote",value=lote, key=f"lote_{idx}")
                    with col3:
                        valores_digitados[f"fabricacao_{idx}"] = st.date_input("Fabricação", value=fab, key=f"fabricacao_{idx}")
                    with col4:
                        valores_digitados[f"validade_{idx}"] = st.date_input("Validade", value=val, key=f"validade_{idx}")
                    with col5:
                        valores_digitados[f"qtd_{idx}"] = st.number_input("Qtd", value=quantidade, key=f"qtd_{idx}")
                    with col6:
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
        
                            fabricacao_str = valores_digitados[f"fabricacao_{idx}"].strftime("%d/%m/%Y")
                            validade_str = valores_digitados[f"validade_{idx}"].strftime("%d/%m/%Y")

                            ide_final = {
                                "codigo_item": ide.get("codigo_item"),
                                "simples_nacional": ide.get("simples_nacional"),
                            }

                            if excluir_itens[idx]:
                                ide_final["acao_item"] = "E"

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
