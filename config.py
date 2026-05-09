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

# Set for langchain
if GOOGLE_API_KEY:
    os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY
if GROQ_API_KEY:
    os.environ["GROQ_API_KEY"] = GROQ_API_KEY

# ==========================================
# LLM MODELS (Heterogeneous)
# ==========================================
# Router Agent: Fast domain classification
LLM_ROUTER = "llama-3.3-70b-versatile"

# Agent 1 (Analyzer): Fast structured extraction
LLM_ANALYZER = "llama-3.3-70b-versatile" 

# Agent 5 (Synthesizer): Long-context legal reasoning
LLM_SYNTHESIZER = "llama-3.3-70b-versatile"

# Fallback/General Model
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
