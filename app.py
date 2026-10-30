import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import google.generativeai as genai
from urllib.parse import urljoin, urlparse
import time

st.title("Auditoria de SEO da Concorrência 🔍")
st.write("Analisa títulos, H1, Meta Tags e deduz palavras-chave com Inteligência Artificial.")

# Interface Visual
api_key = st.text_input("Chave API do Google AI Studio", type="password")
url_concorrente = st.text_input("URL do Concorrente (com https://)", "https://vlb-group.com/")
idioma = st.text_input("Filtro de Idioma (ex: /pt/ ou deixar em branco)", "/pt/")
ignorar = st.text_input("Ignorar links com:", "politica, privacidade, termos, cookies, login")
limite = st.number_input("Limite máximo de páginas a ler", min_value=1, max_value=500, value=15)

if st.button("Iniciar Auditoria", type="primary"):
    if not api_key:
        st.error("Insere a tua API Key para continuar.")
    else:
        genai.configure(api_key=api_key)
        modelo = genai.GenerativeModel('gemini-1.5-flash')
        termos_excluidos = [t.strip().lower() for t in ignorar.split(',') if t.strip()]
        
        paginas_visitadas = set()
        paginas_a_visitar = [url_concorrente]
        dados_seo = []
        dominio_base = urlparse(url_concorrente).netloc
        
        progresso_ui = st.progress(0.0)
        status_texto = st.empty()
        
        while paginas_a_visitar and len(paginas_visitadas) < limite:
            url_atual = paginas_a_visitar.pop(0)
            
            if url_atual in paginas_visitadas: continue
            if idioma and idioma not in url_atual: continue
            if any(termo in url_atual.lower() for termo in termos_excluidos): continue
                
            try:
                status_texto.text(f"A ler página: {url_atual}")
                resposta = requests.get(url_atual, timeout=10)
                sopa = BeautifulSoup(resposta.text, 'html.parser')
                paginas_visitadas.add(url_atual)
                
                title = sopa.title.string.strip() if sopa.title else 'N/A'
                h1 = sopa.find('h1').text.strip() if sopa.find('h1') else 'N/A'
                meta_desc_tag = sopa.find('meta', attrs={'name': 'description'})
                meta_desc = meta_desc_tag['content'].strip() if meta_desc_tag else 'N/A'
                
                time.sleep(5) # Previne bloqueios da API
                prompt = f"Título: {title}\nH1: {h1}\nMeta: {meta_desc}\nLista 3 a 5 palavras-chave principais, separadas por vírgula."
                keywords = modelo.generate_content(prompt).text.strip()
                
                dados_seo.append([url_atual, title, h1, meta_desc, keywords])
                progresso_ui.progress(len(paginas_visitadas) / limite)
                
                for link in sopa.find_all('a', href=True):
                    url_completo = urljoin(url_atual, link['href'])
                    if urlparse(url_completo).netloc == dominio_base and url_completo not in paginas_visitadas:
                        paginas_a_visitar.append(url_completo)
                        
            except Exception:
                pass
        
        status_texto.success("Auditoria Concluída!")
        df = pd.DataFrame(dados_seo, columns=["URL", "Title", "H1", "Meta Description", "Keywords (AI)"])
        st.dataframe(df) # Mostra uma tabela de pré-visualização no site
        
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Descarregar Relatório (CSV)",
            data=csv,
            file_name=f"auditoria_{dominio_base}.csv",
            mime="text/csv"
        )
