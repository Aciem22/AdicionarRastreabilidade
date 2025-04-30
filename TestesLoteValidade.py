import requests
import streamlit as st
from datetime import datetime
import easyocr
import re
from PIL import Image, ImageEnhance, ImageFilter
import io
import calendar
import numpy as np

# ─── Configurações da API ─────────────────────────────────────────────────────
APP_KEY = "1724630275368"
APP_SECRET = "549a26b527f429912abf81f18570030e"

def consultar_pedido(numero_pedido):
    url = "https://app.omie.com.br/api/v1/produtos/pedido/"
    payload = {
        "call": "ConsultarPedido",
        "app_key": APP_KEY,
        "app_secret": APP_SECRET,
        "param": [{"numero_pedido": numero_pedido}]
    }
    return requests.post(url, json=payload).json()

def alterar_pedido(codigo_pedido, novos_produtos):
    url = "https://app.omie.com.br/api/v1/produtos/pedido/"
    payload = {
        "call": "AlterarPedidoVenda",
        "app_key": APP_KEY,
        "app_secret": APP_SECRET,
        "param": {
            "cabecalho": {"codigo_pedido": codigo_pedido},
            "det": novos_produtos
        }
    }
    return requests.post(url, json=payload).json()

# ─── Funções de OCR ────────────────────────────────────────────────────────────
reader = easyocr.Reader(['pt'], gpu=False)

def preprocessar_imagem(img_pil):
    img = img_pil.convert("L")
    img = img.filter(ImageFilter.MedianFilter())
    enhancer = ImageEnhance.Contrast(img)
    return enhancer.enhance(2)

def corrigir_texto_ocr(texto):
    texto = texto.upper()
    return (texto.replace("AG0","AGO")
                 .replace("0CT","OCT")
                 .replace("DE2","DEZ")
                 .replace("FEVEREIR0","FEVEREIRO")
                 .replace("UAL","VAL"))

def converter_validade(mes_ano_str):
    meses = {'JAN':'01','FEV':'02','MAR':'03','ABR':'04','MAI':'05','JUN':'06',
             'JUL':'07','AGO':'08','SET':'09','OUT':'10','NOV':'11','DEZ':'12'}
    m = re.match(r"([A-Z]{2,3})/(\d{2,4})", mes_ano_str)
    if m:
        ma, a = m.groups()
        mm = meses.get(ma[:3], '01')
        if len(a)==2: a = "20"+a
        d = calendar.monthrange(int(a), int(mm))[1]
        return f"{d:02d}/{mm}/{a}"
    return mes_ano_str

# ─── App ──────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Cadastro de Lotes Automático", layout="wide")
st.title("🔍 Consulta e Cadastro de Lotes nos Pedidos")

numero_pedido = st.text_input("Digite o número do pedido:")
if not numero_pedido:
    st.stop()

# Consulta
with st.spinner("Consultando pedido..."):
    resp = consultar_pedido(numero_pedido)
pedido = resp.get("pedido_venda_produto", {})
if pedido.get("cabecalho",{}).get("etapa") == "60":
    st.warning("Pedido já faturado → não pode alterar.")
    st.stop()

itens = pedido.get("det", [])
codigo_pedido = pedido.get("cabecalho",{}).get("codigo_pedido","")

# Prepara espaço em session_state
if 'ocr_data' not in st.session_state or st.session_state.get('last_pedido')!=numero_pedido:
    st.session_state['last_pedido'] = numero_pedido
    st.session_state['ocr_data'] = {}

st.markdown(f"### Pedido Nº {numero_pedido} — {len(itens)} item(ns)")

