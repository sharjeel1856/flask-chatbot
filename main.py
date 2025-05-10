from flask import Flask, request, render_template_string, redirect, url_for, session
import pandas as pd
from difflib import get_close_matches
import os

app = Flask(__name__)
app.secret_key = "supersecretkey"  # Needed for session management

# Define the labels corresponding to the five domains
labels = {
    "Admission": "Dr Gohar",
    "Scholarship": "Dr Naeem",
    "Student Affairs": "Sir Sibtual Hassan",
    "Academics": "Teacher Kinza",
    "Migration": "Dr Asim Zeb"
}

# Load the dataset from Excel
DATASET_PATH = "DATASET_CLEANED.xlsx" # Updated dataset file
sheets = ["Sheet1", "Sheet2", "Sheet3"]  # List of sheets to read
qa_dict = {}

unread_messages = {teacher: 0 for teacher in labels.values()}  # Track unread messages

for sheet in sheets:
    df = pd.read_excel(DATASET_PATH, sheet_name=sheet, usecols=[0, 1], header=None, dtype=str)
    df.dropna(inplace=True)
    df = df[df[0].str.strip() != ""]
    df.columns = ["Question", "Answer"]
    qa_dict.update(dict(zip(df["Question"], df["Answer"])))

# Common responses
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

# Domain keywords for rule-based classification
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
    
    # Count keyword matches for each domain
    for domain, keywords in domain_keywords.items():
        for keyword in keywords:
            if keyword in query:
                domain_match_counts[domain] += 1
    
    # Find the domain with the highest match count
    max_matches = max(domain_match_counts.values())
    if max_matches > 0:
        best_domain = [domain for domain, count in domain_match_counts.items() if count == max_matches][0]
        teacher = labels[best_domain]
        unread_messages[teacher] += 1
        return best_domain, teacher
    
    # Default to "Student Affairs" if no domain is matched
    teacher = labels["Student Affairs"]
    unread_messages[teacher] += 1
    return "Student Affairs", teacher

@app.route("/", methods=["GET", "POST"])
def home():
    chatbot_response = session.get("bot_response", "")
    if request.method == "POST":
        question = request.form.get("student_query", "").strip().lower()
        # Check if the question is a common prompt
        if question in common_responses:
            chatbot_response = common_responses[question]
        else:
            answer = get_answer_from_dataset(question)
            if answer:
                chatbot_response = answer
            else:
                domain, teacher = classify_query(question)
                session['unanswered_question'] = question
                session['assigned_teacher'] = teacher
                return redirect(url_for("teacher_input"))
        session["bot_response"] = chatbot_response
    return render_template_string(chatbot_template, chatbot_response=chatbot_response)

# Chatbot Interface Template (unchanged)
chatbot_template = """
<!DOCTYPE html>
<html>
<head>
    <title>AUST Guidance Chatbot</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #f4f4f9;
            margin: 0;
            padding: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
        }
        .chat-container {
            background: white;
            border-radius: 10px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
            width: 400px;
            padding: 20px;
        }
        h2 {
            text-align: center;
            color: #333;
        }
        form {
            display: flex;
            flex-direction: column;
        }
        input[type="text"] {
            padding: 10px;
            margin-bottom: 10px;
            border: 1px solid #ccc;
            border-radius: 5px;
            font-size: 16px;
        }
        button {
            padding: 10px;
            background-color: #007bff;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
        }
        button:hover {
            background-color: #0056b3;
        }
        .response {
            margin-top: 20px;
            padding: 10px;
            background-color: #e9ecef;
            border-radius: 5px;
            color: #333;
        }
    </style>
</head>
<body>
    <div class="chat-container">
        <h2>AUST Guidance Bot</h2>
        <form method="POST">
            <input type="text" name="student_query" placeholder="Ask a question...">
            <button type="submit">Ask</button>
        </form>
        <div class="response">
            <p>{{ chatbot_response }}</p>
        </div>
    </div>
</body>
</html>
"""

# Teacher Interface Template (unchanged)
teacher_template = """
<!DOCTYPE html>
<html>
<head>
    <title>Teacher Assistant</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #f4f4f9;
            margin: 0;
            padding: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
        }
        .teacher-container {
            background: white;
            border-radius: 10px;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
            width: 500px;
            padding: 20px;
        }
        h3 {
            text-align: center;
            color: #333;
        }
        .teacher-list {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            justify-content: center;
            margin-bottom: 20px;
        }
        .teacher-list button {
            padding: 10px 20px;
            background-color: #28a745;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
        }
        .teacher-list button:hover {
            background-color: #218838;
        }
        .unread {
            background: red;
            color: white;
            padding: 3px 7px;
            border-radius: 50%;
            font-size: 12px;
            margin-left: 5px;
        }
        textarea {
            width: 100%;
            padding: 10px;
            border: 1px solid #ccc;
            border-radius: 5px;
            font-size: 16px;
            margin-bottom: 10px;
        }
        .response {
            margin-top: 20px;
            padding: 10px;
            background-color: #e9ecef;
            border-radius: 5px;
            color: #333;
        }
    </style>
</head>
<body>
    <div class="teacher-container">
        <h3>Teachers</h3>
        <div class="teacher-list">
            {% for teacher, count in unread.items() %}
                <button onclick="selectTeacher('{{ teacher }}')">{{ teacher }}
                    {% if count > 0 %}
                        <span class="unread">{{ count }}</span>
                    {% endif %}
                </button>
            {% endfor %}
        </div>
        <h2>Respond to Student Query</h2>
        <form method="POST">
            <textarea name="teacher_response" placeholder="Enter response here..." rows="4"></textarea><br>
            <button type="submit">Send Response</button>
        </form>
        <div class="response">
            <p>{{ chatbot_response }}</p>
        </div>
    </div>
    <script>
        function selectTeacher(teacher) {
            alert("Selected: " + teacher);
        }
    </script>
</body>
</html>
"""

@app.route("/teacher", methods=["GET", "POST"])
def teacher_input():
    teacher = session.get('assigned_teacher', "Unknown teacher")
    question = session.get('unanswered_question', "Unknown question")
    chatbot_response = session.get("bot_response", "")
    if request.method == "POST":
        response = request.form.get("teacher_response", "").strip()
        if response:
            # Save the new question and answer to the dataset
            new_entry = pd.DataFrame({"Question": [question], "Answer": [response]})
            with pd.ExcelWriter(DATASET_PATH, mode='a', engine='openpyxl', if_sheet_exists='replace') as writer:
                new_entry.to_excel(writer, sheet_name="Sheet1", index=False, header=False)
            
            # Update the in-memory QA dictionary
            qa_dict[question] = response
            
            # Reset unread count for the teacher
            unread_messages[teacher] = 0
            
            # Clear session data
            session.pop('unanswered_question', None)
            session.pop('assigned_teacher', None)
            session["bot_response"] = response  # Update chatbot response
            return redirect(url_for("home"))  # Redirect to home to show response
    return render_template_string(teacher_template, unread=unread_messages, chatbot_response=chatbot_response)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
