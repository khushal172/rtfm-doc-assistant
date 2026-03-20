import os
from dotenv import load_dotenv

load_dotenv()

def verify_connections():
    print("Verifying connections...")
    
    # 1. Verify Gemini
    try:
        from google import genai
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents='Respond with exactly one word: "Success"'
        )
        print(f"✅ Gemini API: {response.text.strip()}")
    except Exception as e:
        print(f"❌ Gemini API Error: {e}")

    # 2. Verify Upstash Vector
    try:
        from upstash_vector import Index
        index = Index.from_env()
        info = index.info()
        print(f"✅ Upstash Vector: Connected. Vector count: {info.vector_count}")
    except Exception as e:
        print(f"❌ Upstash Vector Error: {e}")

    # 3. Verify Upstash Redis
    try:
        from upstash_redis import Redis
        # The SDK expects UPSTASH_REDIS_REST_URL and UPSTASH_REDIS_REST_TOKEN in the env
        r = Redis.from_env()
        res = r.ping()
        print(f"✅ Upstash Redis: PING {res}")
    except Exception as e:
        print(f"❌ Upstash Redis Error: {e}")

if __name__ == "__main__":
    verify_connections()