# ─── 1) Captura & OCR (fora do form) ─────────────────────────────────────────
st.write("#### 📷 Tire foto de cada etiqueta (OCR automático)")
for idx, item in enumerate(itens):
    desc = item['produto']['descricao']

    if st.button(f"📸 Capturar Foto para {desc}", key=f"btn_cam_{idx}"):
        st.session_state[f"show_cam_{idx}"] = not st.session_state.get(f"show_cam_{idx}", False)

    if st.session_state.get(f"show_cam_{idx}", False):
        img = st.camera_input(f"{idx+1}. {desc}", key=f"cam_{idx}")
        if img:
            with st.spinner("Processando OCR..."):
                img_pil = Image.open(io.BytesIO(img.getvalue()))
                img_prep = preprocessar_imagem(img_pil)
                txt = " ".join(reader.readtext(np.array(img_prep), detail=0))
                txtc = corrigir_texto_ocr(txt)

                # extrai lote e validade
                lm = re.search(r"(?:[Ll1]ote|[Ll1])[.:\s]*([A-Za-z0-9\-\/]+)", txtc)
                vm = re.search( r"(?:VAL(?:IDADE)?|V)[.:\s]*"        # prefixo "VAL","VALIDADE" ou "V"
                                r"([A-Z]{2,3}|0[1-9]|1[0-2])"               # grupo 1: "JAN" ou "04"
                                r"[\/\-]?"                          # opcional "/" ou "-"
                                r"(\d{2,4})", txtc, flags=re.IGNORECASE)
                lote = lm.group(1) if lm else ""

                if vm:
                    mes, ano = vm.group(1), vm.group(2)
                    mes_ano_raw = f"{mes}/{ano}"
                    val = converter_validade(mes_ano_raw)  
    
                else:
                    val = ""  # ou o que fizer sentido no seu fluxo
                # salva no session_state
                st.session_state['ocr_data'][idx] = {'lote':lote, 'validade':val}

                st.text_area("Texto OCR", txtc, height=100)
                st.success(f"Extraído → Lote: {lote} | Validade: {val}")

st.write("---")

# ─── 2) Formulário de ajustes + Envio ─────────────────────────────────────────
with st.form("form_lotes"):
    valores = {}
    for idx, item in enumerate(itens):
        desc = item['produto']['descricao']
        qt = item['produto']['quantidade']
        rast = item.get('rastreabilidade',{})
        # defaults: OCR ou o que já vinha do pedido
        default_l = st.session_state['ocr_data'].get(idx,{}).get('lote', rast.get('numeroLote',''))
        default_v = st.session_state['ocr_data'].get(idx,{}).get('validade', rast.get('dataValidadeLote',''))
        default_f = rast.get('dataFabricacaoLote','')

        st.markdown(f"**{idx+1}. {desc}**")
        cols = st.columns([3,2,2,1])
        valores[f"lote_{idx}"] = cols[0].text_input("Lote", value=default_l, key=f"lote_{idx}")
        valores[f"validade_{idx}"] = cols[1].text_input("Validade", value=default_v, key=f"validade_{idx}")
        valores[f"fabricacao_{idx}"] = cols[2].text_input("Fabricação", value=default_f, key=f"fabricacao_{idx}")
        valores[f"qtd_{idx}"] = cols[3].number_input("Qtd", value=qt, key=f"qtd_{idx}")

    if st.form_submit_button("💾 Salvar Dados"):
        novos = []
        for idx, item in enumerate(itens):
            ide = item['ide']
            prod = item['produto']
            novos.append({
                "ide": {"codigo_item": ide['codigo_item'], "simples_nacional": ide['simples_nacional']},
                "produto": prod,
                "rastreabilidade": {
                    "numeroLote": valores[f"lote_{idx}"],
                    "qtdeProdutoLote": valores[f"qtd_{idx}"],
                    "dataFabricacaoLote": valores[f"fabricacao_{idx}"],
                    "dataValidadeLote": valores[f"validade_{idx}"]
                }
            })
        res = alterar_pedido(codigo_pedido, novos)
        if res.get("faultstring"):
            st.error("Erro: "+res["faultstring"])
        else:
            st.success("Pedido alterado com sucesso!")


