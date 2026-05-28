import os
import sqlite3
import uuid
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# Tenta carregar variáveis do Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Determina se usará o Supabase
USE_SUPABASE = bool(SUPABASE_URL and SUPABASE_KEY)
supabase_client = None

if USE_SUPABASE:
    try:
        from supabase import create_client
        supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("Connected to Supabase successfully!")
    except Exception as e:
        print(f"Failed to connect to Supabase: {e}. Falling back to SQLite local database.")
        USE_SUPABASE = False

# Configuração do SQLite Local (Fallback)
DB_PATH = os.path.join(os.path.dirname(__file__), "orders.db")

def init_sqlite_db():
    """Inicializa a tabela SQLite se ela não existir."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            occasion TEXT NOT NULL,
            giver_name TEXT NOT NULL,
            receiver_name TEXT NOT NULL,
            story TEXT,
            style TEXT NOT NULL,
            lyrics TEXT,
            audio_url TEXT,
            stream_audio_url TEXT,
            image_url TEXT,
            suno_task_id TEXT,
            payment_status TEXT NOT NULL,
            status TEXT NOT NULL,
            expires_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

if not USE_SUPABASE:
    init_sqlite_db()
    print("Using SQLite local database (orders.db)")

def create_order(occasion, giver_name, receiver_name, story, style):
    """Cria um pedido com status pendente de pagamento."""
    order_id = str(uuid.uuid4())
    created_at = datetime.utcnow().isoformat()
    expires_at = (datetime.utcnow() + timedelta(days=30)).isoformat()
    
    order_data = {
        "id": order_id,
        "created_at": created_at,
        "occasion": occasion,
        "giver_name": giver_name,
        "receiver_name": receiver_name,
        "story": story,
        "style": style,
        "lyrics": None,
        "audio_url": None,
        "stream_audio_url": None,
        "image_url": None,
        "suno_task_id": None,
        "payment_status": "pending",
        "status": "pending",
        "expires_at": expires_at
    }

    if USE_SUPABASE:
        try:
            # Insere no Supabase
            response = supabase_client.table("orders").insert(order_data).execute()
            if response.data:
                return response.data[0]
        except Exception as e:
            print(f"Supabase write error: {e}. Falling back to SQLite temporary write.")
            # Se der erro no Supabase, salva no SQLite local
            init_sqlite_db()

    # Salva no SQLite local
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO orders (
            id, created_at, occasion, giver_name, receiver_name, story, style,
            lyrics, audio_url, stream_audio_url, image_url, suno_task_id,
            payment_status, status, expires_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        order_data["id"], order_data["created_at"], order_data["occasion"],
        order_data["giver_name"], order_data["receiver_name"], order_data["story"],
        order_data["style"], order_data["lyrics"], order_data["audio_url"],
        order_data["stream_audio_url"], order_data["image_url"], order_data["suno_task_id"],
        order_data["payment_status"], order_data["status"], order_data["expires_at"]
    ))
    conn.commit()
    conn.close()
    return order_data

def get_order(order_id):
    """Recupera um pedido pelo seu ID."""
    if USE_SUPABASE:
        try:
            response = supabase_client.table("orders").select("*").eq("id", order_id).execute()
            if response.data:
                return response.data[0]
        except Exception as e:
            print(f"Supabase read error: {e}. Checking SQLite.")

    # Busca no SQLite local
    init_sqlite_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return None

def update_order(order_id, update_data):
    """Atualiza as informações de um pedido específico."""
    if USE_SUPABASE:
        try:
            response = supabase_client.table("orders").update(update_data).eq("id", order_id).execute()
            if response.data:
                return response.data[0]
        except Exception as e:
            print(f"Supabase update error: {e}. Falling back to SQLite.")

    # Atualiza no SQLite local
    init_sqlite_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Monta a query dinamicamente baseada nas chaves do update_data
    fields = []
    values = []
    for key, val in update_data.items():
        fields.append(f"{key} = ?")
        values.append(val)
    
    values.append(order_id)
    query = f"UPDATE orders SET {', '.join(fields)} WHERE id = ?"
    
    cursor.execute(query, tuple(values))
    conn.commit()
    conn.close()
    
    # Retorna o pedido atualizado
    return get_order(order_id)
