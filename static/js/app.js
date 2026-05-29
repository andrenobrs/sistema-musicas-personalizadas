/* =========================================================================
   LÓGICA JAVASCRIPT DO FORMULÁRIO (WIZARD & STATUS POLLING)
   ========================================================================= */

document.addEventListener("DOMContentLoaded", () => {
    // Estado do Wizard
    let currentStep = 1;
    const totalSteps = 5;
    
    // Dados selecionados
    let selectedOccasion = "";
    let selectedStyle = "";
    let orderId = "";

    // Elementos DOM
    const steps = {
        1: document.getElementById("step-1"),
        2: document.getElementById("step-2"),
        3: document.getElementById("step-3"),
        4: document.getElementById("step-4"),
        5: document.getElementById("step-5"),
        6: document.getElementById("step-6")
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
        const giver = document.getElementById("giver_name").value.trim();
        const receiver = document.getElementById("receiver_name").value.trim();
        
        if (!giver || !receiver) {
            alert("Por favor, preencha os nomes de quem dá e de quem recebe.");
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
        goToStep(5);
    });

    // --- PASSO 5: CHECKOUT / PEDIDO ---
    document.getElementById("btn-prev-5").addEventListener("click", () => goToStep(4));
    document.getElementById("btn-checkout").addEventListener("click", async () => {
        const checkoutBtn = document.getElementById("btn-checkout");
        checkoutBtn.disabled = true;
        checkoutBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Criando seu pedido...';
        
        const payload = {
            occasion: selectedOccasion,
            giver_name: document.getElementById("giver_name").value.trim(),
            receiver_name: document.getElementById("receiver_name").value.trim(),
            story: document.getElementById("story").value.trim(),
            style: selectedStyle
        };
        
        try {
            const response = await fetch("/api/order", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });
            const result = await response.json();
            
            if (result.success) {
                // Redireciona para o checkout (simulado ou do Mercado Pago)
                window.location.href = result.checkout_url;
            } else {
                alert("Erro ao criar pedido: " + result.error);
                checkoutBtn.disabled = false;
                checkoutBtn.innerHTML = '<i class="fa-solid fa-credit-card"></i> Ir para Pagamento Seguro';
            }
        } catch (err) {
            console.error(err);
            alert("Erro na conexão com o servidor.");
            checkoutBtn.disabled = false;
            checkoutBtn.innerHTML = '<i class="fa-solid fa-credit-card"></i> Ir para Pagamento Seguro';
        }
    });

    // --- CONTROLE DE NAVEGAÇÃO DO WIZARD ---
    function goToStep(step) {
        // Oculta todos os passos
        Object.values(steps).forEach(s => s.classList.remove("active"));
        
        // Ativa o passo solicitado
        steps[step].classList.add("active");
        currentStep = step;
        
        // Atualiza a barra de progresso (somente se for passos 1 a 5)
        if (step <= totalSteps) {
            wizardProgress.style.display = "flex";
            updateProgressIndicators(step);
        } else {
            wizardProgress.style.display = "none";
        }
    }

    function updateProgressIndicators(activeStep) {
        // Atualiza a linha preenchida
        const fillPercentage = ((activeStep - 1) / (totalSteps - 1)) * 100;
        progressBarFill.style.width = `${fillPercentage}%`;
        
        // Atualiza os círculos numéricos
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

    // --- VERIFICA SE JÁ VOLTOU DO CHECKOUT SIMULADO ---
    const urlParams = new URLSearchParams(window.location.search);
    const paramOrderId = urlParams.get("order_id");
    const paramStep = urlParams.get("step");
    
    if (paramOrderId && paramStep === "6") {
        orderId = paramOrderId;
        goToStep(6);
        startPollingStatus(paramOrderId);
    }

    // --- POLLING DE STATUS (PASSO 6: TELA DE AGUARDO) ---
    function startPollingStatus(id) {
        const loaderBarFill = document.getElementById("loader-bar-fill");
        const statusText = document.getElementById("loader-status-text");
        const vinylDisc = document.getElementById("vinyl-disc");
        
        // Força animação ativa do vinil
        vinylDisc.style.animationPlayState = "running";
        
        let progress = 5;
        loaderBarFill.style.width = `${progress}%`;
        
        const intervalId = setInterval(async () => {
            try {
                const response = await fetch(`/api/order/${id}`);
                const result = await response.json();
                
                if (!result.success) {
                    clearInterval(intervalId);
                    statusText.innerText = "Erro ao buscar status do pedido.";
                    statusText.style.color = "red";
                    vinylDisc.style.animationPlayState = "paused";
                    return;
                }
                
                const status = result.status;
                const paymentStatus = result.payment_status;
                
                if (paymentStatus === "pending") {
                    statusText.innerText = "Preparando algo especial para você...";
                    progress = Math.min(progress + 2, 18);
                    loaderBarFill.style.width = `${progress}%`;
                } 
                else if (status === "generating_lyrics") {
                    statusText.innerText = "Escrevendo cada verso com carinho...";
                    progress = Math.min(progress + 3, 45);
                    loaderBarFill.style.width = `${progress}%`;
                } 
                else if (status === "generating_audio") {
                    progress = Math.min(progress + 2, 90);
                    loaderBarFill.style.width = `${progress}%`;
                    
                    if (progress < 68) {
                        statusText.innerText = "Afinando os instrumentos...";
                    } else {
                        statusText.innerText = "Sua música está tomando forma...";
                    }
                } 
                else if (status === "completed") {
                    clearInterval(intervalId);
                    statusText.innerText = "Últimos retoques na sua obra de arte...";
                    loaderBarFill.style.width = "100%";
                    
                    setTimeout(() => {
                        window.location.href = `/musica/${id}`;
                    }, 1200);
                } 
                else if (status === "failed") {
                    clearInterval(intervalId);
                    statusText.innerText = "Erro durante a composição. Contate o suporte.";
                    statusText.style.color = "red";
                    vinylDisc.style.animationPlayState = "paused";
                }
            } catch (err) {
                console.error("Error polling order status:", err);
            }
        }, 3000); // Polling a cada 3 segundos para fluidez visual e resposta rápida
    }
});
