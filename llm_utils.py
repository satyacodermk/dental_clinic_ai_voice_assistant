import os
import re
import json
from dotenv import load_dotenv
from langchain_cohere import ChatCohere


class LLMHandler:
    """
    LLMHandler class to interact with Cohere's Chat API using LangChain integration.
    Supports:
    1. Loading API key from .env file
    2. Sending user queries to Cohere
    3. Parsing JSON from model responses
    4. Tracking conversation history (user + model responses)
    """

    def __init__(self, model_name: str = "command-a-03-2025"):
        """
        Initialize the LLMHandler by loading API key from .env and creating ChatCohere object.
        """
        # Load environment variables
        load_dotenv()
        self.api_key = os.getenv("COHERE_API_KEY")
        self.model_name = model_name
        self.conversation_history = []  # ✅ Stores full conversation details

        if not self.api_key:
            print("[ERROR] Missing COHERE_API_KEY in .env file.")
            self.llm = None
            return

        try:
            # Initialize Cohere Chat model
            self.llm = ChatCohere(
                cohere_api_key=self.api_key,
                model=self.model_name
            )
            print(f"[INFO] Cohere Chat model '{self.model_name}' initialized successfully.")
        except Exception as e:
            print(f"[ERROR] Failed to initialize Cohere Chat model: {e}")
            self.llm = None

    def query(self, user_input: str) -> str:
        """
        Send a query to the Cohere LLM and return its response.
        Also logs the user input and model output into conversation history.
        """
        if not self.llm:
            print("[ERROR] LLM not initialized.")
            return None

        try:
            response = self.llm.invoke(user_input)
            output_text = response.content.strip() if response else None

            # ✅ Log the conversation step
            self.conversation_history.append({
                "user": user_input,
                "llm_response": output_text
            })

            return output_text
        except Exception as e:
            print(f"[ERROR] Failed to get response from LLM: {e}")
            return None

    def parse_json_from_text(self, text: str):
        """
        Extract and parse a JSON object from raw text using regex.
        Returns a Python dict if valid JSON found, else None.
        """
        if not text:
            return None

        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if not json_match:
            return None

        json_str = json_match.group(0)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            print("[WARN] Failed to decode JSON from text.")
            return None

    def get_conversation_history(self):
        """
        Return the full conversation log (list of dicts with user + LLM responses).
        """
        return self.conversation_history


# ----------------- TEST SECTION -----------------
if __name__ == "__main__":
    handler = LLMHandler()

    if handler.llm:
        user_query_1 = """ Hi I am deve tiwari"""
        
        llm_response_1 = handler.query(user_query_1)
        print("\n[LLM Response 1]:", llm_response_1)
        parsed_json = handler.parse_json_from_text(llm_response_1)
        print("\n[Parsed JSON 1]:", parsed_json)

        user_query_2 = "give a short friendly message to greet a new dental clinic patient"
        llm_response_2 = handler.query(user_query_2)
        print("\n[LLM Response 2]:", llm_response_2)

        print("\n🧾 [Full Conversation History]:")
        for i, conv in enumerate(handler.get_conversation_history(), 1):
            print(f"{i}. USER: {conv['user']}")
            print(f"   LLM:  {conv['llm_response']}")



"""
this are  my db tables:

table_name:
CREATE TABLE IF NOT EXISTS clients (
    client_id INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100) DEFAULT '',
    phone_no VARCHAR(15) NOT NULL,
    age INTEGER CHECK(age >= 0 AND age <= 120) NOT NULL,
    gender VARCHAR(10) CHECK(gender IN ('Male', 'Female', 'Other')) NOT NULL,
    created_at DATETIME NOT NULL
);

table_name:
CREATE TABLE IF NOT EXISTS appointments (
    appointment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id INTEGER NOT NULL,
    appointment_date DATE NOT NULL,
    appointment_time TIME NOT NULL,
    reason VARCHAR(200) NOT NULL,
    status VARCHAR(20) CHECK(status IN ('Scheduled', 'Completed', 'Cancelled')) DEFAULT 'Scheduled',
    FOREIGN KEY (client_id) REFERENCES clients(client_id)
);

now write an sqlite query which help me to find the appointement of client with first_name: rohit, last_name: sharma

and return in terms of json key value like this ** strictly follow the format **:

## output format:
{{
"query":"<SQL statment>"
}}

## NOTE:
- make sure search for case in sensitive search and craft robust query"""