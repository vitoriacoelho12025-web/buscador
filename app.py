import streamlit as st
import requests
import json
from requests.auth import HTTPBasicAuth
from datetime import datetime

# Configuração da página
st.set_page_config(
    page_title="Buscador de Processos - DataJud",
    page_icon="⚖️",
    layout="wide"
)

# Mapeamento de Regiões para Tribunais
REGION_MAP = {
    "df": "tjdft",
    "sp": "tjsp",
    "rj": "tjrj",
    "mg": "tjmg",
    "rs": "tjrs",
    "pr": "tjpr",
    "sc": "tjsc",
    "ba": "tjba",
    "pe": "tjpe",
    "ce": "tjce",
    "go": "tjgo",
    "mt": "tjmt",
    "ms": "tjms",
    "es": "tjes",
    "am": "tjam",
    "pa": "tjpa",
    "ma": "tjma",
    "pi": "tjpi",
    "rn": "tjrn",
    "pb": "tjpb",
    "al": "tjal",
    "se": "tjse",
    "to": "tjto",
    "ac": "tjac",
    "ro": "tjro",
    "rr": "tjrr",
    "ap": "tjap"
}

def format_date(date_str):
    if not date_str:
        return "N/A"
    try:
        # Formato comum da API: 2023-05-09T14:30:00.000Z
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return dt.strftime("%d/%m/%Y %H:%M")
    except:
        return date_str

def search_datajud(tribunal, query_text, credentials):
    url = f"https://api-publica.datajud.cnj.jus.br/api_publica_{tribunal}/_search"
    
    try:
        user, password = credentials.split(':')
    except ValueError:
        return {"error": "Formato de credenciais inválido. Use 'usuario:senha'."}

    # Query Elasticsearch
    payload = {
        "size": 50,
        "query": {
            "bool": {
                "should": [
                    {"match": {"assuntos.nome": query_text}},
                    {"match": {"classeProcessual.nome": query_text}}
                ],
                "minimum_should_match": 1
            }
        }
    }

    try:
        response = requests.post(
            url,
            json=payload,
            auth=HTTPBasicAuth(user, password),
            timeout=30
        )
        
        if response.status_code == 401:
            return {"error": "Credenciais inválidas (401). Verifique seu usuário e senha."}
        elif response.status_code == 404:
            return {"error": f"Tribunal '{tribunal}' não encontrado ou API indisponível."}
        
        response.raise_for_status()
        return response.json()
    
    except requests.exceptions.Timeout:
        return {"error": "A requisição expirou (Timeout). Tente novamente mais tarde."}
    except requests.exceptions.RequestException as e:
        return {"error": f"Erro na conexão: {str(e)}"}

# Interface Streamlit
st.title("⚖️ Buscador de Processos - DataJud")
st.markdown("---")

# Sidebar com informações e LGPD
with st.sidebar:
    st.header("Sobre")
    st.info("Esta aplicação consulta a API Pública do DataJud do CNJ. As credenciais são usadas apenas como proxy e não são armazenadas.")
    st.warning("⚠️ **Aviso LGPD:** Os dados acessados são públicos. Utilize estas informações com responsabilidade e ética profissional.")
    st.markdown("[Obter credenciais DataJud](https://www.cnj.jus.br/sistemas/datajud/api-publica/)")

# Formulário de Busca
with st.form("search_form"):
    col1, col2 = st.columns(2)
    
    with col1:
        region_input = st.text_input("Região (ex: df, sp, rj)", placeholder="Opcional - preenche o tribunal automaticamente").lower().strip()
        
        default_tribunal = "tjdft"
        if region_input in REGION_MAP:
            default_tribunal = REGION_MAP[region_input]
            
        tribunal = st.text_input("Tribunal", value=default_tribunal, help="Ex: tjdft, tjsp, tjrj")
        
    with col2:
        causa = st.text_input("Causa / Assunto", placeholder="Ex: PASEP, Apelação Cível", help="Busca em assuntos e classe processual")
        creds = st.text_input("Credenciais DataJud (user:senha)", type="password", help="Formato: seu_usuario:sua_senha")

    submit = st.form_submit_button("🔍 Buscar Processos!")

if submit:
    if not causa or not creds:
        st.error("Por favor, preencha a Causa/Assunto e as Credenciais.")
    else:
        with st.spinner(f"Consultando API do {tribunal.upper()}..."):
            results = search_datajud(tribunal.lower(), causa, creds)
            
            if "error" in results:
                st.error(results["error"])
            else:
                hits = results.get("hits", {}).get("hits", [])
                total = results.get("hits", {}).get("total", {}).get("value", 0)
                
                if total == 0:
                    st.warning("Nenhum processo encontrado para os critérios informados.")
                else:
                    st.success(f"Encontrados {total} processos (exibindo até 50).")
                    
                    summary_data = []
                    
                    for hit in hits:
                        p = hit.get("_source", {})
                        num = p.get("numeroProcesso", "N/A")
                        classe = p.get("classeProcessual", {}).get("nome", "N/A")
                        assuntos = ", ".join([a.get("nome", "") for a in p.get("assuntos", [])])
                        valor = p.get("valorCausa", 0.0)
                        
                        summary_data.append({
                            "Número": num,
                            "Classe": classe,
                            "Assunto": assuntos,
                            "Valor": f"R$ {valor:,.2f}"
                        })
                        
                        with st.expander(f"📄 Processo: {num}"):
                            st.markdown(f"""
                            📌 **Processo:** {num}
                            🏛 **Instância:** {p.get('grau', 'N/A')}
                            ⚖ **Órgão Julgador:** {p.get('orgaoJulgador', {}).get('nome', 'N/A')}
                            📂 **Classe:** {classe}
                            📝 **Assunto:** {assuntos}
                            💰 **Valor da Causa:** R$ {valor:,.2f}
                            📅 **Data Início:** {format_date(p.get('dataAjuizamento'))}
                            📅 **Último Movimento:** {format_date(p.get('movimentos', [{}])[-1].get('dataHora')) if p.get('movimentos') else 'N/A'}
                            """)
                            
                            # Polos
                            col_a, col_b = st.columns(2)
                            
                            with col_a:
                                st.markdown("### 🗒 Polo Ativo")
                                for parte in p.get("poloAtivo", []):
                                    st.markdown(f"- **{parte.get('nome', 'N/A')}**")
                                    if parte.get('cpfCnpj'): st.text(f"CPF/CNPJ: {parte.get('cpfCnpj')}")
                                    
                                    # Advogados Polo Ativo
                                    advs = parte.get("advogados", [])
                                    if advs:
                                        st.markdown("*Advogados:*")
                                        for adv in advs:
                                            st.text(f"  • {adv.get('nome')} (OAB: {adv.get('oab', 'N/A')})")

                            with col_b:
                                st.markdown("### 🗒 Polo Passivo")
                                for parte in p.get("poloPassivo", []):
                                    st.markdown(f"- **{parte.get('nome', 'N/A')}**")
                                    if parte.get('cpfCnpj'): st.text(f"CPF/CNPJ: {parte.get('cpfCnpj')}")
                                    
                                    # Advogados Polo Passivo
                                    advs = parte.get("advogados", [])
                                    if advs:
                                        st.markdown("*Advogados:*")
                                        for adv in advs:
                                            st.text(f"  • {adv.get('nome')} (OAB: {adv.get('oab', 'N/A')})")

                    # Tabela Resumo
                    st.markdown("### 📊 Tabela Resumo")
                    st.dataframe(summary_data, use_container_width=True)
