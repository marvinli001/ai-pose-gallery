"""
Test OpenAI API Connection - English Only
"""
import asyncio
import httpx
from app.config import get_settings

async def test_openai_connection():
    """Test OpenAI API connection"""
    settings = get_settings()
    
    print("🔑 Testing OpenAI API connection...")
    print(f"API Key: {settings.openai_api_key[:10]}...{settings.openai_api_key[-4:]}")
    print(f"Base URL: {settings.openai_base_url}")
    print(f"Model: {settings.openai_model}")
    
    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json"
    }
    
    # Test simple text API (English only)
    payload = {
        "model": settings.openai_model,
        "messages": [
            {"role": "user", "content": "Hello, this is a test. Please respond with 'API connection successful'"}
        ],
        "max_tokens": 50
    }
    
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{settings.openai_base_url}/chat/completions",
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                print("✅ OpenAI API connection successful!")
                print(f"Response: {content}")
                
                # Check model info
                model_used = result.get('model', 'unknown')
                print(f"Model used: {model_used}")
                
                # Test image analysis capability
                await test_vision_capability(client, headers)
                
                return True
            else:
                print(f"❌ API call failed: {response.status_code}")
                print(f"Error: {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False

async def test_vision_capability(client, headers):
    """Test GPT-4o vision capability"""
    print("\n👁️ Testing Vision API capability...")
    
    # Simple base64 test image (1x1 pixel PNG)
    test_image_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
    
    payload = {
        "model": "gpt-4o",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Describe this image briefly."},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{test_image_base64}"
                        }
                    }
                ]
            }
        ],
        "max_tokens": 100
    }
    
    try:
        response = await client.post(
            f"{headers.get('Authorization', '').split()[-1] and 'https://api.openai.com/v1' or ''}/chat/completions",
            headers=headers,
            json=payload
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            print("✅ Vision API working!")
            print(f"Vision response: {content}")
            return True
        else:
            print(f"❌ Vision API failed: {response.status_code}")
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Vision test error: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_openai_connection())