import os
import threading
import time
import builtins
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for
from dotenv import load_dotenv

# Forçar flushing imediato de logs (unbuffered stdout)
def print(*args, **kwargs):
    kwargs.setdefault('flush', True)
    builtins.print(*args, **kwargs)

# Carrega chaves do .env
load_dotenv()

import database as db
import openai_service as ai
import suno_service as suno

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "musicas_personalizadas_secret_key_129847")

MERCADO_PAGO_ACCESS_TOKEN = os.getenv("MERCADO_PAGO_ACCESS_TOKEN") or os.getenv("MERCADO_AGO_ACCESS_TOKEN")

def process_music_generation_background(order_id):
    """Gera a letra e compose a música em segundo plano para não travar a requisição."""
    print(f"Starting background generation for order: {order_id}")
    
    # 1. Atualiza status para gerando letra
    order = db.update_order(order_id, {"status": "generating_lyrics"})
    if not order:
        print(f"Order {order_id} not found.")
        return
        
    # Simula um pequeno delay para a experiência visual ficar orgânica
    time.sleep(2)
    
    # 2. Gera letra via OpenAI GPT-4
    try:
        lyrics_data = ai.generate_lyrics_with_gpt4(
            occasion=order["occasion"],
            giver=order["giver_name"],
            receiver=order["receiver_name"],
            story=order["story"],
            style=order["style"]
        )
        
        # Salva a letra gerada e o título e atualiza status para gerando áudio
        order = db.update_order(order_id, {
            "lyrics": lyrics_data["lyrics"],
            "status": "generating_audio"
        })
        song_title = lyrics_data["title"]
        print(f"Lyrics generated successfully: '{song_title}'")
    except Exception as e:
        print(f"Error generating lyrics: {e}")
        db.update_order(order_id, {"status": "failed"})
        return
        
    time.sleep(2)
    
    # 3. Dispara a geração de música via API Suno (Kie.ai)
    try:
        generation_data = suno.trigger_suno_generation(
            prompt=order["lyrics"],
            style=order["style"],
            title=song_title
        )
        
        suno_task_id = generation_data["task_id"]
        order = db.update_order(order_id, {
            "suno_task_id": suno_task_id
        })
        print(f"Suno generation triggered. Task ID: {suno_task_id}")
    except Exception as e:
        print(f"Error triggering Suno: {e}")
        db.update_order(order_id, {"status": "failed"})
        return
        
    # 4. Polling na API do Suno até concluir (tempo limite de 10 minutos)
    max_attempts = 40
    attempt = 0
    polling_interval = 12 if generation_data.get("simulated") else 20  # Menor tempo para simulações
    
    while attempt < max_attempts:
        attempt += 1
        print(f"Polling Suno status for task {suno_task_id} (Attempt {attempt}/{max_attempts})...")
        
        try:
            status_data = suno.get_suno_status(suno_task_id)
            status = status_data["status"]
            
            if status == "completed":
                # Música gerada com sucesso! Atualiza o banco de dados final
                db.update_order(order_id, {
                    "audio_url": status_data["audio_url"],
                    "stream_audio_url": status_data["stream_audio_url"],
                    "image_url": status_data["image_url"],
                    "status": "completed"
                })
                print(f"Music generation completed successfully for order {order_id}!")
                return
            elif status == "failed":
                error_msg = status_data.get("error", "Falha na geração do Suno.")
                print(f"Suno generation failed: {error_msg}")
                db.update_order(order_id, {"status": "failed"})
                return
        except Exception as e:
            print(f"Exception during background status polling: {e}")
            
        time.sleep(polling_interval)
        
    # Se estourar o limite
    print(f"Timeout reached for music generation of order {order_id}.")
    db.update_order(order_id, {"status": "failed"})

# --- ROTAS DA APLICAÇÃO ---

@app.route("/")
def home():
    """Serve a página principal com o formulário de 6 passos."""
    return render_template("index.html")

@app.route("/api/order", methods=["POST"])
def create_order():
    """Cria um pedido pendente e dispara a geração da prévia/música imediatamente."""
    data = request.json
    if not data:
        return jsonify({"error": "Dados ausentes"}), 400
        
    occasion = data.get("occasion")
    giver_name = "" # Forçado vazio para remover o campo do form e manter compatibilidade com DB
    receiver_name = data.get("receiver_name")
    story = data.get("story", "")
    style = data.get("style")
    
    if not all([occasion, receiver_name, style]):
        return jsonify({"error": "Preencha todos os campos obrigatórios."}), 400
        
    # Salva o pedido inicial no banco de dados
    order = db.create_order(occasion, giver_name, receiver_name, story, style)
    
    # Dispara a geração de música em segundo plano IMEDIATAMENTE (Etapa 2 - Prévia)
    threading.Thread(
        target=process_music_generation_background,
        args=(order["id"],),
        daemon=True
    ).start()
    
    return jsonify({
        "success": True,
        "order": order
    })

