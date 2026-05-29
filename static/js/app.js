/* =========================================================================
   LÓGICA JAVASCRIPT DO FORMULÁRIO (WIZARD, PREVIEW & POLLING)
   ========================================================================= */

document.addEventListener("DOMContentLoaded", () => {
    // Estado do Wizard
    let currentStep = 1;
    const totalSteps = 6; // 1: Ocasião, 2: Nomes, 3: História, 4: Estilo, 5: Prévia, 6: Pagamento
    
    // Dados selecionados
    let selectedOccasion = "";
    let selectedStyle = "";
    let orderId = "";
    let checkoutUrl = "";
    
    // Player de Prévia Global
    let previewAudio = null;

    // Elementos DOM
    const steps = {
        1: document.getElementById("step-1"),
        2: document.getElementById("step-2"),
        3: document.getElementById("step-3"),
        4: document.getElementById("step-4"),
        5: document.getElementById("step-5"),
        6: document.getElementById("step-6"),
        7: document.getElementById("step-7")
    };
    
    const progressDots = document.querySelectorAll(".progress-dot");
    const progressBarFill = document.getElementById("progress-bar-fill");
    const wizardProgress = document.getElementById("wizard-progress");

    // --- PASSO 1: OCASIÃO ---
    const occasionCards = document.querySelectorAll("#occasion-grid .option-card");
    occasionCards.forEach(card => {
        card.addEventListener("click", () => {
            occasionCards.forEach(c => c.classList.remove("selected"));
            card.classList.add("selected");
            selectedOccasion = card.getAttribute("data-value");
        });
    });

    document.getElementById("btn-next-1").addEventListener("click", () => {
        if (!selectedOccasion) {
            alert("Por favor, selecione uma ocasião especial para continuar.");
            return;
        }
        goToStep(2);
    });

    // --- PASSO 2: NOMES ---
    document.getElementById("btn-prev-2").addEventListener("click", () => goToStep(1));
    document.getElementById("btn-next-2").addEventListener("click", () => {
        const receiver = document.getElementById("receiver_name").value.trim();
        
        if (!receiver) {
            alert("Por favor, preencha o nome do presenteado.");
            return;
        }
        goToStep(3);
    });

    // --- PASSO 3: HISTÓRIA ---
    document.getElementById("btn-prev-3").addEventListener("click", () => goToStep(2));
    document.getElementById("btn-next-3").addEventListener("click", () => {
        const story = document.getElementById("story").value.trim();
        if (!story) {
            alert("Por favor, compartilhe um pouco da história/memórias para podermos compor a música.");
            return;
        }
        goToStep(4);
    });

    // --- PASSO 4: ESTILO ---
    const styleCards = document.querySelectorAll("#style-grid .style-card");
    styleCards.forEach(card => {
        card.addEventListener("click", () => {
            styleCards.forEach(c => c.classList.remove("selected"));
            card.classList.add("selected");
            selectedStyle = card.getAttribute("data-value");
        });
    });

    document.getElementById("btn-prev-4").addEventListener("click", () => goToStep(3));
    document.getElementById("btn-next-4").addEventListener("click", () => {
        if (!selectedStyle) {
            alert("Por favor, selecione um estilo musical para continuar.");
            return;
        }
        
        // Vai para a Prévia (Passo 5) e inicia a geração em segundo plano imediatamente!
        goToStep(5);
        startPreviewGeneration();
    });

    // --- PASSO 5: PRÉVIA (AÇÕES) ---
    document.getElementById("btn-to-payment").addEventListener("click", () => {
        // Pausa áudio se estiver tocando
        if (previewAudio) {
            previewAudio.pause();
        }
        goToStep(6);
    });

    // --- PASSO 6: PAGAMENTO (AÇÕES) ---
    document.getElementById("btn-back-to-preview").addEventListener("click", () => {
        goToStep(5);
    });

    document.getElementById("btn-checkout").addEventListener("click", () => {
        if (checkoutUrl) {
            window.location.href = checkoutUrl;
        } else {
            alert("Erro ao direcionar para o pagamento. Por favor, reinicie o formulário.");
        }
    });

    // --- GERAÇÃO DA PRÉVIA AUTOMÁTICA ---
    async function startPreviewGeneration() {
        const previewLoading = document.getElementById("preview-loading");
        const previewReady = document.getElementById("preview-ready");
        const previewStatusText = document.getElementById("preview-loader-status-text");
        const previewBarFill = document.getElementById("preview-loader-bar-fill");
        
        // Inicializa estado visual
        previewLoading.style.display = "block";
        previewReady.style.display = "none";
        
        const payload = {
            occasion: selectedOccasion,
            receiver_name: document.getElementById("receiver_name").value.trim(),
            story: document.getElementById("story").value.trim(),
            style: selectedStyle
        };
        
        try {
            previewStatusText.innerText = "Preparando algo especial para você...";
            previewBarFill.style.width = "10%";
            
            const response = await fetch("/api/order", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            const result = await response.json();
            
            if (result.success) {
                orderId = result.order.id;
                checkoutUrl = result.checkout_url;
                
                // Começa o polling do status da música em segundo plano
                pollPreviewStatus(orderId);
            } else {
                previewStatusText.innerText = "Erro ao iniciar composição. Clique em voltar.";
                previewStatusText.style.color = "red";
            }
        } catch (err) {
            console.error(err);
            previewStatusText.innerText = "Erro de conexão com o servidor.";
            previewStatusText.style.color = "red";
        }
    }

    // --- POLLING DE STATUS DA PRÉVIA ---
    function pollPreviewStatus(id) {
        const previewBarFill = document.getElementById("preview-loader-bar-fill");
        const previewStatusText = document.getElementById("preview-loader-status-text");
        
        let progress = 10;
        
        const intervalId = setInterval(async () => {
            try {
                const response = await fetch(`/api/order/${id}`);
                const result = await response.json();
                
                if (!result.success) {
                    clearInterval(intervalId);
                    previewStatusText.innerText = "Erro ao compor música.";
                    previewStatusText.style.color = "red";
                    return;
                }
                
                const status = result.status;
                
                if (status === "generating_lyrics") {
                    previewStatusText.innerText = "Escrevendo cada verso com carinho...";
                    progress = Math.min(progress + 3, 45);
                    previewBarFill.style.width = `${progress}%`;
                } 
                else if (status === "generating_audio") {
                    progress = Math.min(progress + 2, 90);
                    previewBarFill.style.width = `${progress}%`;
                    
                    if (progress < 68) {
                        previewStatusText.innerText = "Afinando os instrumentos...";
                    } else {
                        previewStatusText.innerText = "Sua música está tomando forma...";
                    }
                } 
                else if (status === "completed") {
                    clearInterval(intervalId);
                    previewStatusText.innerText = "Últimos retoques na sua obra de arte...";
                    previewBarFill.style.width = "100%";
                    
                    setTimeout(() => {
                        // Exibe a prévia
                        showPreviewReady(result);
                    }, 1000);
                } 
                else if (status === "failed") {
                    clearInterval(intervalId);
                    previewStatusText.innerText = "Falha ao gerar a melodia. Por favor, tente novamente.";
                    previewStatusText.style.color = "red";
                }
            } catch (err) {
                console.error("Error polling preview status:", err);
            }
        }, 3000);
    }

    // --- MONTAGEM DO PLAYER DE PRÉVIA CAPPED A 30s ---
    function showPreviewReady(orderData) {
        document.getElementById("preview-loading").style.display = "none";
        document.getElementById("preview-ready").style.display = "block";
        


        // Cria elemento de áudio
        if (previewAudio) {
            previewAudio.pause();
        }
        
        previewAudio = new Audio(orderData.audio_url);
        
        const playBtn = document.getElementById("preview-play-pause-btn");
        const playIcon = document.getElementById("preview-play-icon");
        const progressFill = document.getElementById("preview-audio-progress-fill");
        const currentTimeEl = document.getElementById("preview-current-time");
        const capNotice = document.getElementById("preview-cap-notice");
        const progressBar = document.getElementById("preview-audio-progress-bar");
        
        capNotice.style.display = "none";
        progressFill.style.width = "0%";
        currentTimeEl.innerText = "00:00";
        playIcon.className = "fa-solid fa-play";

        // Bind Play/Pause
        playBtn.onclick = () => {
            if (previewAudio.paused) {
                // Se já estiver no limite dos 30 segundos e tentar tocar de novo
                if (previewAudio.currentTime >= 30) {
                    previewAudio.currentTime = 0;
                    capNotice.style.display = "none";
                }
                previewAudio.play();
            } else {
                previewAudio.pause();
            }
        };

        previewAudio.onplay = () => {
            playIcon.className = "fa-solid fa-pause";
        };

        previewAudio.onpause = () => {
            playIcon.className = "fa-solid fa-play";
        };

        // Time update capping at 30 seconds
        previewAudio.ontimeupdate = () => {
            const current = previewAudio.currentTime;
            
            // Limitador de 30 segundos (Prévia)
            if (current >= 30) {
                previewAudio.pause();
                previewAudio.currentTime = 30;
                playIcon.className = "fa-solid fa-play";
                capNotice.style.display = "block";
                progressFill.style.width = "100%";
                currentTimeEl.innerText = "00:30";
            } else {
                const percentage = (current / 30) * 100;
                progressFill.style.width = `${percentage}%`;
                currentTimeEl.innerText = `00:${Math.floor(current).toString().padStart(2, '0')}`;
            }
        };

        // Permite seek apenas dentro dos 30 segundos
        progressBar.onclick = (e) => {
            const rect = progressBar.getBoundingClientRect();
            const clickX = e.clientX - rect.left;
            const width = rect.width;
            const targetTime = (clickX / width) * 30;
            
            previewAudio.currentTime = targetTime;
            capNotice.style.display = "none";
        };
    }

    // --- CONTROLE DE NAVEGAÇÃO DO WIZARD ---
    function goToStep(step) {
        // Oculta todos os passos
        Object.values(steps).forEach(s => s.classList.remove("active"));
        
        // Ativa o passo solicitado
        steps[step].classList.add("active");
        currentStep = step;
        
        // Atualiza a barra de progresso (somente se for passos de preenchimento 1 a 6)
        if (step <= totalSteps) {
            wizardProgress.style.display = "flex";
            updateProgressIndicators(step);
        } else {
            wizardProgress.style.display = "none";
        }
    }

    function updateProgressIndicators(activeStep) {
        const fillPercentage = ((activeStep - 1) / (totalSteps - 1)) * 100;
        progressBarFill.style.width = `${fillPercentage}%`;
        
        progressDots.forEach(dot => {
            const stepNum = parseInt(dot.getAttribute("data-step"));
            dot.classList.remove("active", "completed");
            
            if (stepNum === activeStep) {
                dot.classList.add("active");
            } else if (stepNum < activeStep) {
                dot.classList.add("completed");
            }
        });
    }

    // --- VERIFICA SE JÁ VOLTOU DO CHECKOUT SIMULADO (LIBERAÇÃO) ---
    const urlParams = new URLSearchParams(window.location.search);
    const paramOrderId = urlParams.get("order_id");
    const paramStep = urlParams.get("step");
    
    if (paramOrderId && paramStep === "7") {
        orderId = paramOrderId;
        goToStep(7);
        startPollingLiberacao(paramOrderId);
    }

    // --- POLLING APÓS PAGAMENTO (LIBERAÇÃO IMEDIATA) ---
    function startPollingLiberacao(id) {
        const loaderStatus = document.getElementById("loader-status-text");
        
        let attempts = 0;
        const intervalId = setInterval(async () => {
            attempts++;
            try {
                const response = await fetch(`/api/order/${id}`);
                const result = await response.json();
                
                if (result.success && result.payment_status === "approved") {
                    clearInterval(intervalId);
                    loaderStatus.innerText = "Obra de arte liberada! Redirecionando...";
                    
                    setTimeout(() => {
                        window.location.href = `/musica/${id}`;
                    }, 1200);
                } else if (attempts > 5) {
                    // Força liberação se por acaso o webhook atrasar em simulação
                    clearInterval(intervalId);
                    window.location.href = `/musica/${id}`;
                }
            } catch (err) {
                console.error("Error polling payment release:", err);
            }
        }, 1500);
    }
});
