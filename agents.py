import json
import traceback
from typing import Dict, Any, Optional


# ----------------------------
# Agent configurations
# ----------------------------
agent_configs: Dict[str, Dict[str, Any]] = {
    "message_manager": {
        "agent_name": "message_manager",
        "agent_role": "Router / Dispatcher",
        "agent_details": (
            "Decides which sub-agent should handle an incoming user query. "
            "Analyzes the user input and conversation context to route to appropriate agent."
        ),
        "prompt_template": (
            "You are the Message Manager for a dental clinic receptionist AI.\n\n"
            "User query: \"{input}\"\n"
            "Conversation context: {context}\n\n"
            "Analyze the query and decide which agent should handle it.\n\n"
            "Return ONLY a valid JSON object (no markdown, no extra text):\n"
            "{{\n"
            '  "target_agent": "<one of: generic_query_handler, appointment_manager>",\n'
            '  "reason": "<brief explanation>",\n'
            '  "user_intent": "<what user wants to do>"\n'
            "}}\n\n"
            "Rules:\n"
            "- Use 'generic_query_handler' for: greetings, general questions, dental care info, clinic hours\n"
            "- Use 'appointment_manager' for: booking appointments, checking appointments, providing personal details, "
            "any query related to scheduling or patient information\n"
        ),
    },

    "generic_query_handler": {
        "agent_name": "generic_query_handler",
        "agent_role": "Receptionist conversational agent",
        "agent_details": (
            "Handles simple conversational queries with warmth and professionalism."
        ),
        "prompt_template": (
            "You are a friendly dental clinic receptionist named Emma.\n\n"
            "User query: \"{input}\"\n"
            "Context: {context}\n\n"
            "Respond warmly and professionally. Return ONLY a valid JSON object:\n"
            "{{\n"
            '  "response": "<your friendly response in 1-3 sentences>",\n'
            '  "action": "none"\n'
            "}}\n\n"
            "Keep responses concise, warm, and helpful. Use a conversational tone."
        ),
    },

    "appointment_manager": {
        "agent_name": "appointment_manager",
        "agent_role": "Appointment and Client Manager",
        "agent_details": (
            "Manages the entire appointment booking flow including client creation, "
            "information gathering, and appointment scheduling."
        ),
        "prompt_template": (
            "You are the Appointment Manager for a dental clinic.\n\n"
            "User query: \"{input}\"\n"
            "Current context: {context}\n\n"
            "Your job: Manage client information collection and appointment booking.\n\n"
            "Return ONLY a valid JSON object:\n"
            "{{\n"
            '  "action": "<next_action>",\n'
            '  "response": "<what to say to user>",\n'
            '  "data_collected": {{}},\n'
            '  "missing_fields": [],\n'
            '  "ready_to_execute": false,\n'
            '  "function_call": null\n'
            "}}\n\n"
            "ACTIONS:\n"
            "- 'collect_info': Gathering client/appointment details\n"
            "- 'check_client': Need to verify if client exists in DB\n"
            "- 'check_appointments': Need to fetch client appointments\n"
            "- 'create_client': Ready to create new client profile\n"
            "- 'create_appointment': Ready to book appointment\n"
            "- 'provide_info': Just providing information, no DB action\n\n"
            "REQUIRED FIELDS FOR CLIENT:\n"
            "- first_name, last_name, phone_no, age, gender\n"
            "- email is optional\n\n"
            "REQUIRED FIELDS FOR APPOINTMENT:\n"
            "- appointment_date (YYYY-MM-DD), appointment_time (HH:MM), reason\n\n"
            "RULES:\n"
            "1. If user provides details, extract them and add to 'data_collected'\n"
            "2. If required fields are missing, ask for ONE field at a time in 'response'\n"
            "3. Set 'missing_fields' to list of still-needed fields\n"
            "4. When all required fields collected, set 'ready_to_execute': true\n"
            "5. For 'function_call', use format: {{'function': 'function_name', 'params': {{}}}}\n\n"
            "FUNCTION CALLS:\n"
            "- check_client_exists: {{'function': 'check_client_exists', 'params': {{'first_name': '', 'last_name': ''}}}}\n"
            "- get_client_appointments: {{'function': 'get_client_appointments', 'params': {{'client_id': 123}}}}\n"
            "- create_client: {{'function': 'create_client', 'params': {{'first_name': '', 'last_name': '', 'email': '', 'phone_no': '', 'age': 0, 'gender': ''}}}}\n"
            "- create_appointment: {{'function': 'create_appointment', 'params': {{'client_id': 123, 'appointment_date': '', 'appointment_time': '', 'reason': ''}}}}\n\n"
            "RESPONSE STYLE:\n"
            "- Be warm and professional\n"
            "- Ask for ONE piece of information at a time\n"
            "- Confirm information received\n"
            "- Current date for reference: {current_date}\n"
        ),
    },

    "sql_agent": {
        "agent_name": "sql_agent",
        "agent_role": "SQL query generator",
        "agent_details": (
            "Converts structured instructions into SQL queries for execution."
        ),
        "prompt_template": (
            "You are the SQL Agent. Generate SQL queries based on the instruction.\n\n"
            "Instruction: \"{input}\"\n\n"
            "Return ONLY a valid JSON object:\n"
            "{{\n"
            '  "sql": "<SQL query string>",\n'
            '  "query_type": "<SELECT/INSERT/UPDATE/DELETE>"\n'
            "}}\n\n"
            "TABLES:\n"
            "1. clients (client_id, first_name, last_name, email, phone_no, age, gender, created_at)\n"
            "2. appointments (appointment_id, client_id, appointment_date, appointment_time, reason, status)\n\n"
            "IMPORTANT:\n"
            "- Use proper SQL syntax for SQLite\n"
            "- Use single quotes for string values\n"
            "- For dates use 'YYYY-MM-DD' format\n"
            "- For times use 'HH:MM' format\n"
            "- Use datetime('now') for created_at timestamps\n"
        ),
    }
}


