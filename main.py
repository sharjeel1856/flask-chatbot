from flask import Flask, request, jsonify
from transformers import pipeline
import pandas as pd
from difflib import get_close_matches
import warnings

warnings.filterwarnings("ignore")
app = Flask(__name__)

# Load LLM
llm = pipeline("text-generation", model="tiiuae/falcon-rw-1b", max_new_tokens=150, device_map="auto")

# Labels
labels = {
    "Admission": "Dr Gohar",
    "Scholarship": "Dr Naeem",
    "Student Affairs": "Sir Sibtual Hassan",
    "Academics": "Teacher Kinza",
    "Migration": "Dr Asim Zeb"
}

# Dataset
DATASET_PATH = "DATASET_CLEANED.xlsx"
sheets = ["Sheet1", "Sheet2", "Sheet3"]
qa_dict = {}
unread_messages = {teacher: 0 for teacher in labels.values()}

for sheet in sheets:
    df = pd.read_excel(DATASET_PATH, sheet_name=sheet, usecols=[0, 1], header=None, dtype=str)
    df.dropna(inplace=True)
    df.columns = ["Question", "Answer"]
    qa_dict.update(dict(zip(df["Question"], df["Answer"])))

# Common responses
common_responses = {
    "hi": "Hello! How can I assist you today?",
    "hello": "Hi there! What can I do for you?",
    # ... include all from your original file
}

domain_keywords = {
    "Admission": ["admission", "admit", "apply", "form"],
    "Scholarship": ["scholarship", "financial aid"],
    # ...
}

def get_answer_from_dataset(question):
    matches = get_close_matches(question, qa_dict.keys(), n=1, cutoff=0.6)
    if matches:
        return qa_dict[matches[0]]
    return None

def classify_query(query):
    query = query.lower()
    domain_match_counts = {domain: 0 for domain in domain_keywords.keys()}
    for domain, keywords in domain_keywords.items():
        for keyword in keywords:
            if keyword in query:
                domain_match_counts[domain] += 1
    max_matches = max(domain_match_counts.values())
    if max_matches > 0:
        best_domain = [domain for domain, count in domain_match_counts.items() if count == max_matches][0]
        teacher = labels[best_domain]
        unread_messages[teacher] += 1
        return best_domain, teacher
    teacher = labels["Student Affairs"]
    unread_messages[teacher] += 1
    return "Student Affairs", teacher

@app.route("/ask", methods=["POST"])
def ask():
    user_input = request.json.get("query", "").strip().lower()

    if user_input in common_responses:
        return jsonify({"response": common_responses[user_input]})

    answer = get_answer_from_dataset(user_input)
    if answer:
        return jsonify({"response": answer})

    try:
        llm_response = llm(f"Q: {user_input}\nA:", do_sample=True, temperature=0.7)[0]['generated_text']
        final_response = llm_response.split('\n')[0].replace(f"Q: {user_input}\nA:", "").strip()
        if final_response:
            return jsonify({"response": final_response})
    except:
        pass

    domain, teacher = classify_query(user_input)
    return jsonify({
        "response": f"Your query has been forwarded to {teacher} (Domain: {domain})."
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
