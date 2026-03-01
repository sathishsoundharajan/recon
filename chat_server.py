import os
import glob
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pandasai import SmartDataframe
from pandasai.llm.local_llm import LocalLLM
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Allow CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
CSV_PATH = "recon-dashboard/public/recon_final_v2.csv"
STRATEGY_MD_PATH = "reconciliation_strategies.md"
SOURCE_DOCS_PATTERN = "source/*.md"
OLLAMA_MODEL = "llama3.1:8b" # or "qwen2.5-coder:7b" if available

# Global Data Cache
df = None
agent = None

def load_context():
    """Reads all strategy and contract markdown files to build the agent's context."""
    context_text = ""
    
    # 1. Read Strategy Guide
    if os.path.exists(STRATEGY_MD_PATH):
        with open(STRATEGY_MD_PATH, "r") as f:
            context_text += f"\n\n--- STRATEGY GUIDE ({STRATEGY_MD_PATH}) ---\n"
            context_text += f.read()
            
    return context_text

def initialize_agent():
    global df, agent
    print("Loading Data...")
    
    # Load Data
    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(f"CSV not found at {CSV_PATH}")
        
    df = pd.read_csv(CSV_PATH)
    print(f"Data Loaded: {len(df)} rows.")
    
    # Load Context
    print("Loading Context from Markdown files...")
    custom_instructions = load_context()
    print(f"Context Loaded ({len(custom_instructions)} chars).")
    
    # Initialize LLM (Ollama)
    llm = LocalLLM(api_base="http://localhost:11434/v1", model=OLLAMA_MODEL)
    
    # Initialize SmartDataFrame
    agent = SmartDataframe(
        df, 
        config={
            "llm": llm,
            "custom_instructions": f"""
            You are an expert Reconciliation Analyst for Samsung.
            You have access to a dataset of Delivery Orders (DOs) and their reconciliation status.
            
            Dataset Columns:
            - Related_Doc: The Delivery Order (DO) ID.
            - Status: The reconciliation status (e.g., MATCH, DISCREPANCY, UNDERCHARGED).
            - Amount: The invoiced amount.
            - Expected: The expected contract amount.
            - Diff: The difference (Amount - Expected).
            - Strategy: The logic used to reconcile.
            
            BUSINESS CONTEXT & CONTRACTS:
            {custom_instructions}
            
            GUIDELINES:
            1. Use the Context above to answer qualitative questions about "Why" or "Logic".
            2. Use the Data to answer quantitative questions about "How many" or "Sum".
            3. If the user asks about "Savings", look for 'UNDERCHARGED' status or negative Diff.
            4. If the user asks about "Overcharges", look for 'DISCREPANCY' or 'OVERCHARGED' or positive Diff.
            5. Always be concise.
            """
        }
    )
    print("Agent Initialized.")

# Initialize on Startup
@app.on_event("startup")
async def startup_event():
    initialize_agent()

class ChatRequest(BaseModel):
    query: str

@app.post("/chat")
def chat(request: ChatRequest):
    if agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    
    try:
        response = agent.chat(request.query)
        # PandasAI sometimes returns a plot path or a string. 
        # For now, we assume string. If it's a path, we might need to handle it.
        return {"response": str(response)}
    except Exception as e:
        print(f"Error during chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