@app.route("/checkout-mp/<order_id>")
def checkout_mp_simulated(order_id):
    """Página temporária para apresentar o pagamento simulado ou redirecionar."""
    order = db.get_order(order_id)
    if not order:
        return "Pedido não encontrado", 404
        
    return render_template("checkout.html", order=order)

@app.route("/api/order/<order_id>/payment-init", methods=["POST"])
def payment_init(order_id):
    """Gera um pagamento PIX real ou simulado no Mercado Pago para o pedido."""
    import uuid
    order = db.get_order(order_id)
    if not order:
        return jsonify({"error": "Pedido não encontrado"}), 404
        
    # Se já tiver gerado o PIX anteriormente, apenas retorna o pedido atual
    if order.get("mp_payment_id") and order.get("pix_copy_paste") and order.get("pix_qr_code_base64"):
        return jsonify({
            "success": True,
            "order": order
        })
        
    mp_payment_id = None
    pix_copy_paste = None
    pix_qr_code_base64 = None
    
    # Se houver credenciais reais do Mercado Pago configuradas, tenta gerar o PIX real
    if MERCADO_PAGO_ACCESS_TOKEN:
        try:
            import mercadopago
            sdk = mercadopago.SDK(MERCADO_PAGO_ACCESS_TOKEN)
            
            # Expiração do PIX em 30 minutos
            expiration_time = (datetime.utcnow() + timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
            
            payment_data = {
                "transaction_amount": 29.90,
                "description": f"Música Personalizada - {order['occasion']} ({order['receiver_name']})",
                "payment_method_id": "pix",
                "date_of_expiration": expiration_time,
                "payer": {
                    "email": "cliente@amoremcancao.com.br",
                    "first_name": order["receiver_name"] or "Cliente",
                    "last_name": "AmorEmCancao"
                }
            }
            
            payment_response = sdk.payment().create(payment_data)
            payment = payment_response["response"]
            
            if payment.get("id"):
                mp_payment_id = str(payment.get("id"))
                point_of_interaction = payment.get("point_of_interaction", {})
                transaction_data = point_of_interaction.get("transaction_data", {})
                
                pix_copy_paste = transaction_data.get("qr_code")
                pix_qr_code_base64 = transaction_data.get("qr_code_base64")
                print(f"PIX generated successfully in Mercado Pago. Payment ID: {mp_payment_id}")
            else:
                print(f"Mercado Pago returned response without payment ID: {payment}")
        except Exception as e:
            print(f"Mercado Pago PIX generation failed: {e}. Falling back to simulated PIX.")
            
    # Fallback/Simulação de PIX caso não haja chaves ou tenha falhado
    if not mp_payment_id or not pix_copy_paste or not pix_qr_code_base64:
        mp_payment_id = f"mock_mp_{uuid.uuid4().hex[:8]}"
        pix_copy_paste = f"00020101021226870014br.gov.bcb.pix0125mock-pix-key-amoremcancao520400005303986540529.905802BR5920Amor em Cancao LTDA6009Sao Paulo62070503{order['id'][:8]}"
        # PNG minúsculo de QR Code que funciona como placeholder visual impecável:
        pix_qr_code_base64 = "iVBORw0KGgoAAAANSUhEUgAAAJQAAACUCAYAAAB1ee8RAAAAAXNSR0IArs4c6QAAAAlwSFlzAAALEwAACxMBAJqcGAAAAAd0SU1FB9sJEg0uKz12C3wAAAAdaVRYdENvbW1lbnQAAAAAAENyZWF0ZWQgd2l0aCBHSU1QG5GP0QAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ8vuPBoAAAEGSURBVHja7d0xDhNRAETh924EIgQCgRByEi4BIUTuApeACKEh4BKIEDmBkJNwCUSInG4gEEiG1WplU4X/8WemG0u29v2epN1kG26Pj/cfsT2+PX0AAAAA4H+eZzN2F9sFAAAAAHgZ98fH+4v53fH4+HgRAAAAAPAeAAAAwBqN3cV9sz197AIAAAAAPuD++Hh/cb/YHgEAAAAAnrB32x4BAAAAALyG3e0RAAAAAMAK7G6PAAAAAICV2D/aHgEAAAAAnrBvtj0CAAAAADxhLzM9AgAAAAA8Ye/pEQAAAADgDXuvbXoEAAAAAHjC3tP3CAAAAADwL7tD7RIAAAAAMFMDt0fsAgAAAAC8jv2/7RIAAAAAMPMSw0uMBhDkFNAAAAAElFTkSuQmCC"
        print(f"Using simulated PIX payment data (Mock ID: {mp_payment_id})")

    # Atualiza o pedido no banco com os campos do PIX
    updated_order = db.update_order(order_id, {
        "mp_payment_id": mp_payment_id,
        "pix_copy_paste": pix_copy_paste,
        "pix_qr_code_base64": pix_qr_code_base64
    })
    
    return jsonify({
        "success": True,
        "order": updated_order
    })

@app.route("/api/order/<order_id>/pay-simulate", methods=["POST"])
def pay_simulate(order_id):
    """Simula a aprovação imediata do pagamento Mercado Pago e inicia a geração."""
    order = db.get_order(order_id)
    if not order:
        return jsonify({"error": "Pedido não encontrado"}), 404
        
    if order["payment_status"] == "approved":
        return jsonify({"success": True, "message": "Pagamento já aprovado.", "order": order})
        
    # Atualiza status para pago
    updated_order = db.update_order(order_id, {
        "payment_status": "approved"
    })
    
    # Dispara a geração de música em segundo plano se não tiver sido iniciada ainda
    if updated_order["status"] == "pending":
        threading.Thread(
            target=process_music_generation_background,
            args=(order_id,),
            daemon=True
        ).start()
    
    return jsonify({
        "success": True,
        "message": "Pagamento simulado com sucesso!",
        "order": updated_order
    })

@app.route("/api/order/<order_id>")
def get_order_status(order_id):
    """Retorna os dados atuais do pedido, usado para polling de status pelo frontend."""
    order = db.get_order(order_id)
    if not order:
        return jsonify({"error": "Pedido não encontrado"}), 404
        
    # Se o pagamento ainda estiver pendente e for um ID do Mercado Pago real, consulta status atual
    mp_payment_id = order.get("mp_payment_id")
    if order["payment_status"] == "pending" and mp_payment_id and not mp_payment_id.startswith("mock_"):
        if MERCADO_PAGO_ACCESS_TOKEN:
            try:
                import mercadopago
                sdk = mercadopago.SDK(MERCADO_PAGO_ACCESS_TOKEN)
                payment_response = sdk.payment().get(mp_payment_id)
                payment_info = payment_response["response"]
                
                status = payment_info.get("status")
                if status == "approved":
                    # Atualiza pagamento para aprovado
                    order = db.update_order(order_id, {"payment_status": "approved"})
                    print(f"Payment {mp_payment_id} approved dynamically during status polling!")
                    
                    # Dispara a geração de música em segundo plano se não tiver sido iniciada ainda
                    if order["status"] == "pending":
                        threading.Thread(
                            target=process_music_generation_background,
                            args=(order_id,),
                            daemon=True
                        ).start()
            except Exception as e:
                print(f"Failed to poll payment status from Mercado Pago: {e}")

    return jsonify({
        "success": True,
        "status": order["status"],
        "payment_status": order["payment_status"],
        "audio_url": order["audio_url"],
        "image_url": order["image_url"],
        "lyrics": order["lyrics"],
        "expires_at": order["expires_at"],
        "pix_copy_paste": order.get("pix_copy_paste"),
        "pix_qr_code_base64": order.get("pix_qr_code_base64")
    })

@app.route("/musica/<order_id>")
def delivery(order_id):
    """Exibe a página de entrega com o player de áudio personalizado."""
    order = db.get_order(order_id)
    if not order:
        return "Pedido não encontrado", 404
        
    # Se retornar com o sucesso de pagamento na URL, forçamos aprovação
    if request.args.get("payment") == "success" or request.args.get("status") == "approved":
        if order["payment_status"] != "approved":
            order = db.update_order(order_id, {"payment_status": "approved"})
            
    # Enforça que o pedido deve estar pago para liberar a música inteira
    if order["payment_status"] != "approved":
        return redirect(f"/?order_id={order_id}&step=6")
        
    # Dispara a geração de música em segundo plano como fallback de segurança se não foi iniciada
    if order["status"] == "pending":
        threading.Thread(
            target=process_music_generation_background,
            args=(order_id,),
            daemon=True
        ).start()
        # Atualiza a cópia na memória para refletir a mudança imediata para o template
        order = db.get_order(order_id)
        
    # Verifica se expirou (30 dias)
    expires_at = datetime.fromisoformat(order["expires_at"])
    is_expired = datetime.utcnow() > expires_at
    
    return render_template("delivery.html", order=order, is_expired=is_expired)

@app.route("/api/webhook/mercadopago", methods=["POST"])
def mercadopago_webhook():
    """Recebe notificações de pagamento reais do Mercado Pago."""
    # O Mercado Pago costuma enviar notificações de IPN ou Webhook
    # Esta rota decodifica e aprova o pedido real
    try:
        data = request.json
        if not data:
            # Tenta pegar via args se MP mandou via query params
            data = request.args
            
        topic = data.get("type") or data.get("topic")
        
        if topic == "payment":
            payment_id = data.get("data", {}).get("id") or data.get("id")
            if payment_id:
                # Consulta o pagamento no Mercado Pago
                import mercadopago
                sdk = mercadopago.SDK(MERCADO_AGO_ACCESS_TOKEN)
                payment_info_response = sdk.payment().get(payment_id)
                payment_info = payment_info_response["response"]
                
                status = payment_info.get("status")
                order_id = payment_info.get("external_reference")
                
                if status == "approved" and order_id:
                    order = db.get_order(order_id)
                    if order and order["payment_status"] != "approved":
                        # Marca o pagamento como aprovado e dispara a geração
                        updated_order = db.update_order(order_id, {
                            "payment_status": "approved"
                        })
                        print(f"Payment approved via webhook for order {order_id}!")
                        
                        if updated_order["status"] == "pending":
                            threading.Thread(
                                target=process_music_generation_background,
                                args=(order_id,),
                                daemon=True
                            ).start()
                        
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        print(f"Error in Mercado Pago webhook: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/api/debug", methods=["GET"])
def api_debug():
    """Endpoint de diagnóstico das configurações e do status de geração."""
    load_dotenv() # Força releitura fresca do .env
    
    # 1. Verifica chaves de API
    keys_status = {
        "KIE_AI_API_KEY_configured": "sim" if os.getenv("KIE_AI_API_KEY") else "não",
        "OPENAI_API_KEY_configured": "sim" if os.getenv("OPENAI_API_KEY") else "não",
        "SUPABASE_URL_configured": "sim" if os.getenv("SUPABASE_URL") else "não",
        "SUPABASE_KEY_configured": "sim" if os.getenv("SUPABASE_KEY") else "não",
        "MERCADO_AGO_ACCESS_TOKEN_configured": "sim" if os.getenv("MERCADO_AGO_ACCESS_TOKEN") else "não",
    }
    
    # 2. Verifica o status da última geração
    last_order = None
    try:
        import sqlite3
        conn = sqlite3.connect(db.DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM orders ORDER BY created_at DESC LIMIT 1")
        row = cursor.fetchone()
        if row:
            last_order = dict(row)
        conn.close()
    except Exception as db_err:
        print(f"Error querying last order: {db_err}")
        # Tenta fallback pelo Supabase se habilitado
        try:
            if db.USE_SUPABASE and db.supabase_client:
                res = db.supabase_client.table("orders").select("*").order("created_at", desc=True).limit(1).execute()
                if res.data:
                    last_order = res.data[0]
        except Exception as sb_err:
            print(f"Error querying last order from Supabase: {sb_err}")
            
    generation_status = {
        "found": "não"
    }
    if last_order:
        generation_status = {
            "found": "sim",
            "order_id": last_order.get("id"),
            "occasion": last_order.get("occasion"),
            "receiver_name": last_order.get("receiver_name"),
            "style": last_order.get("style"),
            "status": last_order.get("status"),
            "payment_status": last_order.get("payment_status"),
            "has_lyrics": "sim" if last_order.get("lyrics") else "não",
            "lyrics_preview": last_order.get("lyrics")[:150] + "..." if last_order.get("lyrics") else None,
            "audio_url": last_order.get("audio_url"),
            "image_url": last_order.get("image_url"),
            "suno_task_id": last_order.get("suno_task_id"),
            "created_at": last_order.get("created_at")
        }
        
    return jsonify({
        "keys_status": keys_status,
        "last_generation": generation_status
    }), 200

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"Iniciando o servidor de Músicas Personalizadas na porta {port}...")
    app.run(host="0.0.0.0", port=port, debug=True)
