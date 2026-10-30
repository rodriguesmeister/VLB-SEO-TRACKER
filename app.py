import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import google.generativeai as genai
from urllib.parse import urljoin, urlparse
import time

st.title("Auditoria de SEO da Concorrência 🔍")
st.write("Analisa títulos, H1, Meta Tags e deduz palavras-chave com IA.")

api_key = st.text_input("Chave API do Google AI Studio", type="password")
url_concorrente = st.text_input("URL do Concorrente (com https://)", "https://www.amobgroup.com/pt/")
idioma = st.text_input("Filtro de Idioma (ex: /pt/ ou deixar em branco)", "")
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
        
        # Remove www. para não perder links internos devido a redirecionamentos
        dominio_base = urlparse(url_concorrente).netloc.replace('www.', '')
        
        progresso_ui = st.progress(0.0)
        status_texto = st.empty()
        
        # Disfarce de Browser para contornar firewalls de segurança
        cabecalhos = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        
        while paginas_a_visitar and len(paginas_visitadas) < limite:
            url_atual = paginas_a_visitar.pop(0)
            
            if url_atual in paginas_visitadas: continue
            if idioma and idioma not in url_atual: continue
            if any(termo in url_atual.lower() for termo in termos_excluidos): continue
                
            try:
                status_texto.text(f"A ler página: {url_atual}")
                resposta = requests.get(url_atual, headers=cabecalhos, timeout=15)
                resposta.raise_for_status()
                
                sopa = BeautifulSoup(resposta.text, 'html.parser')
                paginas_visitadas.add(url_atual)
                
                title = sopa.title.text.strip() if sopa.title and sopa.title.text else 'N/A'
                h1 = sopa.find('h1').text.strip() if sopa.find('h1') else 'N/A'
                meta_desc_tag = sopa.find('meta', attrs={'name': 'description'})
                meta_desc = meta_desc_tag['content'].strip() if meta_desc_tag else 'N/A'
                
                time.sleep(5)
                prompt = f"Título: {title}\nH1: {h1}\nMeta: {meta_desc}\nLista 3 a 5 palavras-chave principais, separadas por vírgula."
                keywords = modelo.generate_content(prompt).text.strip()
                
                dados_seo.append([url_atual, title, h1, meta_desc, keywords])
                progresso_ui.progress(len(paginas_visitadas) / limite)
                
                for link in sopa.find_all('a', href=True):
                    url_completo = urljoin(url_atual, link['href'])
                    dominio_link = urlparse(url_completo).netloc.replace('www.', '')
                    if dominio_link == dominio_base and url_completo not in paginas_visitadas:
                        paginas_a_visitar.append(url_completo)
                        
            except Exception as e:
                # Mostra o erro exato na interface
                st.warning(f"Erro na página {url_atual}: {str(e)}")
        
        if dados_seo:
            status_texto.success("Auditoria Concluída!")
            df = pd.DataFrame(dados_seo, columns=["URL", "Title", "H1", "Meta Description", "Keywords (AI)"])
            st.dataframe(df)
            
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(label="Descarregar Relatório (CSV)", data=csv, file_name=f"auditoria_{dominio_base}.csv", mime="text/csv")
        else:
            status_texto.error("A tabela está vazia. Verifica os avisos de erro listados acima.")
