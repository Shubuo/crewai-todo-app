import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.environ.get("OPENAI_API_KEY")
model_name = os.environ.get("OPENAI_MODEL_NAME", "openrouter/owl-alpha")

print("-----------------------------------------")
print("API Key :", api_key[:10] + "..." if api_key else "BULUNAMADI!")
print("Model   :", model_name)
print("-----------------------------------------")

if not api_key:
    print("HATA: .env dosyasında OPENAI_API_KEY bulunamadı.")
    exit(1)

headers = {
    "Authorization": f"Bearer {api_key}",
    "HTTP-Referer": "http://localhost:5000",
    "X-Title": "DroneChecklist Test",
    "Content-Type": "application/json"
}

payload = {
    "model": model_name,
    "messages": [
        {"role": "user", "content": "Merhaba, bu bir API test mesajıdır. Lütfen sadece 'Bağlantı Başarılı' diye yanıt ver."}
    ]
}

print("OpenRouter'a istek gönderiliyor...\n")
try:
    response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
    
    print(f"Durum Kodu: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print("✅ BAŞARILI! Modelin Yanıtı:", data['choices'][0]['message']['content'])
    else:
        print("❌ HATA! API anahtarınız veya model isminiz reddedildi.")
        print("Hata Detayı:", response.text)
except Exception as e:
    print("Sistemsel Hata:", str(e))