# ----------------------------
# Agent manager class
# ----------------------------
class AgentManager:
    """
    AgentManager builds prompts for different agents based on their templates.
    """

    def __init__(self, configs: Dict[str, Dict[str, Any]]):
        self.configs = configs.copy()
        for name, cfg in self.configs.items():
            if "prompt_template" not in cfg:
                raise ValueError(f"Agent config '{name}' is missing 'prompt_template'")

    def render_prompt(
        self, 
        agent_name: str, 
        input_text: str, 
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Render the full prompt for the given agent.

        :param agent_name: key of agent in agent_configs
        :param input_text: raw user input
        :param context: additional context data (dict)
        :return: final prompt string or None on error
        """
        try:
            if agent_name not in self.configs:
                print(f"[ERROR] Unknown agent: {agent_name}")
                return None

            template = self.configs[agent_name]["prompt_template"]
            
            # Prepare context string
            context_str = json.dumps(context if context else {}, indent=2)
            
            # Get current date if in context
            current_date = context.get('current_date', '') if context else ''
            
            # Substitute placeholders
            prompt = template.format(
                input=input_text,
                context=context_str,
                current_date=current_date
            )
            return prompt

        except Exception as e:
            print(f"[ERROR] Failed to render prompt for agent '{agent_name}': {e}")
            traceback.print_exc()
            return None

    def get_agent_config(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """Return the config dict for an agent."""
        return self.configs.get(agent_name)


# ----------------------------
# Example usage
# ----------------------------
if __name__ == "__main__":
    mgr = AgentManager(agent_configs)

    # Test examples
    context = {
        "client_id": None,
        "first_name": None,
        "last_name": None,
        "conversation_stage": "initial",
        "current_date": "2025-11-03"
    }

    examples = [
        ("message_manager", "Hi, I want to book an appointment", context),
        ("generic_query_handler", "What are your clinic hours?", context),
        ("appointment_manager", "I want to book an appointment", context),
        ("appointment_manager", "My name is Rohit Sharma", 
         {**context, "conversation_stage": "collecting_client_info"}),
    ]

    for agent_name, inp, ctx in examples:
        print("\n" + "=" * 70)
        print(f"Agent: {agent_name}")
        print(f"Input: {inp}")
        prompt = mgr.render_prompt(agent_name, inp, ctx)
        print("\n" + prompt[:500] + "..." if len(prompt) > 500 else prompt)