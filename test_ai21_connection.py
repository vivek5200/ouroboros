"""
Test script to verify AI21 Jamba API connection
================================================

Run this to test your AI21 API key before using it in production.
"""

import os
from dotenv import load_dotenv
from src.context_encoder import ContextEncoder, ContextEncoderConfig, EncoderProvider

# Load environment variables
load_dotenv()

def test_ai21_connection():
    """Test AI21 Jamba API connection."""
    
    print("🔍 Testing AI21 Jamba Cloud API Connection...\n")
    
    # Check if API key is set
    api_key = os.getenv("AI21_API_KEY")
    if not api_key or api_key == "your_ai21_api_key_here":
        print("❌ ERROR: AI21_API_KEY not set in .env file")
        print("\n📝 To fix:")
        print("1. Open .env file")
        print("2. Replace 'your_ai21_api_key_here' with your actual API key")
        print("3. Get API key from: https://studio.ai21.com/account/api-key")
        return False
    
    print(f"✅ API Key found: {api_key[:8]}...{api_key[-4:]}")
    
    # Create encoder with cloud config
    print("\n🌐 Initializing Context Encoder (AI21 Cloud)...")
    config = ContextEncoderConfig(provider=EncoderProvider.JAMBA_CLOUD)
    encoder = ContextEncoder(config)
    
    # Test with simple context
    print("\n🧪 Testing context compression...")
    test_context = """
# File: test.ts
export class TestService {
    async testMethod(param: string): Promise<void> {
        console.log("Test implementation");
    }
}
"""
    
    try:
        compressed = encoder.compress(
            codebase_context=test_context,
            target_files=["test.ts"],
            metadata={"test": "ai21_connection"}
        )
        
        print(f"\n✅ SUCCESS! AI21 Jamba API is working!")
        print(f"\n📊 Compression Stats:")
        print(f"   - Input tokens:  {compressed.tokens_in}")
        print(f"   - Output tokens: {compressed.tokens_out}")
        print(f"   - Ratio:         {compressed.compression_ratio:.1f}x")
        print(f"   - Model:         {compressed.metadata['model']}")
        
        print(f"\n📝 Summary Preview:")
        print(f"   {compressed.summary[:200]}...")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR: {type(e).__name__}: {e}")
        print("\n🔧 Troubleshooting:")
        print("1. Verify API key is correct")
        print("2. Check internet connection")
        print("3. Ensure AI21 account is active: https://studio.ai21.com/")
        return False


if __name__ == "__main__":
    success = test_ai21_connection()
    exit(0 if success else 1)
