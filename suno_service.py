import os
import time
import requests
import builtins
from dotenv import load_dotenv

# Forçar flushing imediato de logs (unbuffered stdout)
def print(*args, **kwargs):
    kwargs.setdefault('flush', True)
    builtins.print(*args, **kwargs)

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
    print("\n" + "="*80)
    print(" [DIAGNÓSTICO SUNO] INICIANDO GERAÇÃO DE MÚSICA ")
    print("="*80)
    
    # 1. Verifica se a chave KIE_AI_API_KEY está sendo lida corretamente
    print(f" -> KIE_AI_API_KEY configurada no .env? {'SIM (possui valor)' if KIE_AI_API_KEY else 'NÃO (está vazia/nula)'}")
    print(f" -> Valor parcial da KIE_AI_API_KEY: {KIE_AI_API_KEY[:8] + '...' if KIE_AI_API_KEY else 'Nenhum'}")
    
    # 2. Exibe o estilo musical recebido e o mapeamento enviado
    style_mapping = {
        "Sertanejo": "sertanejo universitario romantico",
        "MPB": "mpb romantica brasileira",
        "Pop": "pop romantico brasileiro",
        "Gospel": "gospel leve romantico"
    }
    suno_style = style_mapping.get(style, style)
    print(f" -> Estilo original solicitado: {repr(style)}")
    print(f" -> Estilo mapeado e enviado para Suno: {repr(suno_style)}")
    print(f" -> Título da faixa: {repr(title)}")
    
    # 3. Exibe a letra enviada para o Suno
    print(f" -> Letra da música enviada para o Suno:\n{'-'*40}\n{prompt}\n{'-'*40}")
    
    # 4. FORÇAR USO DA API REAL (Não usar o mock silencioso!)
    # Se a chave estiver ausente, avisamos que dará erro 401 mas tentamos assim mesmo para demonstrar a falha real da API.
    if not KIE_AI_API_KEY:
        print(" [WARNING] KIE_AI_API_KEY não foi encontrada! O sistema vai tentar bater na API real do Kie.ai para expor o erro real de autenticação no console.")

    url = f"{KIE_AI_BASE_URL}/api/v1/generate"
    headers = {
        "Authorization": f"Bearer {KIE_AI_API_KEY or ''}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "prompt": prompt,
        "customMode": True,
        "style": suno_style,
        "title": title,
        "instrumental": False,
        "model": "chirp-v3-5"
    }
    
    try:
        print(f" -> Realizando chamada HTTP POST para: {url}")
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        print(f" -> Status Code HTTP retornado: {response.status_code}")
        
        response_json = response.json()
        
        # 5. Mostra a resposta completa da API do Kie.ai
        print(f" -> Resposta COMPLETA da API Kie.ai:\n{response_json}\n")
        
        if response.status_code == 200 and response_json.get("code") == 200:
            data = response_json.get("data", {})
            task_id = data.get("taskId")
            if task_id:
                # 6. Mostra o taskId retornado
                print(f" [SUCCESS] taskId retornado com sucesso: {task_id}")
                print("="*80 + "\n")
                return {"task_id": task_id, "simulated": False}
                
        err_msg = f"Kie.ai retornou código de erro na resposta: {response_json}"
        print(f" [ERROR] {err_msg}")
        print("="*80 + "\n")
        raise Exception(err_msg)
        
    except Exception as e:
        print(f" [EXCEPTION] Falha durante chamada da API real do Kie.ai: {e}")
        print("="*80 + "\n")
        raise Exception(f"Kie.ai API Error: {e}")

def get_suno_status(task_id):
    """Consulta o status da geração de áudio no Kie.ai."""
    print("\n" + "="*80)
    print(f" [DIAGNÓSTICO SUNO] VERIFICANDO STATUS DO POLLING (taskId: {task_id}) ")
    print("="*80)
    
    # Suporte legado caso venha um ID mockado antigo, mas avisa
    if task_id.startswith("mock_suno_"):
        print(" -> Task ID mockado detectado. Executando simulação de status...")
        res = get_mock_status(task_id)
        print(f" -> Resultado da simulação: {res}")
        print("="*80 + "\n")
        return res
        
    url = f"{KIE_AI_BASE_URL}/api/v1/jobs/recordInfo?taskId={task_id}"
    headers = {
        "Authorization": f"Bearer {KIE_AI_API_KEY or ''}"
    }
    
    try:
        print(f" -> Realizando chamada HTTP GET para: {url}")
        response = requests.get(url, headers=headers, timeout=15)
        print(f" -> Status Code HTTP retornado: {response.status_code}")
        
        response_json = response.json()
        
        # Mostra o status de cada polling completo
        print(f" -> Resposta COMPLETA do Polling:\n{response_json}\n")
        
        if response.status_code == 200 and response_json.get("code") == 200:
            job_data = response_json.get("data", {})
            status = job_data.get("status", "").lower()
            print(f" -> Status retornado pelo job: {repr(status)}")
            
            if status in ["success"]:
                result = job_data.get("result", {})
                audio_url = None
                image_url = None
                
                if isinstance(result, dict):
                    result_data = result.get("data", [])
                    if result_data and isinstance(result_data, list):
                        audio_url = result_data[0].get("audio_url")
                        image_url = result_data[0].get("image_url")
                    else:
                        audio_url = result.get("audio_url")
                        image_url = result.get("image_url")
                        
                if not audio_url:
                    inner_data = job_data.get("data")
                    if inner_data and isinstance(inner_data, list):
                        audio_url = inner_data[0].get("audio_url")
                        image_url = inner_data[0].get("image_url")
                        
                if not image_url:
                    images = result.get("images", []) if isinstance(result, dict) else []
                    if images:
                        image_url = images[0]
                        
                # Mostra a URL do áudio final retornado
                print(f" -> URL de áudio extraída: {repr(audio_url)}")
                print(f" -> URL de imagem extraída: {repr(image_url)}")
                
                if audio_url:
                    print(f" [SUCCESS] Áudio final gerado com sucesso!")
                    print(f" -> URL final de áudio: {audio_url}")
                    print("="*80 + "\n")
                    return {
                        "status": "completed",
                        "audio_url": audio_url,
                        "stream_audio_url": audio_url,
                        "image_url": image_url or "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?w=500&q=80"
                    }
                else:
                    print(" -> O status do job está com sucesso, mas a URL do áudio ainda não está pronta na resposta.")
                    print("="*80 + "\n")
                    return {"status": "generating_audio"}
                    
            elif status in ["fail", "error"]:
                err_msg = job_data.get("failMsg", "Erro desconhecido informado pela API do Suno")
                print(f" [ERROR] Geração falhou na API do Suno: {err_msg}")
                print("="*80 + "\n")
                return {"status": "failed", "error": err_msg}
                
            elif status in ["generating"]:
                print(" -> A música está sendo gerada ativamente...")
                print("="*80 + "\n")
                return {"status": "generating_audio"}
                
            else:
                print(f" -> O status atual é {repr(status)} (tratando como gerando_áudio)...")
                print("="*80 + "\n")
                return {"status": "generating_audio"}
                
        err_msg = f"Falha na resposta do polling do Kie.ai: {response_json}"
        print(f" [ERROR] {err_msg}")
        print("="*80 + "\n")
        return {"status": "failed", "error": err_msg}
        
    except Exception as e:
        print(f" [EXCEPTION] Falha durante polling na API do Kie.ai: {e}")
        print("="*80 + "\n")
        return {"status": "failed", "error": str(e)}

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
