import streamlit as st
import os

# Choisir le mode ici
MODE = "offline"  # "api" pour GPT réel, "offline" pour test

st.title("🛠️ Analyse ICPE / VRD")

user_input = st.text_area("Décris ta modification VRD :", height=200)

if st.button("Analyser"):
    if not user_input:
        st.warning("Merci de remplir le champ.")
    else:
        if MODE == "offline":
            # Simulation de réponse sans GPT
            response = f"""
**Analyse simulée :**

Ta modification pourrait impacter les réseaux hydrauliques de la zone ICPE.  
Vérifie la conformité avec l'arrêté du 11 avril 2017 (bassins de rétention),  
et assure-toi que les eaux de ruissellement sont bien séparées des eaux incendie.
"""
            st.success("🧪 Mode test (local)")
            st.markdown(response)

        elif MODE == "api":
            from dotenv import load_dotenv
            import openai

            load_dotenv()
            openai.api_key = os.getenv("OPENAI_API_KEY")

            try:
                client = openai.OpenAI()
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "Tu es un assistant réglementaire ICPE/VRD."},
                        {"role": "user", "content": user_input}
                    ]
                )
                st.success("Réponse OpenAI (API)")
                st.markdown(response.choices[0].message.content)
            except Exception as e:
                st.error(f"Erreur API : {e}")
