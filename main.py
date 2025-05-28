import pandas as pd
from difflib import get_close_matches
from transformers import pipeline
import warnings

warnings.filterwarnings("ignore")

# === Load Hugging Face Model ===
print("🔄 Loading Hugging Face model (tiiuae/falcon-rw-1b)...")
llm = pipeline("text-generation", model="tiiuae/falcon-rw-1b", max_new_tokens=150, device_map="auto")
print("✅ LLM ready.\n")

# === Domain and Teacher Setup ===
labels = {
    "Admission": "Dr Gohar",
    "Scholarship": "Dr Naeem",
    "Student Affairs": "Sir Sibtual Hassan",
    "Academics": "Teacher Kinza",
    "Migration": "Dr Asim Zeb"
}

DATASET_PATH = "C:/Agent/DATASET_CLEANED.xlsx"
sheets = ["Sheet1", "Sheet2", "Sheet3"]
qa_dict = {}
unread_messages = {teacher: 0 for teacher in labels.values()}

# === Load Dataset ===
for sheet in sheets:
    df = pd.read_excel(DATASET_PATH, sheet_name=sheet, usecols=[0, 1], header=None, dtype=str)
    df.dropna(inplace=True)
    df = df[df[0].str.strip() != ""]
    df.columns = ["Question", "Answer"]
    qa_dict.update(dict(zip(df["Question"], df["Answer"])))

# === Common Responses ===
common_responses = {
    "hi": "Hello! How can I assist you today?",
    "hello": "Hi there! What can I do for you?",
    "hey": "Hey! How can I help you?",
    "good morning": "Good morning! How can I assist you today?",
    "good afternoon": "Good afternoon! What can I do for you?",
    "good evening": "Good evening! How can I help you?",
    "bye": "Goodbye! Have a great day!",
    "goodbye": "See you later! Take care!",
    "thank you": "You're welcome!",
    "thanks": "You're welcome!",
    "welcome": "Thank you! How can I assist you further?",
    "how are you": "I'm just a bot, but I'm here to help you! How can I assist you today?",
    "what's up": "Not much, just here to help you! What can I do for you?"
}

# === Domain Classification ===
domain_keywords = {
    "Admission": ["admission", "admit", "apply", "form", "test", "document", "verification", "eligibility", "deadline"],
    "Scholarship": ["scholarship", "financial aid", "grant", "funding", "tuition", "discount", "fee waiver"],
    "Student Affairs": ["event", "club", "extracurricular", "activity", "engagement", "student life", "hostel", "facility"],
    "Academics": ["exam", "course", "grade", "attendance", "syllabus", "result", "academic", "lecture", "assignment"],
    "Migration": ["migration", "transfer", "relocation", "visa", "immigration", "international", "abroad"]
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
    # Fallback
    teacher = labels["Student Affairs"]
    unread_messages[teacher] += 1
    return "Student Affairs", teacher

def ask_llm(prompt):
    response = llm(prompt, do_sample=True, temperature=0.7)[0]['generated_text']
    return response.split('\n')[0].replace(prompt, '').strip()

# === Main Loop ===
print("🤖 Welcome to the AUST Guidance Chatbot (Terminal Version with LLM)")
print("Type 'exit' to quit.\n")

while True:
    user_input = input("You: ").strip().lower()

    if user_input in ["exit", "quit"]:
        print("Bot: Goodbye!")
        break

    if user_input in common_responses:
        print(f"Bot: {common_responses[user_input]}")
        continue

    # Step 1: Try to answer from dataset
    answer = get_answer_from_dataset(user_input)
    if answer:
        print(f"Bot: {answer}")
        continue

    # Step 2: Try answering using LLM
    print("Bot: Hmm, let me think about that...")
    try:
        llm_response = ask_llm(f"Q: {user_input}\nA:")
        if llm_response and len(llm_response.strip()) > 10:
            print(f"Bot (LLM): {llm_response}")
            accept = input("Was this answer helpful? (yes/no): ").strip().lower()
            if accept == "yes":
                qa_dict[user_input] = llm_response
                new_entry = pd.DataFrame({"Question": [user_input], "Answer": [llm_response]})
                with pd.ExcelWriter(DATASET_PATH, mode='a', engine='openpyxl', if_sheet_exists='replace') as writer:
                    new_entry.to_excel(writer, sheet_name="Sheet1", index=False, header=False)
                print("Bot: Great! I've saved that answer for future use.")
                continue
    except Exception as e:
        print("Bot: ⚠ LLM failed to respond.")

    # Step 3: Forward to domain-specific teacher
    domain, teacher = classify_query(user_input)
    print(f"Bot: I still couldn't find a good answer. Forwarding your query to {teacher} (Domain: {domain}).")
    response = input(f"{teacher}, please provide a response: ").strip()
    if response:
        qa_dict[user_input] = response
        new_entry = pd.DataFrame({"Question": [user_input], "Answer": [response]})
        with pd.ExcelWriter(DATASET_PATH, mode='a', engine='openpyxl', if_sheet_exists='replace') as writer:
            new_entry.to_excel(writer, sheet_name="Sheet1", index=False, header=False)
        unread_messages[teacher] = 0
        print(f"Bot: {response}")