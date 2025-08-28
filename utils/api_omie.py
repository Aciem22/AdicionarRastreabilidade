import streamlit as st
import requests
import json
import calendar
from datetime import date, datetime
import time
import re

APP_KEY = st.secrets["APP_KEY"]
APP_SECRET = st.secrets["APP_SECRET"]

def consultar_pedido(numero_pedido, tentativas=5):
    url = "https://app.omie.com.br/api/v1/produtos/pedido/"
    payload = {
        "call": "ConsultarPedido",
        "app_key": APP_KEY,
        "app_secret": APP_SECRET,
        "param": [
            {"numero_pedido": numero_pedido}
        ]
    }
    for tentativa in range(1, tentativas + 1):
        print(f"🔹 Tentativa {tentativa} de {tentativas} para consultar pedido {numero_pedido}")
        response = requests.post(url, json=payload)
        resultado = response.json()

        fault = resultado.get("faultstring", "")
        if fault.startswith("ERROR: Consumo redundante"):
            match = re.search(r"(\d+) segundos", fault)
            segundos = int(match.group(1)) if match else 6
            print(f"⚠️ Consumo redundante detectado. Aguardando {segundos}s antes da próxima tentativa...")
            time.sleep(segundos)
        else:
            return resultado

    print("❌ Todas as tentativas foram usadas, retornando último resultado")
    return resultado

def alterar_pedido(codigo_pedido, novos_produtos, quantidade_caixas, tentativas=3):
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

    for tentativa in range(1, tentativas + 1):
        print(f"🔹 Tentativa {tentativa} de {tentativas} para alterar pedido {codigo_pedido}")
        response = requests.post(url, json=payload)
        resultado = response.json()

        fault = resultado.get("faultstring", "")
        if fault.startswith("ERROR: Consumo redundante"):
            match = re.search(r"(\d+) segundos", fault)
            segundos = int(match.group(1)) if match else 6
            print(f"⚠️ Consumo redundante detectado. Aguardando {segundos}s antes da próxima tentativa...")
            time.sleep(segundos)
        else:
            print("===== RETORNO DA API =====")
            print(json.dumps(resultado, indent=2, ensure_ascii=False))
            print("===========================")
            return resultado

    print("❌ Todas as tentativas foram usadas, retornando último resultado")
    return resultado

