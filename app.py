"""
Improved Streamlit UI for Dental Clinic AI Receptionist
Simple, functional, and effective
"""

import streamlit as st
import re
from datetime import datetime
import threading

# Import your existing components
from receptionist import ReceptionistBrain
from db.db_utils import execute_query
from llm_utils import LLMHandler
from get_calendar_link import create_google_calendar_link
from voice_utils import speak, initialize_voice_system, mic
from dotenv import load_dotenv
import os

load_dotenv()

# Page configuration
st.set_page_config(
    page_title="🦷 Dental Clinic AI",
    page_icon="🦷",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Minimal, clean CSS
st.markdown("""
<style>
    .stApp {
        background-color: #f8f9fa;
    }
    
    .main-header {
        background: linear-gradient(135deg, #2196F3 0%, #1976D2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 1.5rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    
    .main-header h1 {
        margin: 0;
        font-size: 2rem;
    }
    
    .chat-container {
        background: white;
        border-radius: 10px;
        padding: 1.5rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        margin-bottom: 1rem;
        max-height: 500px;
        overflow-y: auto;
    }
    
    .message {
        margin-bottom: 1rem;
        padding: 0.8rem 1rem;
        border-radius: 8px;
        line-height: 1.6;
    }
    
    .user-message {
        background: #E3F2FD;
        border-left: 3px solid #2196F3;
        margin-left: 2rem;
    }
    
    .bot-message {
        background: #F5F5F5;
        border-left: 3px solid #4CAF50;
        margin-right: 2rem;
    }
    
    .message-label {
        font-weight: 600;
        margin-bottom: 0.3rem;
        font-size: 0.9rem;
    }
    
    .user-label {
        color: #1976D2;
    }
    
    .bot-label {
        color: #388E3C;
    }
    
    .calendar-btn {
        display: inline-block;
        background: #4CAF50;
        color: white !important;
        padding: 0.6rem 1.2rem;
        border-radius: 6px;
        text-decoration: none;
        font-weight: 600;
        margin-top: 0.5rem;
        transition: all 0.2s;
    }
    
    .calendar-btn:hover {
        background: #45a049;
        text-decoration: none;
        color: white !important;
    }
    
    .input-container {
        background: white;
        border-radius: 10px;
        padding: 1rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05);
    }
    
    div.stButton > button {
        border-radius: 6px;
        font-weight: 600;
        transition: all 0.2s;
    }
    
    div.stTextInput > div > div > input {
        border-radius: 6px;
    }
    
    .recording-status {
        background: #FFEBEE;
        border-left: 3px solid #F44336;
        padding: 0.8rem;
        border-radius: 6px;
        margin: 0.5rem 0;
        color: #C62828;
        font-weight: 600;
        animation: pulse 1.5s infinite;
    }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.7; }
    }
    
    .info-badge {
        background: #E8F5E9;
        border-left: 3px solid #4CAF50;
        padding: 0.5rem;
        border-radius: 6px;
        margin: 0.5rem 0;
        color: #2E7D32;
        font-size: 0.85rem;
    }
    
    .warning-badge {
        background: #FFF3E0;
        border-left: 3px solid #FF9800;
        padding: 0.5rem;
        border-radius: 6px;
        margin: 0.5rem 0;
        color: #E65100;
        font-size: 0.85rem;
    }
</style>
""", unsafe_allow_html=True)


def extract_urls(text):
    """Extract URLs from text."""
    url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    urls = re.findall(url_pattern, text)
    clean_text = re.sub(url_pattern, '[CALENDAR_LINK]', text)
    return clean_text, urls


def format_message(text, message_type='bot'):
    """Format message with calendar links."""
    clean_text, urls = extract_urls(text)
    
    # Replace [CALENDAR_LINK] placeholder with actual button
    if urls:
        for url in urls:
            button_html = f'<a href="{url}" target="_blank" class="calendar-btn">📅 Add to Google Calendar</a>'
            clean_text = clean_text.replace('[CALENDAR_LINK]', button_html, 1)
    
    label_class = 'user-label' if message_type == 'user' else 'bot-label'
    message_class = 'user-message' if message_type == 'user' else 'bot-message'
    label = '👤 You' if message_type == 'user' else '🤖 AI Receptionist'
    
    html = f'''
    <div class="message {message_class}">
        <div class="message-label {label_class}">{label}</div>
        <div>{clean_text}</div>
    </div>
    '''
    
    return html


def safe_speak(text):
    """Safely call speak function with error handling."""
    try:
        if st.session_state.voice_enabled:
            speak(text)
    except Exception as e:
        print(f"[WARNING] Could not speak response: {e}")


def initialize_session_state():
    """Initialize session state."""
    if 'initialized' not in st.session_state:
        st.session_state.llm_handler = LLMHandler()
        st.session_state.receptionist = ReceptionistBrain(
            llm_handler=st.session_state.llm_handler,
            db_executor=execute_query,
            calendar_creator=create_google_calendar_link
        )
        
        # Initialize voice system
        st.session_state.voice_enabled = False
        try:
            VOSK_MODEL_PATH = os.getenv("VOSK_MODEL_PATH")
            if VOSK_MODEL_PATH and os.path.exists(VOSK_MODEL_PATH):
                initialize_voice_system(VOSK_MODEL_PATH)
                st.session_state.voice_enabled = True
                print("[INFO] Voice system initialized successfully")
            else:
                print("[WARNING] VOSK_MODEL_PATH not found, voice features disabled")
        except Exception as e:
            print(f"[WARNING] Could not initialize voice system: {e}")
        
        st.session_state.initialized = True
    
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    
    if 'processing_voice' not in st.session_state:
        st.session_state.processing_voice = False


def process_input(user_input):
    """Process user input and get bot response."""
    if user_input and user_input.strip():
        # Add user message
        st.session_state.messages.append({
            'role': 'user',
            'content': user_input
        })
        
        # Get bot response
        with st.spinner('🤔 Thinking...'):
            bot_response = st.session_state.receptionist.process_query(user_input)
        
        # Add bot message
        st.session_state.messages.append({
            'role': 'bot',
            'content': bot_response
        })
        
        # Speak response in background (with error handling)
        threading.Thread(target=safe_speak, args=(bot_response,), daemon=True).start()
        
        return True
    return False


def handle_voice_input():
    """Handle voice input."""
    if not st.session_state.voice_enabled:
        st.error("❌ Voice system not available. Please check VOSK model configuration.")
        return
    
    st.session_state.processing_voice = True
    
    try:
        with st.spinner('🎤 Listening... Please speak now'):
            user_input = mic(timeout=10)
        
        if user_input and user_input.strip():
            process_input(user_input)
        else:
            st.warning("⚠️ No speech detected. Please try again.")
    
    except Exception as e:
        st.error(f"❌ Voice input error: {str(e)}")
    
    finally:
        st.session_state.processing_voice = False


def reset_conversation():
    """Reset the conversation."""
    st.session_state.messages = []
    st.session_state.receptionist.reset_conversation()
    st.session_state.processing_voice = False


def main():
    """Main application."""
    initialize_session_state()
    
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🦷 Dental Clinic AI Receptionist</h1>
        <p style="margin: 0.5rem 0 0 0;">24/7 Appointment Booking & Inquiries</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Main layout
    col1, col2 = st.columns([3, 1])
    
    with col2:
        st.markdown("### Controls")
        if st.button("🔄 Reset Chat", use_container_width=True, key="reset_btn"):
            reset_conversation()
            st.rerun()
        
        # Voice status indicator
        st.markdown("---")
        if st.session_state.voice_enabled:
            st.markdown('<div class="info-badge">✅ Voice system ready</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="warning-badge">⚠️ Voice system disabled</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("### Tips")
        st.markdown("""
        - Type your question or use voice
        - Press Enter to send text
        - Voice auto-speaks responses
        - Click calendar links to add appointments
        """)
    
    with col1:
        # Chat container
        st.markdown('<div class="chat-container">', unsafe_allow_html=True)
        
        if not st.session_state.messages:
            st.info("👋 Welcome! How can I help you today? Ask about appointments, services, or dental care.")
        else:
            for msg in st.session_state.messages:
                st.markdown(
                    format_message(msg['content'], msg['role']),
                    unsafe_allow_html=True
                )
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Input area
        st.markdown('<div class="input-container">', unsafe_allow_html=True)
        
        # Text input with form for Enter key support
        with st.form(key=f'input_form_{len(st.session_state.messages)}', clear_on_submit=True):
            user_input = st.text_input(
                "Type your message:",
                placeholder="e.g., I need a teeth cleaning appointment next week",
                label_visibility="collapsed",
                key=f"text_input_{len(st.session_state.messages)}"
            )
            
            col_a, col_b, col_c = st.columns([2, 1, 1])
            
            with col_a:
                submit_btn = st.form_submit_button("📤 Send", use_container_width=True, type="primary")
            
            with col_b:
                # Voice button (outside form)
                pass
            
            with col_c:
                # Clear button
                pass
            
            if submit_btn and user_input:
                if process_input(user_input):
                    st.rerun()
        
        # Voice and Clear buttons (outside form)
        col_a, col_b, col_c = st.columns([2, 1, 1])
        
        with col_b:
            if st.button("🎤 Voice", use_container_width=True, disabled=st.session_state.processing_voice or not st.session_state.voice_enabled, key="voice_btn"):
                handle_voice_input()
                st.rerun()
        
        with col_c:
            if st.button("🗑️ Clear", use_container_width=True, key="clear_btn"):
                st.rerun()
        
        # Show recording status
        if st.session_state.processing_voice:
            st.markdown("""
            <div class="recording-status">
                🎙️ Recording in progress... Please speak clearly!
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; padding: 0.5rem;">
        <small>🦷 Dental Care Clinic | Available 24/7 | Emergency: +91-XXXX-XXXXX</small>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()