import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials
import streamlit as st

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
