import google.generativeai as genai
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Replace with your actual Gemini API Key
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

def chatbot():
    chat = model.start_chat(history=[])
    print("Gemini Chatbot: Hello! How can I assist you today? (Type 'exit' to end)")

    while True:
        user_input = input("You: ")
        if user_input.lower() == 'exit':
            print("Gemini Chatbot: Goodbye!")
            break

        response = chat.send_message(user_input)
        print("Gemini Chatbot:", response.text)

if __name__ == "__main__":
    chatbot()