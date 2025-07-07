import streamlit as st
import openai
from dotenv import load_dotenv
import os

# Chargement de la clé API
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Configuration Streamlit
st.set_page_config(page_title="Analyse ICPE / VRD")
st.title("🛠️ Analyse ICPE / VRD")
st.markdown("Décris ci-dessous ta modification de travaux VRD pour analyser son impact ICPE :")

prompt = st.text_area("✍️ Modification / intervention prévue :", height=200)

if st.button("Analyser avec GPT"):
    if prompt:
        with st.spinner("Analyse en cours..."):
            try:
                client = openai.OpenAI()
                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "Tu es un assistant expert en ICPE et VRD. Réponds de manière claire et réglementaire."},
                        {"role": "user", "content": prompt}
                    ]
                )
                st.success("✅ Résultat :")
                st.markdown(response.choices[0].message.content)
            except Exception as e:
                st.error(f"❌ Une erreur est survenue : {e}")
    else:
        st.warning("⚠️ Merci d’entrer une modification pour lancer l’analyse.")
