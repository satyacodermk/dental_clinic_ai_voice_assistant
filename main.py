"""
Integration Example: How to use the Receptionist Brain

This shows how to integrate your existing components:
- LLMHandler
- execute_query (DB function)
- create_google_calendar_link
"""

from receptionist import ReceptionistBrain
from datetime import datetime, date, time
from typing import Union, Optional


# ----------------------------
# Your existing functions (placeholders - replace with your actual implementations)
# ----------------------------
from db.db_utils import execute_query
from llm_utils import LLMHandler
from get_calendar_link import create_google_calendar_link


# ----------------------------
# Main Integration
# ----------------------------

def main():
    """
    Main function demonstrating the receptionist system.
    """
    
    # Initialize your components
    llm_handler = LLMHandler()
    
    # Initialize the receptionist brain
    receptionist = ReceptionistBrain(
        llm_handler=llm_handler,
        db_executor=execute_query,
        calendar_creator=create_google_calendar_link
    )
    
    print("=" * 70)
    print("🦷 Dental Clinic AI Receptionist")
    print("=" * 70)
    print("\nType 'quit' or 'exit' to end conversation")
    print("Type 'reset' to start a new conversation\n")
    
    # Conversation loop
    while True:
        try:
            # Get user input
            user_input = input("\nYou: ").strip()
            
            if not user_input:
                continue
            
            # Check for exit commands
            if user_input.lower() in ['quit', 'exit', 'bye']:
                print("\nBot: Thank you for visiting! Have a great day! 👋")
                break
            
            # Check for reset command
            if user_input.lower() == 'reset':
                receptionist.reset_conversation()
                print("\n[System] Conversation reset. Starting fresh!\n")
                continue
            
            # Process the query
            bot_response = receptionist.process_query(user_input)
            
            # Display response
            print(f"\nBot: {bot_response}")
            
        except KeyboardInterrupt:
            print("\n\nBot: Goodbye!")
            break
        except Exception as e:
            print(f"\n[ERROR] {e}")
            print("Bot: I apologize, something went wrong. Let's try again.")


# ----------------------------
# Example conversation flows
# ----------------------------

def test_conversation_flows():
    """
    Test different conversation scenarios without user input.
    Useful for development and testing.
    """
    
    llm_handler = LLMHandler()
    receptionist = ReceptionistBrain(
        llm_handler=llm_handler,
        db_executor=execute_query,
        calendar_creator=create_google_calendar_link
    )
    
    print("\n" + "=" * 70)
    print("SCENARIO 1: New Patient Booking")
    print("=" * 70)
    
    test_queries_1 = [
        "Hi, I want to book an appointment",
        "My name is Rohit Sharma",
        "My email is rohit@example.com and phone is +91-9876543210",
        "I'm 35 years old",
        "Male",
        "I need a teeth cleaning",
        "How about November 15th at 2:30 PM?",
    ]
    
    for query in test_queries_1:
        print(f"\nUser: {query}")
        response = receptionist.process_query(query)
        print(f"Bot: {response}")
    
    # Reset for next scenario
    receptionist.reset_conversation()
    
    print("\n" + "=" * 70)
    print("SCENARIO 2: Existing Patient Checking Appointments")
    print("=" * 70)
    
    test_queries_2 = [
        "Hi, I want to check my appointments",
        "I'm Priya Verma",
    ]
    
    for query in test_queries_2:
        print(f"\nUser: {query}")
        response = receptionist.process_query(query)
        print(f"Bot: {response}")
    
    print("\n" + "=" * 70)
    print("SCENARIO 3: General Query")
    print("=" * 70)
    
    receptionist.reset_conversation()
    
    test_queries_3 = [
        "What are your clinic hours?",
        "Do you provide teeth whitening services?",
    ]
    
    for query in test_queries_3:
        print(f"\nUser: {query}")
        response = receptionist.process_query(query)
        print(f"Bot: {response}")


# ----------------------------
# Voice Mode Integration (Future)
# ----------------------------

def voice_mode_example():
    """
    Example of how to integrate with voice (mic + speak functions).
    
    This shows the pattern you'll use when adding voice capabilities.
    """
    
    def mic() -> str:
        """Your microphone input function - captures and converts speech to text."""
        # Your implementation here
        pass
    
    def speak(text: str):
        """Your text-to-speech function - converts text to speech."""
        # Your implementation here
        pass
    
    # Initialize receptionist
    llm_handler = LLMHandler()
    receptionist = ReceptionistBrain(
        llm_handler=llm_handler,
        db_executor=execute_query,
        calendar_creator=create_google_calendar_link
    )
    
    # Voice conversation loop
    print("🎤 Voice mode activated. Say 'goodbye' to exit.")
    speak("Hello! How can I help you today?")
    
    while True:
        # Listen to user
        user_speech = mic()
        
        if not user_speech:
            continue
        
        if "goodbye" in user_speech.lower():
            speak("Thank you for visiting! Have a great day!")
            break
        
        # Process through receptionist (same function!)
        bot_response = receptionist.process_query(user_speech)
        
        # Speak the response
        speak(bot_response)


# ----------------------------
# Run
# ----------------------------

if __name__ == "__main__":
    # For interactive testing
    main()
    
    # For automated testing
    # test_conversation_flows()
    
    # For voice mode (future)
    # voice_mode_example()