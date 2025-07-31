import requests
import streamlit as st

APP_KEY = st.secrets["APP_KEY"]
APP_SECRET = st.secrets["APP_SECRET"]

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

def alterar_pedido(codigo_pedido, novos_produtos, quantidade_caixas):
    url = "https://app.omie.com.br/api/v1/produtos/pedido/"
    payload = {
        "call": "AlterarPedidoVenda",
        "app_key": APP_KEY,
        "app_secret": APP_SECRET,
        "param": {
            "cabecalho": {
                "codigo_pedido": codigo_pedido
            },
            "frete": {
                "quantidade_volumes": quantidade_caixas,
                "especie_volumes": "CAIXAS"
            },
            "det": novos_produtos
        }
    }
    response = requests.post(url, json=payload)
    return response.json()
