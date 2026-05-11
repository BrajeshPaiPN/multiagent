"""
Configuration Module
====================
Centralized configuration for the Legal Intelligence System.
Loads credentials from .env and initializes shared resources.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Fix Windows console encoding for Unicode output
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# Load environment variables
load_dotenv(Path(__file__).parent / ".env")

# ==========================================
# API CREDENTIALS
# ==========================================
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
NEO4J_URI = os.environ.get("NEO4J_URI", "")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "")

# Validate critical credentials on startup
if not GROQ_API_KEY:
    print("[WARN] GROQ_API_KEY is not set! LLM calls will fail.")
if not GOOGLE_API_KEY:
    print("[WARN] GOOGLE_API_KEY is not set! RAG Embeddings will fail.")
if not NEO4J_URI or not NEO4J_PASSWORD:
    print("[WARN] NEO4J credentials incomplete. Graph queries will be skipped.")

# Set for langchain
if GOOGLE_API_KEY:
    os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY
if GROQ_API_KEY:
    os.environ["GROQ_API_KEY"] = GROQ_API_KEY

# ==========================================
# LLM MODELS — Heterogeneous Multi-Model Strategy
# ==========================================
# Using different model families at each pipeline stage to prevent
# single-model bias and distribute reasoning across architectures.
#
# Pipeline stages:
#   1. ROUTER / EXTRACTION  → llama-3.1-8b-instant (Groq)
#      Low token task, fast structured output, ~500 tokens
#
#   2. SPECIALIST SYNTHESIS → llama-3.3-70b-versatile (Groq)
#      Complex long-form legal reasoning, 32k context window
#      Different model family from extraction = reduces bias
#
#   3. HALLUCINATION CHECK  → Two models for cross-validation:
#      v1: llama-3.1-8b-instant (fast first-pass)
#      v2: gemma2-9b-it (Google architecture, different reasoning path)
#
#   4. MASTER SYNTHESIZER   → llama-3.3-70b-versatile (Groq)
#      Deep reasoning to synthesize multiple expert drafts into one cohesive memo
#
#   5. CRITIC               → gemma2-9b-it (Groq / Google)
#      Different architecture from all synthesis models = unbiased review
#
#   6. CONTRACT ANALYSIS    → Gemini 2.5 Flash (Google AI)
#      1M token context — only model that can ingest full contracts

# Stage 1: Extraction / Routing (fast, low-token)
LLM_ROUTER   = "llama-3.1-8b-instant"
LLM_ANALYZER = "llama-3.1-8b-instant"    # used as extractor in each agent

# Stage 2: Specialist synthesis (fast, avoids 70B rate limits during parallel execution)
LLM_SYNTHESIZER = "llama-3.1-8b-instant"

# Stage 3: Hallucination verifier (cross-model validation)
LLM_VERIFIER_V1 = "llama-3.1-8b-instant"   # fast first-pass
LLM_VERIFIER_V2 = "gemma2-9b-it"            # Google family, independent check

# Stage 4: Master synthesizer (deep reasoning)
LLM_MASTER = "llama-3.3-70b-versatile"

# Stage 5: Critic (Google architecture, fresh perspective)
LLM_CRITIC = "gemma2-9b-it"

# Stage 6: Contract analysis (Google AI, massive context)
GEMINI_MODEL = "gemini-2.5-flash"

# ==========================================
# AUTHORITY HIERARCHY (for Hierarchy Scoring)
# ==========================================
# H = (A * J) / T
# A = Authority Level, J = Jurisdiction Match, T = Recency
AUTHORITY_LEVELS = {
    "Supreme Court of India": 100,
    "High Court": 75,
    "District Court": 50,
    "Tribunal": 25,
    "Commission": 15,
}

JURISDICTION_MATCH = {
    "same_state": 1.0,
    "different_state": 0.5,
    "central": 1.0,  # Federal/Central applies everywhere
}

# ==========================================
# CASE CATEGORIES
# ==========================================
CASE_CATEGORIES = [
    "Criminal Law",
    "Constitutional Law",
    "Civil Law",
    "Patent Law",
    "Real Estate Law",
    "Traffic Law",
    "Family Law",
    "Corporate Law",
    "Tax Law",
    "Cyber Law",
    "Environmental Law",
]

# ==========================================
# CURRENT YEAR (for temporal calculations)
# ==========================================
CURRENT_YEAR = 2026
