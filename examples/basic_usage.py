"""
Basic usage example for IndexTTS FastAPI
"""
import requests
from openai import OpenAI

# Example 1: Using OpenAI SDK
def example_openai_sdk():
    """Example using OpenAI Python SDK"""
    client = OpenAI(
        base_url="http://localhost:8000/v1",
        api_key="not-needed"
    )
    
    response = client.audio.speech.create(
        model="tts-1",
        voice="alloy",
        input="Hello! This is a test of IndexTTS FastAPI."
    )
    
    response.stream_to_file("output_openai.mp3")
    print("✓ Saved to output_openai.mp3")


# Example 2: Direct HTTP request
def example_http_request():
    """Example using direct HTTP requests"""
    url = "http://localhost:8000/v1/audio/speech"
    
    payload = {
        "model": "tts-1",
        "input": "Hello from HTTP request!",
        "voice": "alloy",
        "response_format": "wav"
    }
    
    response = requests.post(url, json=payload)
    response.raise_for_status()
    
    with open("output_http.wav", "wb") as f:
        f.write(response.content)
    
    print("✓ Saved to output_http.wav")


# Example 3: List available voices
def example_list_voices():
    """List all available voices"""
    url = "http://localhost:8000/v1/voices"
    
    response = requests.get(url)
    response.raise_for_status()
    
    voices = response.json()
    print(f"\nFound {len(voices['data'])} voices:")
    for voice in voices['data']:
        preset = " (preset)" if voice['is_preset'] else ""
        print(f"  - {voice['id']}: {voice['file_path']}{preset}")


# Example 4: Native API with file upload
def example_native_api():
    """Example using native API with file upload"""
    url = "http://localhost:8000/api/v1/tts"
    
    # Note: You need to have a voice file available
    files = {
        "spk_audio_prompt": open("path/to/voice.wav", "rb")
    }
    
    data = {
        "text": "Hello from native API!",
        "emo_alpha": 0.65,
        "temperature": 0.8,
    }
    
    response = requests.post(url, files=files, data=data)
    response.raise_for_status()
    
    with open("output_native.wav", "wb") as f:
        f.write(response.content)
    
    print("✓ Saved to output_native.wav")
    files["spk_audio_prompt"].close()


if __name__ == "__main__":
    print("IndexTTS FastAPI Examples")
    print("=" * 50)
    print("\nMake sure the API server is running:")
    print("  indextts-api")
    print("\nPress Enter to continue...")
    input()
    
    try:
        # Check if server is running
        response = requests.get("http://localhost:8000/health")
        response.raise_for_status()
        
        print("\n1. Using OpenAI SDK:")
        example_openai_sdk()
        
        print("\n2. Using HTTP requests:")
        example_http_request()
        
        print("\n3. Listing voices:")
        example_list_voices()
        
        print("\n" + "=" * 50)
        print("Examples completed!")
        
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to API server.")
        print("Please start the server first: indextts-api")
    except Exception as e:
        print(f"Error: {e}")

