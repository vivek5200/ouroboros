
import os
import google.generativeai as genai
import ai21
from dotenv import load_dotenv

load_dotenv()

def check_google():
    print("Checking Google (Gemini)...")
    key = os.getenv("GOOGLE_API_KEY")
    if not key:
        print("FAIL: GOOGLE_API_KEY not found in env")
        return
    
    genai.configure(api_key=key)
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content("Hello")
        print("Google: OK")
    except Exception as e:
        print(f"Google: FAIL - {e}")

def check_ai21():
    print("\nChecking AI21 (Jamba)...")
    key = os.getenv("AI21_API_KEY")
    if not key:
        print("FAIL: AI21_API_KEY not found in env")
        return

    try:
        client = ai21.AI21Client(api_key=key)
        # Simple call (list models or minimal completion)
        # Using Jamba instruct if possible, or just checking validation
        try:
             # Just checking client init sometimes isn't enough, need a call
             # Trying a simple completion
             response = client.chat.completions.create(
                 model="jamba-1.5-mini",
                 messages=[{"role": "user", "content": "Hi"}],
                 max_tokens=1
             )
             print("AI21: OK")
        except Exception as e:
             import traceback
             # traceback.print_exc()
             print(f"AI21: FAIL - {e}")

    except Exception as e:
        print(f"AI21: FAIL - {e}")

if __name__ == "__main__":
    check_google()
    check_ai21()
