#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Script Streamlit : ICPE / VRD Analyzer (local RAG + API)

import streamlit as st
import os
from io import BytesIO
from datetime import datetime
from PyPDF2 import PdfReader
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

# Imports RAG local
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline
from langchain.text_splitter import RecursiveCharacterTextSplitter

# === CONFIG PAGE ===
st.set_page_config(page_title="ICPE / VRD Analyzer", layout="centered", page_icon="🛠️")

# === STYLE ===
st.markdown("""
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
""", unsafe_allow_html=True)

# === BARRE LATÉRALE ===
st.sidebar.title("🧭 Navigation")
MODE = st.sidebar.radio("🧠 Mode d'analyse :", ["Démo hors ligne", "API OpenAI (GPT)"])

st.sidebar.markdown("📂 **Téléverse un document réglementaire**")
uploaded_file = st.sidebar.file_uploader("Fichier PDF", type=["pdf"], label_visibility="collapsed")

# Extraction du texte brut du PDF
def read_pdf_file(uploaded):
    reader = PdfReader(uploaded)
    return "\n".join([page.extract_text() or "" for page in reader.pages])

pdf_text = ""
if uploaded_file is not None:
    st.sidebar.success(f"✅ Fichier chargé : {uploaded_file.name}")
    try:
        pdf_text = read_pdf_file(uploaded_file)
        with st.expander("🧾 Voir le contenu du PDF importé"):
            st.write(pdf_text[:1000] + ("..." if len(pdf_text) > 1000 else ""))
    except Exception as e:
        st.sidebar.error(f"Erreur lors de la lecture du PDF : {e}")

# === INIT LOCAL RAG ===
@st.cache_resource
def init_local_rag(
    text: str,
    chunk_size: int = 1024,
    overlap: int = 80,
    embed_model: str = "sentence-transformers/all-MiniLM-L6-v2",
    gen_model: str = "google/flan-t5-large"
):
    # découpage
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=overlap)
    chunks = splitter.split_text(text)
    # embeddings
    embedder = SentenceTransformer(embed_model)
    embeddings = embedder.encode(chunks, convert_to_numpy=True, normalize_embeddings=True)
    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)
    # générateur
    tokenizer = AutoTokenizer.from_pretrained(gen_model)
    model = AutoModelForSeq2SeqLM.from_pretrained(gen_model, device_map="auto")
    generator = pipeline("text2text-generation", model=model, tokenizer=tokenizer)
    return chunks, embedder, index, generator

# === SAISIE ===
st.markdown("## 🛠️ ICPE / VRD Analyzer")
st.info("👋 Décris ta modification VRD pour évaluer l’impact réglementaire ICPE.")

user_input = st.text_area("✍️ Modification VRD :", height=150)

# === ANALYSE ===
result_text = ""
if st.button("🔍 Analyser la situation"):
    if not user_input.strip():
        st.warning("⚠️ Décris d'abord ta modification VRD.")
    elif MODE == "Démo hors ligne":
        if not pdf_text:
            st.error("⚠️ Téléverse un PDF pour le mode hors ligne.")
        else:
            st.info("🧪 Mode local RAG")
            chunks, embedder, index, generator = init_local_rag(pdf_text)
            # retrieval
            q_emb = embedder.encode([user_input], convert_to_numpy=True, normalize_embeddings=True)
            scores, ids = index.search(q_emb, 5)
            candidates = [(i, s) for i, s in zip(ids[0], scores[0]) if s >= 0.5]
            if not candidates:
                candidates = [(ids[0][0], scores[0][0])]
            context = "\n\n".join(f"[Score {s:.2f}] {chunks[i]}" for i, s in candidates)
            prompt = f"Question ICPE/VRD: {user_input}\nContexte:\n{context}\nRéponds de façon concise en citant les articles."
            out = generator(prompt, max_new_tokens=256, num_beams=3, temperature=0.7)
            result_text = out[0]["generated_text"].strip()
            st.success("✅ Réponse :")
            st.write(result_text)
    else:
        st.info("🌐 Mode API OpenAI")
        # ... conserver bloc API GPT existant ...

# === EXPORT PDF ===
if result_text:
    # (génération PDF identique)
    pass

# === FOOTER ===
st.markdown("© 2025 Quartus · Tous droits réservés.")
