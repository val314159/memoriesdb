import os
import dotenv
import ollama

dotenv.load_dotenv()

print("CHAT OLLAMA")
print("CHAT OLLAMA", os.getenv('OLLAMA_HOST'))
print("CHAT OLLAMA", os.getenv('PGPASSWORD'))
