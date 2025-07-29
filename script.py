import streamlit as st
import os
from PyPDF2 import PdfReader
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from datetime import datetime

# —— NOUVEAUX IMPORTS POUR RAG LOCAL ——
import glob
import faiss
import numpy as np
import fitz
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline

# === CONFIG PAGE ===
st.set_page_config(page_title="ICPE / VRD Analyzer", layout="centered", page_icon="🛠️")

# === STYLE ===
st.markdown(
    """
    <style>
    .stApp {
        background-image: url("https://cdn.dribbble.com/users/527451/screenshots/3115734/safetynow_frame1-drib.gif");
        background-size: cover;
        background-attachment: fixed;
        background-position: center;
    }
    .main .block-container {
        background-color: rgba(255,255,255,0.9);
        border-radius: 15px;
        padding: 2rem;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# === BARRE LATÉRALE ===
st.sidebar.title("🧭 Navigation")
MODE = st.sidebar.radio("🧠 Mode d'analyse :", ["Démo hors ligne", "API OpenAI (GPT)"])

st.sidebar.markdown("📂 **Téléverse un document réglementaire**")
uploaded_file = st.sidebar.file_uploader("Fichier PDF", type=["pdf"], label_visibility="collapsed")

# Extraction du texte brut du PDF
pdf_text = ""
if uploaded_file is not None:
    st.sidebar.success(f"✅ Fichier chargé : {uploaded_file.name}")
    try:
        reader = PdfReader(uploaded_file)
        pdf_text = "\n".join([page.extract_text() or "" for page in reader.pages])
        with st.expander("🧾 Voir le contenu du PDF importé"):
            st.write(pdf_text[:1000] + ("..." if len(pdf_text) > 1000 else ""))
    except Exception as e:
        st.sidebar.error(f"Erreur lors de la lecture du PDF : {e}")

# === EN-TÊTE ===
col1, col2 = st.columns([1, 5])
with col1:
    st.image("https://www.construction21.org/france/data/sources/users/20051/20230217094921-5quartuslogoversion1-noire.jpg", width=150)
with col2:
    st.markdown("## 🛠️ ICPE / VRD Analyzer")
    st.markdown("**Outil d'analyse réglementaire des projets VRD liés aux ICPE**")

st.markdown("---")
st.info("👋 Bienvenue ! Décris ici ta modification VRD pour évaluer son impact réglementaire ICPE.")

# === SAISIE DE L'UTILISATEUR ===
st.markdown("### ✍️ Décris la modification VRD à analyser")
with st.expander("🔍 Besoin d'un exemple ?"):
    st.markdown("""
    **Exemple :**  
    Déplacement d'un bassin de rétention vers l'ouest, en dehors de la zone inondable,  
    pour libérer l'accès pompier. Le nouveau bassin aura une capacité de 60 000 m³.
    """)

user_input = st.text_area(
    "Saisie de la modification VRD :",
    placeholder="Décris ici ta modification (ouvrage, zone, raison, impact...)",
    height=200
)

# === FONCTIONS UTILES RAG LOCAL ===
from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

def generate_answer(question, chunks, index, embedder, generator):
    # 1. Embedding de la question
    q_emb = embedder.encode([question], convert_to_numpy=True)
    q_emb /= np.linalg.norm(q_emb, axis=1, keepdims=True)
    
    # 2. Retrieval avec FAISS (top 3 chunks)
    scores, indices = index.search(q_emb, 3)
    context = "\n".join([chunks[i] for i in indices[0]])
    
    # 3. Construction du prompt adapté à Flan-T5
    prompt = f"""
Question: {question}
Contexte: {context}
Réponds précisément en t'appuyant sur le contexte réglementaire ICPE.
Réponse:"""
    
    # 4. Génération avec paramètres optimisés
    answer = generator(
        prompt,
        max_length=256,
        num_beams=3,
        repetition_penalty=1.5,
        early_stopping=True,
        temperature=0.7
    )[0]['generated_text']
    
    return answer

# === BOUTON ANALYSE ===
result_text = ""
if st.button("🔍 Analyser la situation"):
    if not user_input.strip():
        st.warning("⚠️ Décris d'abord ta modification VRD.")
    else:
        if MODE == "Démo hors ligne":
            if not pdf_text:
                st.error("⚠️ Téléverse un document PDF pour le mode hors ligne.")
            else:
                st.info("🧪 Mode démonstration **local RAG**")
                chunks, embedder, index, generator = init_local_rag(pdf_text)

                # --- RETRIEVAL OPTIMISÉ ---
                q_emb = embedder.encode([user_input], convert_to_numpy=True)
                q_emb /= np.linalg.norm(q_emb, axis=1, keepdims=True)
                scores, ids = index.search(q_emb, 5)  # 5 chunks pour plus de contexte
                
                # Filtrage par score de similarité
                context_chunks = [chunks[i] for i, score in zip(ids[0], scores[0]) if score > 0.2]
                context = "\n".join(context_chunks) if context_chunks else chunks[ids[0][0]]

                # --- PROMPT ADAPTÉ FLAN-T5 ---
                local_prompt = f"""
                Question ICPE/VRD: {user_input}
                Contexte réglementaire: {context}
                Exigences de réponse:
                - Sois concis et technique
                - Cite les articles de loi applicables
                - Propose une solution pratique
                Réponse:
                """

                # --- GÉNÉRATION AVEC PARAMÈTRES OPTIMISÉS ---
                with st.spinner("⌛ Analyse en cours (modèle local)..."):
                    try:
                        out = generator(
                            local_prompt,
                            max_new_tokens=512,
                            num_beams=3,
                            do_sample=True,
                            temperature=0.7,
                            top_k=40,
                            repetition_penalty=1.2,  # Évite les répétitions
                        )
                        raw_response = out[0]["generated_text"]
                        
                        # EXTRACTION INTELLIGENTE DE LA RÉPONSE
                        if "Réponse:" in raw_response:
                            answer = raw_response.split("Réponse:")[-1].strip()
                        else:
                            answer = raw_response.replace(local_prompt, "").strip()
                        
                        # NETTOYAGE FINAL
                        answer = (answer
                                 .replace("<pad>", "")
                                 .replace("</s>", "")
                                 .split("###")[0]
                                 .strip())

                    except Exception as e:
                        st.error(f"Erreur de génération: {str(e)}")
                        answer = ""

                # --- AFFICHAGE ---
                if answer and len(answer) > 30:  # Vérifie que la réponse est valide
                    st.success("✅ Analyse réglementaire :")
                    st.markdown(f"""
                    <div style="
                        background-color: #f8f9fa;
                        border-left: 4px solid #28a745;
                        padding: 1rem;
                        margin: 1rem 0;
                        border-radius: 0.25rem;
                    ">
                        {answer}
                    </div>
                    """, unsafe_allow_html=True)
                    result_text = answer
                else:
                    st.warning("Le modèle n'a pas pu générer de réponse pertinente. Essayez avec plus de contexte.")

        else:  # === MODE OPENAI (GPT) ===
            try:
                from dotenv import load_dotenv
                from openai import OpenAI
                load_dotenv()
                client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

                # --- PROMPT STRUCTURÉ POUR GPT ---
                system_msg = """Tu es un expert ICPE/VRD français. Ta réponse doit:
                - Être concise et technique
                - Citer les articles de loi précis
                - Proposer des solutions pratiques
                - Éviter tout anglicisme
                Format de réponse:
                [Article] Texte de loi pertinent
                [Recommandation] Solution concrète
                """
                
                messages = [{"role": "system", "content": system_msg}]
                
                if pdf_text:
                    messages.append({
                        "role": "user",
                        "content": f"Document de référence:\n{pdf_text[:3000]}\n\nQuestion: {user_input}"
                    })
                else:
                    messages.append({"role": "user", "content": user_input})

                # --- APPEL API STREAMING ---
                with st.spinner("🔍 Consultation des textes réglementaires..."):
                    response = client.chat.completions.create(
                        model="gpt-4-turbo-preview",  # Modèle plus récent
                        messages=messages,
                        temperature=0.3,  # Un peu de flexibilité
                        max_tokens=1024,
                        stream=True  # Streaming pour l'expérience utilisateur
                    )
                    
                    # Affichage progressif
                    response_container = st.empty()
                    full_response = []
                    
                    for chunk in response:
                        chunk_content = chunk.choices[0].delta.content
                        if chunk_content:
                            full_response.append(chunk_content)
                            response_container.markdown("".join(full_response))

                result_text = "".join(full_response).strip()
                
                if result_text:
                    st.success("✅ Analyse complétée")
                    # Sauvegarde dans l'historique
                    if "historique" not in st.session_state:
                        st.session_state.historique = []
                    st.session_state.historique.append((user_input, result_text))

            except Exception as e:
                st.error(f"❌ Erreur API: {str(e)}")
                if "rate limit" in str(e).lower():
                    st.info("💡 Astuce: Essayez plus tard ou utilisez le mode hors ligne")

# === GÉNÉRATION DE LA FICHE PDF ===
if user_input and result_text:
    def generate_pdf(user_input, result_text):
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        logo = ImageReader("https://www.galivel.com/media/full/nouveau_logo_quartus-5.jpg")
        logo_w, logo_h = 100, 40

        def wrap_lines(text, max_width):
            words = text.split()
            lines = []; cur = ""
            for w in words:
                test = w if not cur else f"{cur} {w}"
                if c.stringWidth(test) <= max_width:
                    cur = test
                else:
                    lines.append(cur); cur = w
            if cur: lines.append(cur)
            return lines

        # page 1 header/footer
        def draw_header_footer(page_num):
            c.setFont("Helvetica-Bold", 16)
            c.drawString(50, height - 50, "Fiche d'analyse ICPE / VRD")
            c.drawImage(logo, width - 150, height - 80, width=logo_w, height=logo_h, mask="auto")
            c.setFont("Helvetica", 10)
            c.drawString(50, height - 70, f"Date : {datetime.now():%d/%m/%Y %H:%M}")
            c.setFont("Helvetica-Oblique", 8)
            c.drawCentredString(width/2, 20, f"Page {page_num}")

        # écrire le contenu
        draw_header_footer(1)
        y = height - 100
        c.setFont("Helvetica-Bold", 12); c.drawString(50, y, "✍️ Modification décrite :")
        text_obj = c.beginText(50, y - 20); text_obj.setFont("Helvetica", 10)
        for line in wrap_lines(user_input, width-100):
            text_obj.textLine(line)
        c.drawText(text_obj)

        y2 = text_obj.getY() - 30
        c.setFont("Helvetica-Bold", 12); c.drawString(50, y2, "✅ Analyse réglementaire :")
        res_obj = c.beginText(50, y2 - 20); res_obj.setFont("Helvetica", 10)
        for line in wrap_lines(result_text, width-100):
            res_obj.textLine(line)
        c.drawText(res_obj)

        c.showPage(); c.save()
        buffer.seek(0)
        return buffer

    pdf_bytes = generate_pdf(user_input, result_text)
    st.download_button(
        label="📥 Télécharger la fiche PDF",
        data=pdf_bytes,
        file_name="fiche_analyse_ICPE_VRD.pdf",
        mime="application/pdf",
        use_container_width=True
    )

# === PIED DE PAGE ===
st.markdown('<div class="bottom">© 2025 Quartus · Tous droits réservés.</div>', unsafe_allow_html=True)
