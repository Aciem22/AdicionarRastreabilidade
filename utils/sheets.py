import streamlit as st
import gspread
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
import pandas as pd
import pickle
import os

# === Função para autenticação OAuth Web ===
def get_creds():
    if "oauth_creds" in st.session_state:
        return st.session_state["oauth_creds"]

    # Cache do token no arquivo interno
    token_path = "token.pkl"
    if os.path.exists(token_path):
        with open(token_path, "rb") as f:
            creds = pickle.load(f)
            st.session_state["oauth_creds"] = creds
            return creds

    # Configura OAuth flow
    client_config = st.secrets["gcp_oauth"]
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": client_config["client_id"],
                "client_secret": client_config["client_secret"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["https://aciem22.streamlitapp.io/"]
            }
        },
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets.readonly",
            "https://www.googleapis.com/auth/drive.readonly"
        ]
    )

    auth_url, _ = flow.authorization_url(prompt='consent')
    st.write("🚀 Clique no link abaixo, autorize o acesso e cole a URL final:")
    st.write(auth_url)

    url_response = st.text_input("Cole aqui a URL após autorização", key="url_input")
    if not url_response:
        st.stop()

    flow.fetch_token(authorization_response=url_response)
    creds = flow.credentials
    st.session_state["oauth_creds"] = creds

    # Salva token no cache
    with open(token_path, "wb") as f:
        pickle.dump(creds, f)

    return creds

# === Função para carregar planilha ===
@st.cache_data
def carregar_lotes_validade():
    creds = get_creds()
    client = gspread.authorize(creds)
    planilha = client.open(st.secrets["gcp_oauth"]["spreadsheet_name"])
    aba = planilha.worksheet(st.secrets["gcp_oauth"]["worksheet_name"])
    dados = aba.get_all_records()
    df = pd.DataFrame(dados)

    df["Código do Produto"] = df["Código do Produto"].astype(str)
    df["LOTE"] = df["LOTE"].astype(str).apply(lambda x: f"'{x}")
    df["VALIDADE"] = df["VALIDADE"].astype(str)
    return df

# === Streamlit UI ===
st.title("Lotes e Validades")
df_lotes = carregar_lotes_validade()
st.dataframe(df_lotes)
