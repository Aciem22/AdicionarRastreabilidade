import gspread
from google_auth_oauthlib.flow import Flow
import pandas as pd
import streamlit as st

@st.cache_data
def carregar_lotes_validade():
    scope = [
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly"
    ]

    client_config = st.secrets["gcp_oauth"]
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": client_config["client_id"],
                "client_secret": client_config["client_secret"],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"]
            }
        },
        scopes=scope
    )

    if "oauth_creds" in st.session_state:
        creds = st.session_state["oauth_creds"]
    else:
        auth_url, _ = flow.authorization_url(prompt='consent')
        st.write("🚀 Abra este link em outro navegador e copie o código de autorização:")
        st.write(auth_url)
        
        code = st.text_input("Cole aqui o código de autorização", key="oauth_code")
        if not code:
            st.stop()
        
        flow.fetch_token(code=code)
        creds = flow.credentials
        st.session_state["oauth_creds"] = creds

    client = gspread.authorize(creds)
    planilha = client.open("Controle Lote e Val Rastreabilidade")
    aba = planilha.worksheet("Lotes")
    dados = aba.get_all_records()
    df = pd.DataFrame(dados)

    df["Código do Produto"] = df["Código do Produto"].astype(str)
    df["LOTE"] = df["LOTE"].astype(str).apply(lambda x: f"'{x}")
    df["VALIDADE"] = df["VALIDADE"].astype(str)

    return df

st.title("Lotes e Validades")
df_lotes = carregar_lotes_validade()
st.dataframe(df_lotes)
