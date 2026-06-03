/* =========================================================================
   LÓGICA JAVASCRIPT DO FORMULÁRIO (WIZARD, PREVIEW, PIX & POLLING)
   ========================================================================= */

document.addEventListener("DOMContentLoaded", () => {
    // Estado do Wizard
    let currentStep = 1;
    const totalSteps = 6; // 1: Ocasião, 2: Nomes, 3: História, 4: Estilo, 5: Prévia, 6: Pagamento
    
    // Dados selecionados
    let selectedOccasion = "";
    let selectedStyle = "";
    let orderId = "";
    
    // Player de Prévia Global
    let previewAudio = null;
    
    // Intervalos e timers de PIX
    let pixIntervalId = null;
    let pixCountdownId = null;

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
    document.getElementById("btn-next-4").addEventListener("click", async () => {
        if (!selectedStyle) {
            alert("Por favor, selecione um estilo musical para continuar.");
            return;
        }
        
        const btn = document.getElementById("btn-next-4");
        const originalHTML = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Preparando...';
        
        const payload = {
            occasion: selectedOccasion,
            receiver_name: document.getElementById("receiver_name").value.trim(),
            story: document.getElementById("story").value.trim(),
            style: selectedStyle
        };
        
        try {
            // Configura os títulos da tela de carregamento para a Prévia (Passo 7)
            document.querySelector("#step-7 .step-title").innerText = "Criando sua prévia personalizada...";
            document.querySelector("#step-7 .loader-subtitle").innerText = "A nossa IA está escrevendo e compondo uma melodia exclusiva para a sua história.";
            document.getElementById("loader-bar-fill").style.width = "10%";
            document.getElementById("loader-status-text").innerText = "Iniciando a composição...";
            
            // Transiciona para a tela de Loader (Passo 7)
            goToStep(7);
            
            const response = await fetch("/api/order", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            const result = await response.json();
            
            if (result.success) {
                orderId = result.order.id;
                // Inicia o polling dinâmico de composição da IA
                pollPreviewStatus(orderId);
            } else {
                alert("Erro ao preparar o pedido. Por favor, tente novamente.");
                goToStep(4);
            }
        } catch (err) {
            console.error(err);
            alert("Erro de conexão com o servidor.");
            goToStep(4);
        } finally {
            btn.disabled = false;
            btn.innerHTML = originalHTML;
        }
    });

    // --- POLLING DE STATUS DA COMPOSIÇÃO DA PRÉVIA ---
    function pollPreviewStatus(id) {
        const previewBarFill = document.getElementById("loader-bar-fill");
        const previewStatusText = document.getElementById("loader-status-text");
        
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
                        // Exibe a prévia gratuita de 30 segundos
                        showPreviewReady(result);
                    }, 1000);
                } 
                else if (status === "failed") {
                    clearInterval(intervalId);
                    previewStatusText.innerText = "Falha ao gerar a melodia. Por favor, tente novamente.";
                    previewStatusText.style.color = "red";
                    setTimeout(() => { goToStep(4); }, 2000);
                }
            } catch (err) {
                console.error("Error polling preview status:", err);
            }
        }, 3000);
    }

    // --- MONTAGEM DO PLAYER DE PRÉVIA CAPPED A 30s (Passo 5) ---
    function showPreviewReady(orderData) {
        goToStep(5); // Vai para a tela de prévia
        
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
        const vinylDisc = document.getElementById("preview-vinyl-disc");
        
        capNotice.style.display = "none";
        progressFill.style.width = "0%";
        currentTimeEl.innerText = "00:00";
        playIcon.className = "fa-solid fa-play";
        
        if (vinylDisc) {
            vinylDisc.style.animationPlayState = "paused";
        }

        // Bind Play/Pause da prévia
        playBtn.onclick = () => {
            if (previewAudio.paused) {
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
            if (vinylDisc) {
                vinylDisc.style.animationPlayState = "running";
            }
        };

        previewAudio.onpause = () => {
            playIcon.className = "fa-solid fa-play";
            if (vinylDisc) {
                vinylDisc.style.animationPlayState = "paused";
            }
        };

        // Time update capping a 30s da prévia
        previewAudio.ontimeupdate = () => {
            const current = previewAudio.currentTime;
            
            if (current >= 30) {
                previewAudio.pause();
                previewAudio.currentTime = 30;
                playIcon.className = "fa-solid fa-play";
                if (vinylDisc) {
                    vinylDisc.style.animationPlayState = "paused";
                }
                capNotice.style.display = "block";
                progressFill.style.width = "100%";
                currentTimeEl.innerText = "00:30";
            } else {
                const percentage = (current / 30) * 100;
                progressFill.style.width = `${percentage}%`;
                currentTimeEl.innerText = `00:${Math.floor(current).toString().padStart(2, '0')}`;
            }
        };

        // Seek apenas dentro dos 30s
        progressBar.onclick = (e) => {
            const rect = progressBar.getBoundingClientRect();
            const clickX = e.clientX - rect.left;
            const width = rect.width;
            const targetTime = (clickX / width) * 30;
            
            previewAudio.currentTime = targetTime;
            capNotice.style.display = "none";
        };
    }

    // Ação "Quero a música completa" (Passo 5 para Passo 6)
    document.getElementById("btn-to-payment").addEventListener("click", async () => {
        if (previewAudio) previewAudio.pause();
        
        const btn = document.getElementById("btn-to-payment");
        const originalHTML = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Gerando PIX...';
        
        try {
            const response = await fetch(`/api/order/${orderId}/payment-init`, {
                method: "POST"
            });
            const result = await response.json();
            
            if (result.success) {
                // Preenche dados do PIX
                document.getElementById("pix-qr-image").src = "data:image/png;base64," + result.order.pix_qr_code_base64;
                document.getElementById("pix-code-text").value = result.order.pix_copy_paste;
                
                // Inicia contagem regressiva e polling do PIX
                startPixTimerAndPolling(result.order);
                
                goToStep(6); // Vai para tela de pagamento
            } else {
                alert("Falha ao inicializar o pagamento. Por favor, tente novamente.");
            }
        } catch (err) {
            console.error("Erro ao gerar PIX:", err);
            alert("Erro de conexão ao gerar o PIX.");
        } finally {
            btn.disabled = false;
            btn.innerHTML = originalHTML;
        }
    });

    // Ação "Refazer Prévia" (Passo 5 para Passo 4)
    document.getElementById("btn-remake-preview").addEventListener("click", () => {
        if (previewAudio) {
            previewAudio.pause();
            previewAudio = null;
        }
        goToStep(4);
    });

    // --- GERENCIAMENTO DE TIMERS E POLLING DO PIX (Passo 6) ---
    function startPixTimerAndPolling(order) {
        if (pixIntervalId) clearInterval(pixIntervalId);
        if (pixCountdownId) clearInterval(pixCountdownId);
        
        let timeLeft = 1800; // 30 minutos
        const timerEl = document.getElementById("pix-timer");
        const btnCopy = document.getElementById("btn-copy-pix");
        
        timerEl.innerText = "30:00";
        timerEl.style.color = "var(--primary-pink)";
        btnCopy.disabled = false;
        
        // 1. Cronômetro regressivo
        pixCountdownId = setInterval(() => {
            timeLeft--;
            if (timeLeft <= 0) {
                clearInterval(pixCountdownId);
                clearInterval(pixIntervalId);
                timerEl.innerText = "EXPIRADO";
                timerEl.style.color = "red";
                btnCopy.disabled = true;
                alert("O código PIX expirou. Por favor, reinicie a criação do pedido.");
                return;
            }
            
            const minutes = Math.floor(timeLeft / 60).toString().padStart(2, "0");
            const seconds = (timeLeft % 60).toString().padStart(2, "0");
            timerEl.innerText = `${minutes}:${seconds}`;
        }, 1000);
        
        // 2. Polling automático de status a cada 10s
        pixIntervalId = setInterval(async () => {
            try {
                const response = await fetch(`/api/order/${order.id}`);
                const result = await response.json();
                
                if (result.success && result.payment_status === "approved") {
                    clearInterval(pixIntervalId);
                    clearInterval(pixCountdownId);
                    
                    // Configura loader para a liberação
                    document.querySelector("#step-7 .step-title").innerText = "Sua Música foi Liberada!";
                    document.querySelector("#step-7 .loader-subtitle").innerText = "Seu presente exclusivo está pronto! Redirecionando em instantes...";
                    document.getElementById("loader-bar-fill").style.width = "100%";
                    document.getElementById("loader-status-text").innerText = "Obra de arte liberada! Redirecionando...";
                    
                    goToStep(7);
                    
                    setTimeout(() => {
                        window.location.href = `/musica/${order.id}`;
                    }, 1500);
                }
            } catch (err) {
                console.error("Erro no polling do PIX:", err);
            }
        }, 10000);
    }

    // --- PASSO 6: AÇÕES DO PAINEL PIX ---
    document.getElementById("btn-back-to-style").addEventListener("click", () => {
        if (pixIntervalId) clearInterval(pixIntervalId);
        if (pixCountdownId) clearInterval(pixCountdownId);
        goToStep(5); // Retorna para a tela de prévia
    });

    // Copiar código PIX
    document.getElementById("btn-copy-pix").addEventListener("click", () => {
        const copyInput = document.getElementById("pix-code-text");
        copyInput.select();
        copyInput.setSelectionRange(0, 99999);
        navigator.clipboard.writeText(copyInput.value);
        
        const copyBtn = document.getElementById("btn-copy-pix");
        const originalText = copyBtn.innerHTML;
        copyBtn.innerHTML = '<i class="fa-solid fa-check"></i> Copiado!';
        copyBtn.style.background = "#4CAF50";
        
        setTimeout(() => {
            copyBtn.innerHTML = originalText;
            copyBtn.style.background = "";
        }, 2000);
    });

    // Simulação de aprovação em Dev
    document.getElementById("btn-pay-simulate-natively").addEventListener("click", async () => {
        const btn = document.getElementById("btn-pay-simulate-natively");
        btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Aprovando PIX...';
        
        try {
            const response = await fetch(`/api/order/${orderId}/pay-simulate`, {
                method: "POST"
            });
            const result = await response.json();
            
            if (result.success) {
                if (pixIntervalId) clearInterval(pixIntervalId);
                if (pixCountdownId) clearInterval(pixCountdownId);
                
                document.querySelector("#step-7 .step-title").innerText = "Sua Música foi Liberada!";
                document.querySelector("#step-7 .loader-subtitle").innerText = "Seu presente exclusivo está pronto! Redirecionando em instantes...";
                document.getElementById("loader-bar-fill").style.width = "100%";
                document.getElementById("loader-status-text").innerText = "Obra de arte liberada! Redirecionando...";
                
                goToStep(7);
                
                setTimeout(() => {
                    window.location.href = `/musica/${orderId}`;
                }, 1500);
            } else {
                alert("Falha na simulação do PIX.");
                btn.disabled = false;
                btn.innerHTML = "🚀 Simular Aprovação (Modo Desenvolvedor)";
            }
        } catch (err) {
            console.error("Erro na simulação do PIX:", err);
            alert("Erro de rede.");
            btn.disabled = false;
            btn.innerHTML = "🚀 Simular Aprovação (Modo Desenvolvedor)";
        }
    });

    // --- NAVEGAÇÃO E WIZARD GENERALIZADO ---
    function goToStep(step) {
        Object.values(steps).forEach(s => s.classList.remove("active"));
        steps[step].classList.add("active");
        currentStep = step;
        
        const mainCard = document.getElementById("main-glass-card");
        if (mainCard) {
            if (step === 7) {
                mainCard.classList.add("card-pink");
            } else {
                mainCard.classList.remove("card-pink");
            }
        }
        
        if (step <= 6) {
            wizardProgress.style.display = "flex";
            updateProgressIndicators(step);
        } else {
            wizardProgress.style.display = "none";
        }
    }

    function updateProgressIndicators(activeStep) {
        const stepMapping = { 1: 0, 2: 20, 3: 40, 4: 60, 5: 80, 6: 100 };
        const fillPercentage = stepMapping[activeStep] !== undefined ? stepMapping[activeStep] : 0;
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
});
