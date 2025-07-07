import streamlit as st
import os
st.markdown(
    """
    <style>
    /* Fond global */
    .stApp {
        background: linear-gradient(to right, #f7f8fc, #e0e6f7);
    }

    /* Boîte texte */
    textarea {
        background-color: #ffffffcc !important;
        border-radius: 10px !important;
        padding: 10px !important;
    }

    /* Bouton d'analyse */
    .stButton > button {
        background-color: #3d5afe;
        color: white;
        font-weight: bold;
        border-radius: 8px;
        padding: 0.5em 1.5em;
        transition: 0.3s ease;
    }

    .stButton > button:hover {
        background-color: #304ffe;
        transform: scale(1.03);
    }

    /* Footer centré et discret */
    footer {
        visibility: hidden;
    }

    .reportview-container .main footer {
        visibility: hidden;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# === CONFIGURATION ===
st.set_page_config(page_title="ICPE / VRD Analyzer", layout="centered", page_icon="🛠️")
MODE = st.sidebar.radio("🧠 Mode d'analyse :", ["Démo hors ligne", "API OpenAI (GPT)"])

# === LOGO & TITRE ===
col1, col2 = st.columns([1, 5])
with col1:
    st.image("https://www.mucem.org/sites/default/files/2022-08/logo-Morgane.gif", width=80)
with col2:
    st.markdown("## 🛠️ Outil d’analyse ICPE / VRD")
    st.markdown("Analyse réglementaire des modifications de travaux en zone ICPE.")

st.markdown("---")

# === FORMULAIRE DE SAISIE ===
st.subheader("✍️ Décrivez la modification de travaux VRD :")
user_input = st.text_area(
    label="Exemple : Déplacement d’un bassin de rétention vers l’ouest à cause de contraintes incendie...",
    height=200
)

# === BOUTON ET ANALYSE ===
if st.button("🔍 Analyser la situation"):
    if not user_input:
        st.warning("⚠️ Merci de décrire une intervention avant de lancer l’analyse.")
    else:
        if MODE == "Démo hors ligne":
            st.info("🧪 Mode démonstration local")
            st.markdown(f"""
### ✅ Analyse simulée :

- La modification décrite concerne potentiellement un ouvrage hydraulique situé en zone ICPE.
- Vérifie la conformité avec **l'arrêté du 11 avril 2017** (bassins, rejets, etc.).
- Si volume > **50 000 m³**, cela peut activer la **rubrique 1510**.
- Pense à **mettre à jour le Porter-à-Connaissance ICPE** si le changement est significatif.

📘 Référence utile : Guide technique ICPE - Rubrique 2.1.5.0
            """)
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
                        {"role": "system", "content": "Tu es un expert réglementaire ICPE et VRD. Sois précis et clair."},
                        {"role": "user", "content": user_input}
                    ]
                )
                st.success("✅ Réponse générée par GPT :")
                st.markdown(response.choices[0].message.content)
            except Exception as e:
                st.error(f"❌ Erreur lors de l'appel API : {e}")

# === PIED DE PAGE ===
st.markdown("---")
st.caption("🔖 Quartus · Projet ICPE / VRD · Version 1.0 · © 2025")
