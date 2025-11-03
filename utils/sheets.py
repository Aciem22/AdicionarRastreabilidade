import streamlit as st
import gspread
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
import pandas as pd
import pickle
import os
from urllib.parse import urlparse, parse_qs

# ===============================
# FUNÇÃO DE AUTENTICAÇÃO OAUTH
# ===============================
def get_creds():
    if "oauth_creds" in st.session_state:
        return st.session_state["oauth_creds"]

    token_path = "token.pkl"
    if os.path.exists(token_path):
        with open(token_path, "rb") as f:
            creds = pickle.load(f)
            st.session_state["oauth_creds"] = creds
            return creds

    client_config = st.secrets["gcp_oauth"]
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": client_config["client_id"],
                "client_secret": client_config["client_secret"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [f"https://rastreabilidadelenvie.streamlitapp.io/"]
            }
        },
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets.readonly",
            "https://www.googleapis.com/auth/drive.readonly"
        ]
    )

    # Se ainda não tiver código na URL, mostra link de autorização
    query_params = st.experimental_get_query_params()
    if "code" not in query_params:
        auth_url, _ = flow.authorization_url(prompt='consent')
        st.write("🚀 Clique no link abaixo e autorize o acesso:")
        st.write(auth_url)
        st.stop()

    code = query_params["code"][0]
    flow.fetch_token(code=code)
    creds = flow.credentials
    st.session_state["oauth_creds"] = creds

    # Salva token local
    with open(token_path, "wb") as f:
        pickle.dump(creds, f)

    return creds

# ===============================
# FUNÇÃO PARA CARREGAR PLANILHA
# ===============================
@st.cache_data
def carregar_lotes_validade(creds):
    client = gspread.authorize(creds)
    planilha = client.open(st.secrets["gcp_oauth"]["spreadsheet_name"])
    aba = planilha.worksheet(st.secrets["gcp_oauth"]["worksheet_name"])
    dados = aba.get_all_records()
    df = pd.DataFrame(dados)

    df["Código do Produto"] = df["Código do Produto"].astype(str)
    df["LOTE"] = df["LOTE"].astype(str).apply(lambda x: f"'{x}")
    df["VALIDADE"] = df["VALIDADE"].astype(str)
    return df

# ===============================
# STREAMLIT UI
# ===============================
st.title("Lotes e Validades")
creds = get_creds()
df_lotes = carregar_lotes_validade(creds)
st.dataframe(df_lotes)
