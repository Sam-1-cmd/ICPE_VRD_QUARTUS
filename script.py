import streamlit as st
import openai
from dotenv import load_dotenv
import os

# Chargement des variables d'environnement
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Interface Streamlit
st.set_page_config(page_title="Analyse ICPE / VRD", layout="centered")
st.title("🛠️ Outil d'analyse ICPE / VRD")
st.markdown("Décris ci-dessous ta modification de travaux VRD pour analyser son impact ICPE :")

# Zone de texte pour entrer le contexte
prompt = st.text_area("✍️ Modification / intervention prévue :", height=200)

# Bouton d'envoi
if st.button("Analyser avec GPT"):
    if prompt:
        with st.spinner("Analyse en cours..."):
            try:
                # Appel OpenAI
                response = openai.ChatCompletion.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "Tu es un assistant spécialisé en réglementation ICPE et VRD."},
                        {"role": "user", "content": prompt}
                    ]
                )
                st.success("✅ Résultat de l'analyse :")
                st.markdown(response["choices"][0]["message"]["content"])
            except Exception as e:
                st.error(f"❌ Une erreur est survenue : {e}")
    else:
        st.warning("⚠️ Merci de décrire une intervention avant d'analyser.")



