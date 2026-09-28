import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("GEMINI_API_KEY is not configured.")
else:
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model='gemini-3.8-flash',
            contents='Reply with exactly: OK'
        )
        print("Success:")
        print(response.text)
    except Exception as e:
        print("Error:")
        print(e)
