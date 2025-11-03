import json
import traceback
from datetime import datetime, date
from typing import Dict, Any, Optional
from agents import AgentManager, agent_configs


class ConversationState:
    """Manages conversation state across multiple turns."""
    
    def __init__(self):
        self.client_id: Optional[int] = None
        self.first_name: Optional[str] = None
        self.last_name: Optional[str] = None
        self.email: Optional[str] = ""
        self.phone_no: Optional[str] = None
        self.age: Optional[int] = None
        self.gender: Optional[str] = None
        
        # Appointment data
        self.appointment_date: Optional[str] = None
        self.appointment_time: Optional[str] = None
        self.appointment_reason: Optional[str] = None
        
        # Flow control
        self.conversation_stage: str = "initial"
        self.current_task: Optional[str] = None
        self.waiting_for: Optional[str] = None
        self.client_checked: bool = False  # Track if we've checked for existing client
        
        # Metadata
        self.current_date: str = date.today().strftime("%Y-%m-%d")
        self.current_time: str = datetime.now().strftime("%H:%M")
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary for context."""
        return {
            "client_id": self.client_id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "phone_no": self.phone_no,
            "age": self.age,
            "gender": self.gender,
            "appointment_date": self.appointment_date,
            "appointment_time": self.appointment_time,
            "appointment_reason": self.appointment_reason,
            "conversation_stage": self.conversation_stage,
            "current_task": self.current_task,
            "waiting_for": self.waiting_for,
            "client_checked": self.client_checked,
            "current_date": self.current_date,
            "current_time": self.current_time,
        }
    
    def update_from_dict(self, data: Dict[str, Any]):
        """Update state from collected data."""
        for key, value in data.items():
            if hasattr(self, key) and value is not None:
                setattr(self, key, value)
    
    def has_complete_name(self) -> bool:
        """Check if we have both first and last name."""
        return bool(self.first_name and self.last_name)
    
    def has_complete_client_info(self) -> bool:
        """Check if we have all required client info."""
        return bool(
            self.first_name and 
            self.last_name and 
            self.phone_no and 
            self.age and 
            self.gender
        )
    
    def has_complete_appointment_info(self) -> bool:
        """Check if we have all required appointment info."""
        return bool(
            self.appointment_date and 
            self.appointment_time and 
            self.appointment_reason
        )
    
    def reset(self):
        """Reset all state."""
        self.__init__()


class ReceptionistBrain:
    """
    Main orchestrator for the dental clinic receptionist.
    Improved flow with better name extraction and client checking.
    """
    
    def __init__(self, llm_handler, db_executor, calendar_creator):
        self.llm = llm_handler
        self.db = db_executor
        self.calendar = calendar_creator
        self.agent_mgr = AgentManager(agent_configs)
        self.state = ConversationState()
        
    def process_query(self, user_query: str) -> str:
        """
        Main entry point: takes user query, returns bot response.
        
        Flow:
        1. If appointment-related and no name -> Ask for name
        2. If we have name but not checked DB -> Check if client exists
        3. If new client -> Collect remaining info and create
        4. If existing client -> Proceed with task
        5. Handle generic queries normally
        """
        try:
            print(f"\n[DEBUG] Processing query: {user_query}")
            print(f"[DEBUG] Current stage: {self.state.conversation_stage}")
            print(f"[DEBUG] Client checked: {self.state.client_checked}")
            
            # Step 1: Route to determine intent
            routing = self._route_query(user_query)
            if not routing:
                return "I'm having trouble understanding. Could you please rephrase that?"
            
            target_agent = routing.get("target_agent", "generic_query_handler")
            print(f"[DEBUG] Routed to: {target_agent}")
            
            # Step 2: Handle based on agent type
            if target_agent == "generic_query_handler":
                return self._handle_generic_query(user_query)
            
            elif target_agent == "appointment_manager":
                return self._handle_appointment_workflow(user_query)
            
            else:
                return "I'm not sure how to help with that. Could you please clarify?"
                
        except Exception as e:
            print(f"[ERROR] in process_query: {e}")
            traceback.print_exc()
            return "I apologize, I encountered an error. Could you please try again?"
    
    def _route_query(self, user_query: str) -> Optional[Dict[str, Any]]:
        """Route query to appropriate agent."""
        try:
            prompt = self.agent_mgr.render_prompt(
                "message_manager",
                user_query,
                self.state.to_dict()
            )
            
            response = self.llm.query(prompt)
            routing = self.llm.parse_json_from_text(response)
            return routing
            
        except Exception as e:
            print(f"[ERROR] in _route_query: {e}")
            return None
    
    def _handle_generic_query(self, user_query: str) -> str:
        """Handle non-appointment queries (info, greetings, etc.)."""
        try:
            prompt = self.agent_mgr.render_prompt(
                "generic_query_handler",
                user_query,
                self.state.to_dict()
            )
            
            response = self.llm.query(prompt)
            result = self.llm.parse_json_from_text(response)
            
            return result.get("response", "How can I help you today?")
            
        except Exception as e:
            print(f"[ERROR] in _handle_generic_query: {e}")
            return "How can I assist you today?"
    
    def _handle_appointment_workflow(self, user_query: str) -> str:
        """
        Main appointment workflow with improved flow:
        1. Ask for name if we don't have it
        2. Check if client exists once we have name
        3. Branch based on new/existing client
        4. Collect and create as needed
        """
        try:
            # STEP 1: If we don't have a complete name, extract it first
            if not self.state.has_complete_name():
                name_extraction = self._extract_name_from_query(user_query)
                
                if name_extraction.get("has_name"):
                    self.state.first_name = name_extraction.get("first_name")
                    self.state.last_name = name_extraction.get("last_name")
                    print(f"[DEBUG] Extracted name: {self.state.first_name} {self.state.last_name}")
                    
                    # Now check if this client exists
                    return self._check_and_route_client()
                else:
                    # Still need name
                    return "To assist you better, could you please provide your full name? (For example: Raj Sharma)"
            
            # STEP 2: We have name but haven't checked DB yet
            if self.state.has_complete_name() and not self.state.client_checked:
                return self._check_and_route_client()
            
            # STEP 3: We know if client is new or existing, proceed with data collection
            if self.state.client_id:
                # Existing client - handle their request
                return self._handle_existing_client_flow(user_query)
            else:
                # New client - collect info and create
                return self._handle_new_client_flow(user_query)
                
        except Exception as e:
            print(f"[ERROR] in _handle_appointment_workflow: {e}")
            traceback.print_exc()
            return "I apologize, something went wrong. Could you please try again?"
    
    def _extract_name_from_query(self, user_query: str) -> Dict[str, Any]:
        """
        Use LLM to extract first and last name from various formats.
        Handles: "Raj Sharma", "my name is Kumar Sheety", "I'm Satyam Chillal", etc.
        """
        try:
            prompt = f"""Extract the person's first name and last name from the user query.

