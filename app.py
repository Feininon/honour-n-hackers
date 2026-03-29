from flask import Flask, render_template, request, jsonify
import ollama
import os

app = Flask(__name__)

# Configuration
LORE_FILE = "campaign_lore.txt"
RULES_FILE = "dnd_rules.txt"
MODEL = 'llama3.2'

# Ensure files exist to prevent errors
if not os.path.exists(LORE_FILE): 
    with open(LORE_FILE, 'w', encoding='utf-8') as f: f.write("--- CAMPAIGN CHRONICLE START ---\n")
if not os.path.exists(RULES_FILE): 
    with open(RULES_FILE, 'w', encoding='utf-8') as f: f.write("Standard D&D 5e Rules apply.")

def get_file_content(path):
    if not os.path.exists(path): return ""
    with open(path, "r", encoding="utf-8") as f: return f.read()

# --- PAGE ROUTES ---

@app.route('/')
def dashboard():
    lore = get_file_content(LORE_FILE)
    return render_template('dashboard.html', lore=lore)

@app.route('/create')
def create_page():
    return render_template('create.html')

# --- API ROUTES ---

# --- STEP 1: AI AUDIT & SUGGESTIONS ---
@app.route('/api/review_char', methods=['POST'])
def api_review():
    data = request.json.get('sheet')
    rules = get_file_content(RULES_FILE)
    
    # Prompting the AI to be an advisor, not a gatekeeper
    prompt = f"""
    SYSTEM: You are an expert D&D 5e Dungeon Master Advisor. 
    RULES: {rules}
    
    TASK: Review this Level 1 character proposal. 
    Provide a concise bulleted list of suggestions or warnings. 
    Check if the HP/AC math looks right and if the Bio fits the world.
    
    CHARACTER:
    {data}
    
    OUTPUT: Provide 3-4 bullet points of advice. If it looks perfect, say "The Oracle finds no fault in this hero."
    """
    try:
        response = ollama.generate(model= MODEL , prompt=prompt)['response']
        return jsonify({"feedback": response})
    except Exception as e:
        return jsonify({"error": str(e)})

# --- STEP 2: PERMANENT SAVE (DM APPROVED) ---
@app.route('/api/save_char', methods=['POST'])
def api_save():
    data = request.json.get('sheet')
    
    # Formatted block for the Retrieval Augmented Reasoning (RAR) engine
    sheet_str = f"""
[CHARACTER REGISTERED]
NAME: {data['name']} | RACE: {data['race']} | CLASS: {data['class']}
VITALS: HP:{data['vitals']['hp']} | AC:{data['vitals']['ac']} | INIT:{data['vitals']['init']}
STATS: S:{data['stats']['str']} D:{data['stats']['dex']} C:{data['stats']['con']} I:{data['stats']['int']} W:{data['stats']['wis']} CH:{data['stats']['cha']}
SAVES: {', '.join(data['saves'])} | SKILLS: {', '.join(data['skills'])}
GEAR: {data['gear']}
BIO: {data['bio']}
----------------------------------------------"""
    
    try:
        with open(LORE_FILE, "a", encoding="utf-8") as f:
            f.write(f"\n{sheet_str}\n")
        return jsonify({"status": "success", "message": "Character forged in the chronicle!"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/update_lore', methods=['POST'])
def update_lore():
    event = request.json.get('event')
    if not event: return jsonify({"status": "error"}), 400
    
    with open(LORE_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n\n[DM UPDATE]: {event}")
    return jsonify({"status": "success"})

@app.route('/api/ask', methods=['POST'])
def api_ask():
    # This was missing in your previous file!
    data = request.json
    query = data.get('query')
    dice = data.get('dice', 0)
    
    lore = get_file_content(LORE_FILE)
    rules = get_file_content(RULES_FILE)
    
    rar_prompt = f"""
    SYSTEM: You are a D&D DM Assistant using Retrieval Augmented Reasoning.
    
    CONTEXT (LORE & CHARACTERS):
    {lore}
    
    MECHANICS (RULES):
    {rules}
    
    DICE ROLL: {dice}
    DM QUESTION: {query}
    
    INSTRUCTIONS:
    1. REASONING: Analyze how the character's stats/lore interact with the dice roll and the rules.
    2. OUTCOME: Describe the logical result of the action.
    """
    
    try:
        response = ollama.generate(model=MODEL, prompt=rar_prompt)['response']
        return jsonify({"response": response})
    except Exception as e:
        return jsonify({"response": f"Oracle Error: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)

