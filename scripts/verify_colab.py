import requests
import sys

def verify(url):
    print(f"Testing connection to {url}...")
    try:
        response = requests.post(
            f"{url}/generate",
            json={
                "prompt": "# Python function to add two numbers\ndef add(a, b):\n",
                "max_tokens": 50
            },
            timeout=10
        )
        if response.status_code == 200:
            print("✅ Success! Server responded:")
            print("-" * 40)
            print(response.json().get("generated_text"))
            print("-" * 40)
            return True
        else:
            print(f"❌ Server returned error: {response.status_code}")
            print(response.text)
            return False
            
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

if __name__ == "__main__":
    # URL provided by user
    url = "https://unpoled-crawly-jefferey.ngrok-free.dev"
    
    print(f"Target URL: {url}")
    
    # Try a more explicit instruction
    prompt = "Write a Python function to calculate the factorial of a number."
    
    print(f"Sending prompt: {prompt}")
    
    # We call verify with the prompt (need to modify verify signature or just hack it here)
    # Re-implementing simplified verify here for clarity
    import requests
    try:
        response = requests.post(
            f"{url}/generate",
            json={
                "prompt": prompt,
                "max_tokens": 128,
                "temperature": 0.1
            },
            timeout=180  # LLaDA is slow - needs 2-3 minutes for 128 tokens
        )
        if response.status_code == 200:
            text = response.json().get("generated_text", "")
            print("✅ Success! Server responded:")
            print("-" * 40)
            print(f"Raw repr: {repr(text)}")
            print("-" * 40)
            print(text)
            print("-" * 40)
        else:
            print(f"❌ Server returned error: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ Connection failed: {e}")
