import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

KIE_AI_API_KEY = os.getenv("KIE_AI_API_KEY")
KIE_AI_BASE_URL = "https://api.kie.ai"

# Presets de áudio de alta qualidade e estáveis para o modo demonstração
PRESET_AUDIOS = {
    "Sertanejo": {
        "audio_url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
        "image_url": "https://images.unsplash.com/photo-1511192336575-5a79af67a629?w=500&q=80", # Violão rústico
        "duration": 372.0
    },
    "MPB": {
        "audio_url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3",
        "image_url": "https://images.unsplash.com/photo-1514525253161-7a46d19cd819?w=500&q=80", # Bossa Nova jazz club
        "duration": 423.0
    },
    "Pop": {
        "audio_url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-4.mp3",
        "image_url": "https://images.unsplash.com/photo-1470225620780-dba8ba36b745?w=500&q=80", # Luzes neon pop
        "duration": 302.0
    },
    "Gospel": {
        "audio_url": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-8.mp3",
        "image_url": "https://images.unsplash.com/photo-1465847899084-d164df4dedc6?w=500&q=80", # Teclado suave luz natural
        "duration": 318.0
    }
}

# Controle interno para simulação de status (Dicionário em memória)
# Para fins de simulação de polling
_mock_tasks = {}

def trigger_suno_generation(prompt, style, title):
    """Dispara a geração de música na API do Suno via Kie.ai."""
    if not KIE_AI_API_KEY:
        print("Kie.ai API key missing. Registering simulated Suno task.")
        return trigger_mock_generation(style)
        
    url = f"{KIE_AI_BASE_URL}/api/v1/generate"
    headers = {
        "Authorization": f"Bearer {KIE_AI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Mapeamento do estilo em português para as tags solicitadas do Suno
    style_mapping = {
        "Sertanejo": "sertanejo universitario romantico",
        "MPB": "mpb romantica brasileira",
        "Pop": "pop romantico brasileiro",
        "Gospel": "gospel leve romantico"
    }
    suno_style = style_mapping.get(style, style)
    
    payload = {
        "prompt": prompt,
        "customMode": True,
        "style": suno_style,
        "title": title,
        "instrumental": False,
        "model": "chirp-v3-5"
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response_json = response.json()
        
        if response.status_code == 200 and response_json.get("code") == 200:
            data = response_json.get("data", {})
            task_id = data.get("taskId")
            if task_id:
                print(f"Suno task created successfully: {task_id}")
                return {"task_id": task_id, "simulated": False}
                
        print(f"Kie.ai returned error code: {response_json}. Falling back to simulation.")
        return trigger_mock_generation(style)
    except Exception as e:
        print(f"Kie.ai API exception: {e}. Falling back to simulation.")
        return trigger_mock_generation(style)

def get_suno_status(task_id):
    """Consulta o status da geração de áudio no Kie.ai."""
    # Se for uma tarefa simulada
    if task_id.startswith("mock_suno_"):
        return get_mock_status(task_id)
        
    url = f"{KIE_AI_BASE_URL}/api/v1/jobs/recordInfo?taskId={task_id}"
    headers = {
        "Authorization": f"Bearer {KIE_AI_API_KEY}"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response_json = response.json()
        
        if response.status_code == 200 and response_json.get("code") == 200:
            job_data = response_json.get("data", {})
            status = job_data.get("status", "").lower()
            
            # Mapeamento de status da Kie.ai para o padrão interno do nosso app
            # Estados comuns: 'waiting', 'queuing', 'generating', 'success', 'fail'
            if status in ["success"]:
                # Faz a extração resiliente da URL do áudio, vídeo e imagem
                result = job_data.get("result", {})
                
                # Formato 1: result.data[0].audio_url
                # Formato 2: result.audio_url
                # Formato 3: job_data.data[0].audio_url (caso retorne direto em data)
                audio_url = None
                image_url = None
                
                # Caso result seja um dict
                if isinstance(result, dict):
                    result_data = result.get("data", [])
                    if result_data and isinstance(result_data, list):
                        audio_url = result_data[0].get("audio_url")
                        image_url = result_data[0].get("image_url")
                    else:
                        audio_url = result.get("audio_url")
                        image_url = result.get("image_url")
                        
                # Caso não tenha encontrado, tenta em job_data direto
                if not audio_url:
                    inner_data = job_data.get("data")
                    if inner_data and isinstance(inner_data, list):
                        audio_url = inner_data[0].get("audio_url")
                        image_url = inner_data[0].get("image_url")
                        
                if not image_url:
                    # Tenta imagens em result
                    images = result.get("images", []) if isinstance(result, dict) else []
                    if images:
                        image_url = images[0]
                        
                if audio_url:
                    return {
                        "status": "completed",
                        "audio_url": audio_url,
                        "stream_audio_url": audio_url,
                        "image_url": image_url or "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=500&q=80"
                    }
                else:
                    # Encontrou status de sucesso mas não achou os arquivos de áudio ainda
                    return {"status": "generating"}
                    
            elif status in ["fail", "error"]:
                return {"status": "failed", "error": job_data.get("failMsg", "Erro desconhecido na API do Suno")}
                
            elif status in ["generating"]:
                return {"status": "generating_audio"}
                
            else:
                return {"status": "generating_audio"}  # Qualquer estado intermediário (waiting, queuing) trata como gerando
                
        print(f"Kie.ai status check returned failure: {response_json}")
        return {"status": "generating_audio"}
    except Exception as e:
        print(f"Exception during Kie.ai status check: {e}")
        return {"status": "generating_audio"}

# --- FUNÇÕES AUXILIARES PARA SIMULAÇÃO ---

def trigger_mock_generation(style):
    """Cria uma tarefa simulada na memória."""
    mock_id = f"mock_suno_{int(time.time())}"
    _mock_tasks[mock_id] = {
        "created_at": time.time(),
        "style": style
    }
    return {"task_id": mock_id, "simulated": True}

def get_mock_status(task_id):
    """Simula o progresso realista da geração Suno ao longo do tempo."""
    task = _mock_tasks.get(task_id)
    if not task:
        # Se a tarefa sumiu da memória por reinício do app, resolve instantaneamente
        return {
            "status": "completed",
            "audio_url": PRESET_AUDIOS["MPB"]["audio_url"],
            "stream_audio_url": PRESET_AUDIOS["MPB"]["audio_url"],
            "image_url": PRESET_AUDIOS["MPB"]["image_url"]
        }
        
    elapsed = time.time() - task["created_at"]
    style = task["style"]
    preset = PRESET_AUDIOS.get(style, PRESET_AUDIOS["MPB"])
    
    # 0 a 6 segundos: Escrevendo a letra (tratado pelo backend separadamente, mas para o polling de áudio é 'generating_audio')
    # 6 a 12 segundos: Na fila do Suno
    # 12 a 20 segundos: Compondo e gravando o vocal
    # > 20 segundos: Sucesso absoluto!
    if elapsed < 8:
        return {"status": "generating_audio", "message": "Preparando arranjos especiais..."}
    elif elapsed < 16:
        return {"status": "generating_audio", "message": "Compondo a partitura e afinando instrumentos..."}
    elif elapsed < 22:
        return {"status": "generating_audio", "message": "Gravando os vocais e harmonizando a melodia..."}
    else:
        return {
            "status": "completed",
            "audio_url": preset["audio_url"],
            "stream_audio_url": preset["audio_url"],
            "image_url": preset["image_url"]
        }