User Query: "{user_query}"

Instructions:
- Extract ONLY the person's first name and last name
- Handle formats like: "Raj Sharma", "my name is Kumar Sheety", "I'm Satyam Chillal"
- For middle initials or names, include with last name (e.g., "Raj J. Sharma" -> first: Raj, last: J. Sharma)
- If no name is found, set has_name to false

Return JSON format:
{{
    "has_name": true/false,
    "first_name": "FirstName",
    "last_name": "LastName"
}}

Examples:
Query: "Raj Sharma" -> {{"has_name": true, "first_name": "Raj", "last_name": "Sharma"}}
Query: "my name is Kumar Sheety" -> {{"has_name": true, "first_name": "Kumar", "last_name": "Sheety"}}
Query: "I'm Satyam Chillal" -> {{"has_name": true, "first_name": "Satyam", "last_name": "Chillal"}}
Query: "raj jk. Mahalotra" -> {{"has_name": true, "first_name": "Raj", "last_name": "JK Mahalotra"}}
Query: "yes" -> {{"has_name": false, "first_name": null, "last_name": null}}

JSON Response:"""

            response = self.llm.query(prompt)
            result = self.llm.parse_json_from_text(response)
            return result
            
        except Exception as e:
            print(f"[ERROR] in _extract_name_from_query: {e}")
            return {"has_name": False, "first_name": None, "last_name": None}
    
    def _check_and_route_client(self) -> str:
        """Check if client exists in DB and route accordingly."""
        try:
            # Check database
            client_check = self._check_client_exists(
                self.state.first_name, 
                self.state.last_name
            )
            
            self.state.client_checked = True
            
            if client_check and client_check.get("exists"):
                # Existing client found
                client_data = client_check.get("client")
                self.state.update_from_dict(client_data)
                self.state.conversation_stage = "existing_client"
                
                return (f"Welcome back, {self.state.first_name} {self.state.last_name}! "
                        f"How can I help you today? Would you like to book an appointment or check your existing appointments?")
            else:
                # New client
                self.state.conversation_stage = "new_client_collecting_info"
                return (f"Nice to meet you, {self.state.first_name} {self.state.last_name}! "
                        f"I'll need a few details to create your profile. Could you please provide your phone number?")
                
        except Exception as e:
            print(f"[ERROR] in _check_and_route_client: {e}")
            return "I had trouble checking our records. Could you please repeat your name?"
    
    def _handle_existing_client_flow(self, user_query: str) -> str:
        """Handle requests from existing clients."""
        try:
            # Use LLM to understand what they want to do
            prompt = self.agent_mgr.render_prompt(
                "appointment_manager",
                user_query,
                self.state.to_dict()
            )
            
            response = self.llm.query(prompt)
            result = self.llm.parse_json_from_text(response)
            
            action = result.get("action", "collect_info")
            bot_response = result.get("response", "")
            data_collected = result.get("data_collected", {})
            function_call = result.get("function_call")
            
            # Update state with any collected data
            if data_collected:
                self.state.update_from_dict(data_collected)
            
            # Execute function if needed
            if function_call:
                func_result = self._execute_function_call(function_call)
                
                if action == "check_appointments":
                    return self._format_appointments_response(func_result)
                
                elif action == "create_appointment":
                    return self._format_appointment_creation_response(func_result)
            
            return bot_response
            
        except Exception as e:
            print(f"[ERROR] in _handle_existing_client_flow: {e}")
            return "How can I help you today? Would you like to book an appointment or check your appointments?"
    
    def _handle_new_client_flow(self, user_query: str) -> str:
        """Handle data collection and creation for new clients."""
        try:
            # Use LLM to extract information from user query
            prompt = self.agent_mgr.render_prompt(
                "appointment_manager",
                user_query,
                self.state.to_dict()
            )
            
            response = self.llm.query(prompt)
            result = self.llm.parse_json_from_text(response)
            
            data_collected = result.get("data_collected", {})
            bot_response = result.get("response", "")
            function_call = result.get("function_call")
            
            # Update state with collected data
            if data_collected:
                self.state.update_from_dict(data_collected)
                print(f"[DEBUG] Updated state with: {data_collected}")
            
            # Check if we have all client info to create profile
            if self.state.has_complete_client_info() and not self.state.client_id:
                # Create the client
                client_id = self._create_client({
                    "first_name": self.state.first_name,
                    "last_name": self.state.last_name,
                    "email": self.state.email or "",
                    "phone_no": self.state.phone_no,
                    "age": self.state.age,
                    "gender": self.state.gender
                })
                
                if client_id:
                    self.state.client_id = client_id
                    self.state.conversation_stage = "existing_client"
                    return (f"Great! I've created your profile, {self.state.first_name}. "
                            f"Now, let's book your appointment. What is the reason for your visit?")
                else:
                    return "I had trouble creating your profile. Could you please verify your information?"
            
            # If we have client_id and complete appointment info, create appointment
            if self.state.client_id and self.state.has_complete_appointment_info():
                if function_call:
                    func_result = self._execute_function_call(function_call)
                    return self._format_appointment_creation_response(func_result)
            
            return bot_response
            
        except Exception as e:
            print(f"[ERROR] in _handle_new_client_flow: {e}")
            traceback.print_exc()
            return "I need a bit more information. Could you please repeat that?"
    
    def _execute_function_call(self, function_call: Dict[str, Any]) -> Any:
        """Execute the specified function call."""
        try:
            func_name = function_call.get("function")
            params = function_call.get("params", {})
            
            print(f"[DEBUG] Executing: {func_name} with {params}")
            
            if func_name == "check_client_exists":
                return self._check_client_exists(
                    params.get("first_name"),
                    params.get("last_name")
                )
            
            elif func_name == "get_client_appointments":
                return self._get_client_appointments(params.get("client_id"))
            
            elif func_name == "create_client":
                return self._create_client(params)
            
            elif func_name == "create_appointment":
                return self._create_appointment(params)
            
            else:
                print(f"[WARNING] Unknown function: {func_name}")
                return None
                
        except Exception as e:
            print(f"[ERROR] in _execute_function_call: {e}")
            traceback.print_exc()
            return None
    
    def _check_client_exists(self, first_name: str, last_name: str) -> Optional[Dict[str, Any]]:
        """Check if client exists in database."""
        try:
            sql = f"""
            SELECT client_id, first_name, last_name, email, phone_no, age, gender 
            FROM clients 
            WHERE LOWER(TRIM(first_name)) = LOWER(TRIM('{first_name}'))
            AND LOWER(TRIM(last_name)) = LOWER(TRIM('{last_name}'))
            LIMIT 1
            """
            
            result = self.db(sql)
            
            if result and len(result) > 0:
                row = result[0]
                return {
                    "exists": True,
                    "client": {
                        "client_id": row[0],
                        "first_name": row[1],
                        "last_name": row[2],
                        "email": row[3],
                        "phone_no": row[4],
                        "age": row[5],
                        "gender": row[6],
                    }
                }
            else:
                return {"exists": False, "client": None}
                
        except Exception as e:
            print(f"[ERROR] in _check_client_exists: {e}")
            return None
    
    def _get_client_appointments(self, client_id: int) -> Optional[list]:
        """Get all appointments for a client."""
        try:
            sql = f"""
            SELECT appointment_id, appointment_date, appointment_time, reason, status
            FROM appointments
            WHERE client_id = {client_id}
            ORDER BY appointment_date DESC, appointment_time DESC
            LIMIT 10
            """
            
            result = self.db(sql)
            
            if result:
                return [{
                    "appointment_id": row[0],
                    "date": row[1],
                    "time": row[2],
                    "reason": row[3],
                    "status": row[4]
                } for row in result]
            else:
                return []
                
        except Exception as e:
            print(f"[ERROR] in _get_client_appointments: {e}")
            return None
    
    def _create_client(self, params: Dict[str, Any]) -> Optional[int]:
        """Create new client in database."""
        try:
            # Escape single quotes in strings to prevent SQL errors
            first_name = params.get("first_name", "").replace("'", "''")
            last_name = params.get("last_name", "").replace("'", "''")
            email = params.get("email", "").replace("'", "''")
            phone_no = params.get("phone_no", "").replace("'", "''")
            gender = params.get("gender", "").replace("'", "''").capitalize()
            
            sql = f"""
            INSERT INTO clients (first_name, last_name, email, phone_no, age, gender, created_at)
            VALUES (
                '{first_name}',
                '{last_name}',
                '{email}',
                '{phone_no}',
                {params.get("age")},
                '{gender}',
                datetime('now')
            )
            """
            
            self.db(sql)
            print(f"[DEBUG] Client created successfully")
            
            # Get the created client_id
            check_result = self._check_client_exists(
                params.get("first_name"),
                params.get("last_name")
            )
            
            if check_result and check_result.get("exists"):
                return check_result["client"]["client_id"]
            
            return None
            
        except Exception as e:
            print(f"[ERROR] in _create_client: {e}")
            traceback.print_exc()
            return None
    
    def _create_appointment(self, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create new appointment in database."""
        try:
            reason = params.get("reason", "").replace("'", "''")
            
            sql = f"""
            INSERT INTO appointments (client_id, appointment_date, appointment_time, reason, status, created_at)
            VALUES (
                {params.get("client_id")},
                '{params.get("appointment_date")}',
                '{params.get("appointment_time")}',
                '{reason}',
                'Scheduled',
                datetime('now')
            )
            """
            
            self.db(sql)
            print(f"[DEBUG] Appointment created successfully")
            
            # Create calendar link
            calendar_link = self.calendar(
                title=f"Dental Appointment - {params.get('reason')}",
                app_date=params.get("appointment_date"),
                app_time=params.get("appointment_time"),
                duration_minutes=30,
                details=f"Appointment for {self.state.first_name} {self.state.last_name}",
                location="Dental Clinic"
            )
            
            return {
                "success": True,
                "calendar_link": calendar_link,
                "appointment_date": params.get("appointment_date"),
                "appointment_time": params.get("appointment_time"),
                "reason": params.get("reason")
            }
            
        except Exception as e:
            print(f"[ERROR] in _create_appointment: {e}")
            traceback.print_exc()
            return None
    
    def _format_appointments_response(self, appointments: Optional[list]) -> str:
        """Format appointments list into readable response."""
        if appointments is None:
            return "I couldn't retrieve your appointments. Please try again."
        
        if len(appointments) == 0:
            return f"You don't have any appointments scheduled, {self.state.first_name}. Would you like to book one?"
        
        response = f"Here are your appointments, {self.state.first_name}:\n\n"
        for apt in appointments:
            response += f"• {apt['date']} at {apt['time']} - {apt['reason']} ({apt['status']})\n"
        
        response += "\nWould you like to book another appointment?"
        return response
    
    def _format_appointment_creation_response(self, result: Optional[Dict]) -> str:
        """Format appointment creation result."""
        if result and result.get("success"):
            response = (f"Perfect! Your appointment is confirmed for "
                       f"{result['appointment_date']} at {result['appointment_time']} "
                       f"for {result['reason']}.")
            
            if result.get("calendar_link"):
                response += f"\n\nAdd to your calendar: {result['calendar_link']}"
            
            response += "\n\nIs there anything else I can help you with?"
            
            # Reset appointment data
            self.state.appointment_date = None
            self.state.appointment_time = None
            self.state.appointment_reason = None
            
            return response
        else:
            return "I had trouble booking your appointment. Could you please try again?"
    
    def reset_conversation(self):
        """Reset conversation state for new conversation."""
        self.state.reset()
        print("[INFO] Conversation state reset")


# Example usage
if __name__ == "__main__":
    class MockLLM:
        def query(self, prompt):
            return '{"response": "Hello!"}'
        
        def parse_json_from_text(self, text):
            try:
                return json.loads(text)
            except:
                return {}
    
    def mock_db(query):
        print(f"[MOCK DB] {query}")
        return []
    
    def mock_calendar(**kwargs):
        return "https://calendar.google.com/mock"
    
    brain = ReceptionistBrain(MockLLM(), mock_db, mock_calendar)
    print("[Test] Receptionist Brain initialized successfully")