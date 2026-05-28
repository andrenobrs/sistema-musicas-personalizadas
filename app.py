import os
import threading
import time
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for
from dotenv import load_dotenv

# Carrega chaves do .env
load_dotenv()

import database as db
import openai_service as ai
import suno_service as suno

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "musicas_personalizadas_secret_key_129847")

MERCADO_AGO_ACCESS_TOKEN = os.getenv("MERCADO_AGO_ACCESS_TOKEN")

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
    """Cria um pedido pendente e gera a sessão de pagamento."""
    data = request.json
    if not data:
        return jsonify({"error": "Dados ausentes"}), 400
        
    occasion = data.get("occasion")
    giver_name = data.get("giver_name")
    receiver_name = data.get("receiver_name")
    story = data.get("story", "")
    style = data.get("style")
    
    if not all([occasion, giver_name, receiver_name, style]):
        return jsonify({"error": "Preencha todos os campos obrigatórios."}), 400
        
    # Salva o pedido inicial no banco de dados
    order = db.create_order(occasion, giver_name, receiver_name, story, style)
    
    checkout_url = f"/checkout-mp/{order['id']}" # Link interno para simulação/checkout real
    
    # Se houver credenciais reais do Mercado Pago configuradas, podemos gerar uma preferência real
    if MERCADO_AGO_ACCESS_TOKEN:
        try:
            import mercadopago
            sdk = mercadopago.SDK(MERCADO_AGO_ACCESS_TOKEN)
            preference_data = {
                "items": [
                    {
                        "title": f"Música Personalizada - {occasion} ({receiver_name})",
                        "quantity": 1,
                        "unit_price": 97.00,
                        "currency_id": "BRL"
                    }
                ],
                "back_urls": {
                    "success": request.host_url + f"musica/{order['id']}?payment=success",
                    "failure": request.host_url + f"?payment=failed",
                    "pending": request.host_url + f"?payment=pending"
                },
                "auto_return": "approved",
                "external_reference": order["id"],
                "notification_url": request.host_url + "api/webhook/mercadopago"
            }
            preference_response = sdk.preference().create(preference_data)
            preference = preference_response["response"]
            
            # Atualiza o checkout_url com a preferência oficial de sandbox ou produção do Mercado Pago
            # Dependendo se é sandbox ou produção (preference["sandbox_init_point"] ou init_point)
            checkout_url = preference.get("init_point") or preference.get("sandbox_init_point") or checkout_url
        except Exception as e:
            print(f"Mercado Pago configuration failed: {e}. Using simulated payment gateway.")
            
    return jsonify({
        "success": True,
        "order": order,
        "checkout_url": checkout_url
    })

@app.route("/checkout-mp/<order_id>")
def checkout_mp_simulated(order_id):
    """Página temporária para apresentar o pagamento simulado ou redirecionar."""
    order = db.get_order(order_id)
    if not order:
        return "Pedido não encontrado", 404
        
    return render_template("checkout.html", order=order)

@app.route("/api/order/<order_id>/pay-simulate", methods=["POST"])
def pay_simulate(order_id):
    """Simula a aprovação imediata do pagamento Mercado Pago."""
    order = db.get_order(order_id)
    if not order:
        return jsonify({"error": "Pedido não encontrado"}), 404
        
    if order["payment_status"] == "approved":
        return jsonify({"success": True, "message": "Pagamento já aprovado.", "order": order})
        
    # Atualiza status para pago e gerando
    updated_order = db.update_order(order_id, {
        "payment_status": "approved",
        "status": "generating_lyrics"
    })
    
    # Inicia a geração da música em segundo plano
    threading.Thread(
        target=process_music_generation_background,
        args=(order_id,),
        daemon=True
    ).start()
    
    return jsonify({
        "success": True,
        "message": "Pagamento simulado com sucesso! Iniciando composição da música.",
        "order": updated_order
    })

@app.route("/api/order/<order_id>")
def get_order_status(order_id):
    """Retorna os dados atuais do pedido, usado para polling de status pelo frontend."""
    order = db.get_order(order_id)
    if not order:
        return jsonify({"error": "Pedido não encontrado"}), 404
        
    return jsonify({
        "success": True,
        "status": order["status"],
        "payment_status": order["payment_status"],
        "audio_url": order["audio_url"],
        "image_url": order["image_url"],
        "expires_at": order["expires_at"]
    })

@app.route("/musica/<order_id>")
def delivery(order_id):
    """Exibe a página de entrega com o player de áudio personalizado."""
    order = db.get_order(order_id)
    if not order:
        return "Pedido não encontrado", 404
        
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
                        # Aprova o pagamento e inicia geração
                        db.update_order(order_id, {
                            "payment_status": "approved",
                            "status": "generating_lyrics"
                        })
                        threading.Thread(
                            target=process_music_generation_background,
                            args=(order_id,),
                            daemon=True
                        ).start()
                        print(f"Payment approved via webhook for order {order_id}!")
                        
        return jsonify({"status": "ok"}), 200
    except Exception as e:
        print(f"Error in Mercado Pago webhook: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    print("Iniciando o servidor de Músicas Personalizadas na porta 5000...")
    app.run(host="0.0.0.0", port=5000, debug=True)
