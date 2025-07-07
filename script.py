import streamlit as st
import os

# === CONFIGURATION ===
MODE = st.sidebar.radio("🧠 Mode d'analyse :", ["Démo hors ligne", "API OpenAI (GPT)"])
st.set_page_config(page_title="ICPE / VRD Analyzer", layout="centered")

# === EN-TÊTE ===
st.title("🛠️ Outil d'analyse ICPE / VRD")
st.markdown("Décrivez une **modification de travaux VRD** pour en analyser les impacts réglementaires ICPE.")

# === ZONE DE SAISIE ===
user_input = st.text_area("✍️ Modification prévue :", height=200, placeholder="Exemple : Déplacement d’un bassin de rétention côté sud à cause de l’aire incendie...")

# === ANALYSE ===
if st.button("🔍 Analyser"):
    if not user_input:
        st.warning("Merci de renseigner une modification à analyser.")
    else:
        if MODE == "Démo hors ligne":
            st.info("🧪 Mode démo local (aucune connexion à GPT)")
            fake_response = f"""
**Analyse simulée :**

✅ La modification décrite concerne un ouvrage hydraulique en zone ICPE.

- Vérifie la conformité avec l'arrêté du 11 avril 2017.
- Évalue si une mise à jour du porter-à-connaissance est nécessaire.
- Impact possible sur la rubrique 1510 si volume > 50 000 m³.

📘 Référence suggérée : Guide technique ICPE, rubrique 2.1.5.0.
"""
            st.markdown(fake_response)

        elif MODE == "API OpenAI (GPT)":
            try:
                from dotenv import load_dotenv
                import openai
                load_dotenv()
                openai.api_key = os.getenv("OPENAI_API_KEY")
                client = openai.OpenAI()
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "Tu es un assistant expert en réglementation ICPE et VRD."},
                        {"role": "user", "content": user_input}
                    ]
                )
                st.success("✅ Réponse générée par GPT :")
                st.markdown(response.choices[0].message.content)
            except Exception as e:
                st.error(f"❌ Erreur lors de l'appel API : {e}")

# === PIED DE PAGE ===
st.markdown("---")
st.markdown("📄 Version 1.0 · Projet Quartus · © 2025")

