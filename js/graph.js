// Variável global para o gráfico
let burndownChart = null;

// Cores do tema via variáveis CSS
function readCssVar(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

function getThemeColors() {
    return {
        primary: readCssVar('--primary-color') || '#3b82f6',
        secondary: readCssVar('--secondary-color') || '#10b981',
        accent: readCssVar('--accent-color') || '#8b5cf6',
        background: readCssVar('--background-color') || '#ffffff',
        surface: readCssVar('--surface-color') || '#f8fafc',
        text: readCssVar('--text-color') || '#1e293b',
        textSecondary: readCssVar('--text-secondary') || '#64748b',
        border: readCssVar('--border-color') || '#e2e8f0'
    };
}

let theme = getThemeColors();

// Utilitário para converter hex em rgb
function hexToRgb(hex) {
    const sanitized = hex.replace('#', '');
    const bigint = parseInt(sanitized.length === 3 ? sanitized.split('').map(c => c + c).join('') : sanitized, 16);
    const r = (bigint >> 16) & 255;
    const g = (bigint >> 8) & 255;
    const b = bigint & 255;
    return { r, g, b };
}

// Utilitário para converter hex em rgba
function hexToRgba(hex, alpha) {
    const sanitized = hex.replace('#', '');
    const full = sanitized.length === 3 ? sanitized.split('').map(c => c + c).join('') : sanitized;
    const bigint = parseInt(full, 16);
    const r = (bigint >> 16) & 255;
    const g = (bigint >> 8) & 255;
    const b = bigint & 255;
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

// Usar credenciais do arquivo credentials.js
const DEMO_KEYS = window.CREDENTIALS || {};

// Função para obter o grupo atual baseado nas credenciais
function getCurrentGroup() {
    const key = localStorage.getItem('trello_key') || '';
    const token = localStorage.getItem('trello_token') || '';
    const boardId = localStorage.getItem('trello_board_id') || '';
    
    for (const [group, credentials] of Object.entries(DEMO_KEYS)) {
        if (key === credentials.key && token === credentials.token && boardId === credentials.board) {
            return group;
        }
    }
    return 'errorsquad'; // padrão
}

// Função para obter o número da sprint da URL
function getSprintNumberFromUrl() {
    const urlParams = new URLSearchParams(window.location.search);
    const sprint = urlParams.get('sprint');
    if (sprint) {
        // Se for formato "sprint-1", "sprint-2", etc.
        if (sprint.startsWith('sprint-')) {
            return parseInt(sprint.replace('sprint-', ''));
        }
        // Se for apenas número
        return parseInt(sprint);
    }
    return 1;
}

// Função para carregar dados simulados baseado no grupo e sprint
async function loadSimulatedData(group, sprintNumber) {
    try {
        const dataFile = `${group}-sprint${sprintNumber}.json`;
        
        console.log(`Carregando dados simulados para grupo: ${group}, sprint: ${sprintNumber}`);
        console.log(`Arquivo de dados: ${dataFile}`);
        
        const response = await fetch(`../data/${dataFile}`);
        if (!response.ok) {
            if (sprintNumber > 1) {
                throw new Error(`📊 Não há dados disponíveis para a Sprint ${sprintNumber} do grupo ${group}.`);
            }
            throw new Error(`Erro ao carregar dados simulados: ${response.statusText}`);
        }
        const data = await response.json();
        
        return data;
    } catch (error) {
        console.error('Erro ao carregar dados simulados:', error);
        throw error;
    }
}

// Função para verificar se as credenciais são válidas (demo)
function isValidCredentials(key, token, boardId) {
    return Object.values(DEMO_KEYS).some(creds => 
        key === creds.key && token === creds.token && boardId === creds.board
    );
}

// Funções para controle do modal
function openTrelloModal() {
    document.getElementById('trello-modal').style.display = 'block';
}

function closeTrelloModal() {
    document.getElementById('trello-modal').style.display = 'none';
}

// Salvar credenciais no localStorage
function saveCredentials(key, token, boardId) {
    try {
        localStorage.setItem('trello_key', key);
        localStorage.setItem('trello_token', token);
        localStorage.setItem('trello_board_id', boardId);
    } catch (e) {
        console.error('Erro ao salvar configurações:', e);
    }
}

// Carregar credenciais salvas
function loadCredentials() {
    try {
        const key = localStorage.getItem('trello_key');
        const token = localStorage.getItem('trello_token');
        const boardId = localStorage.getItem('trello_board_id');
        if (key) document.getElementById('trello-key').value = key;
        if (token) document.getElementById('trello-token').value = token;
        if (boardId) document.getElementById('trello-board').value = boardId;
    } catch (e) {
        console.error('Erro ao carregar configurações:', e);
    }
}

// Função para limpar credenciais e desconectar
function disconnectFromTrello() {
    try {
        // Limpar as credenciais do localStorage
        localStorage.removeItem('trello_key');
        localStorage.removeItem('trello_token');
        localStorage.removeItem('trello_board_id');
        
        // Limpar os campos do formulário
        document.getElementById('trello-key').value = '';
        document.getElementById('trello-token').value = '';
        document.getElementById('trello-board').value = '';
        
        // Atualizar a mensagem para o usuário
        document.getElementById('loading-message').textContent = 'Preencha as credenciais para visualizar o gráfico.';
        document.getElementById('loading-message').style.display = 'block';
        
        // Se existe um gráfico, destruí-lo
        if (burndownChart) {
            burndownChart.destroy();
            burndownChart = null;
        }
        
        // Limpar as métricas
        document.getElementById('cards-text').textContent = '0/0 (0%)';
        document.getElementById('cards-progress').style.width = '0%';
        document.getElementById('points-text').textContent = '0/0 (0%)';
        document.getElementById('points-progress').style.width = '0%';
        document.getElementById('days-text').textContent = '0/0 (0%)';
        document.getElementById('days-progress').style.width = '0%';
        
        // Exibir mensagem de sucesso
        const errorDiv = document.getElementById('trello-error');
        errorDiv.textContent = 'Desconectado com sucesso!';
        errorDiv.style.color = 'green';
        errorDiv.style.display = 'block';
        
        // Disparar evento storage para atualizar outras páginas abertas
        window.dispatchEvent(new StorageEvent('storage', {
            key: 'trello_board_id',
            newValue: null
        }));
    } catch (e) {
        console.error('Erro ao desconectar:', e);
    }
}

// Função para calcular a linha ideal
function calculateIdealLine(data) {
    const totalDays = data.labels.length;
    const totalPoints = data.totalPontos;
    const pointsPerDay = totalPoints / (totalDays - 1);
    
    return data.labels.map((_, index) => {
        return Math.max(0, totalPoints - (index * pointsPerDay));
    });
}

// Função para atualizar as métricas
function updateMetrics(data) {
    // Calcular métricas a partir dos dados
    const totalCards = data.totalCards;
    const totalPoints = data.totalPontos;
    const completedCards = data.cardsCompletados[data.cardsCompletados.length - 1];
    const completedPoints = data.pontosCompletados[data.pontosCompletados.length - 1];
    
    const cardsPercentage = Math.round((completedCards / totalCards) * 100);
    const pointsPercentage = Math.round((completedPoints / totalPoints) * 100);
    
    // Cards Progress
    const cardsProgress = document.getElementById('cards-progress');
    cardsProgress.style.width = `${cardsPercentage}%`;
    document.getElementById('cards-text').textContent = 
        `${completedCards}/${totalCards} (${cardsPercentage}%)`;

    // Points Progress
    const pointsProgress = document.getElementById('points-progress');
    pointsProgress.style.width = `${pointsPercentage}%`;
    document.getElementById('points-text').textContent = 
        `${completedPoints}/${totalPoints} (${pointsPercentage}%)`;

    // Days Progress - calcular baseado nos dados reais
    const totalDays = data.totalDias;
    const workedDays = data.diasTrabalhados || 0; // Usar diasTrabalhados do JSON
    const daysPercentage = Math.round((workedDays / totalDays) * 100);
    
    const daysProgress = document.getElementById('days-progress');
    const daysText = document.getElementById('days-text');
    
    if (daysProgress && daysText) {
        daysProgress.style.width = `${daysPercentage}%`;
        daysText.textContent = `${workedDays}/${totalDays} (${daysPercentage}%)`;
    } else {
        console.error('Elementos days-progress ou days-text não encontrados');
    }
    
    // Mostrar informações da equipe se disponível
    if (data.membrosEquipe) {
        updateTeamInfo(data);
    }
}

// Função para atualizar informações da equipe
function updateTeamInfo(data) {
    const teamInfoContainer = document.getElementById('team-info');
    if (!teamInfoContainer) return;
    
    const membrosEquipe = data.membrosEquipe;
    const totalPontos = data.totalPontos;
    const totalDias = data.totalDias;
    
    // Calcular pontos por membro por dia
    const pontosPorMembroPorDia = (totalPontos / totalDias) / membrosEquipe;
    
    let html = '<h4>Informações da Equipe:</h4>';
    html += `<div class="team-stats">`;
    html += `<div class="team-stat-item">`;
    html += `<span class="team-stat-label">👥 Membros da Equipe:</span>`;
    html += `<span class="team-stat-value">${membrosEquipe}</span>`;
    html += `</div>`;
    html += `<div class="team-stat-item">`;
    html += `<span class="team-stat-label">📊 Pontos por Membro/Dia:</span>`;
    html += `<span class="team-stat-value">${pontosPorMembroPorDia.toFixed(2)} pts</span>`;
    html += `</div>`;
    html += `<div class="team-stat-item">`;
    html += `<span class="team-stat-label">📅 Duração da Sprint:</span>`;
    html += `<span class="team-stat-value">${totalDias} dias</span>`;
    html += `</div>`;
    html += `</div>`;
    
    teamInfoContainer.innerHTML = html;
}

// Função para carregar dados simulados
async function loadBurndownData() {
    const key = document.getElementById('trello-key').value.trim();
    const token = document.getElementById('trello-token').value.trim();
    const boardId = document.getElementById('trello-board').value.trim();
    const errorDiv = document.getElementById('trello-error');
    errorDiv.style.display = 'none';

    if (!key || !token || !boardId) {
        document.getElementById('loading-message').textContent = 'Preencha as credenciais para visualizar o gráfico.';
        document.getElementById('loading-message').style.display = 'block';
        return;
    }

    // Verifica se as credenciais são válidas
    if (!isValidCredentials(key, token, boardId)) {
        errorDiv.textContent = 'Credenciais inválidas. Use as credenciais de um dos grupos disponíveis.';
        errorDiv.style.display = 'block';
        document.getElementById('loading-message').textContent = 'Erro: Credenciais inválidas.';
        return;
    }

    // Salva as credenciais no localStorage
    localStorage.setItem('trello_key', key);
    localStorage.setItem('trello_token', token);
    localStorage.setItem('trello_board_id', boardId);

    document.getElementById('loading-message').textContent = 'Carregando dados...';
    document.getElementById('loading-message').style.display = 'block';

    try {
        // Obtém o grupo e sprint
        const group = getCurrentGroup();
        const sprintNumber = getSprintNumberFromUrl();
        console.log('Carregando grupo:', group, 'sprint:', sprintNumber);
        
        const data = await loadSimulatedData(group, sprintNumber);
        await renderBurndownWithData(data);
        document.getElementById('loading-message').style.display = 'none';
        updateSprintTitle(sprintNumber);
    } catch (err) {
        console.error('Erro ao carregar dados:', err);
        
        // Limpar o gráfico existente
        if (burndownChart) {
            burndownChart.destroy();
            burndownChart = null;
        }
        
        // Limpar o canvas
        const ctx = document.getElementById('burndownChart').getContext('2d');
        ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
        
        // Mostrar mensagem de erro
        errorDiv.textContent = err.message;
        errorDiv.style.display = 'block';
        document.getElementById('loading-message').textContent = 'Erro ao carregar dados.';
        
        // Limpar métricas
        clearMetrics();
    }
}

// Função para limpar as métricas
function clearMetrics() {
    // Limpar métricas de cards
    const cardsProgress = document.getElementById('cards-progress');
    const cardsText = document.getElementById('cards-text');
    if (cardsProgress && cardsText) {
        cardsProgress.style.width = '0%';
        cardsText.textContent = '0/0 (0%)';
    }
    
    // Limpar métricas de pontos
    const pointsProgress = document.getElementById('points-progress');
    const pointsText = document.getElementById('points-text');
    if (pointsProgress && pointsText) {
        pointsProgress.style.width = '0%';
        pointsText.textContent = '0/0 (0%)';
    }
    
    // Limpar métricas de dias
    const daysProgress = document.getElementById('days-progress');
    const daysText = document.getElementById('days-text');
    if (daysProgress && daysText) {
        daysProgress.style.width = '0%';
        daysText.textContent = '0/0 (0%)';
    }
}

// Função para atualizar o título da sprint dinamicamente
function updateSprintTitle(sprintId) {
    const titleEl = document.getElementById('sprint-title');
    if (!titleEl) return;
    if (sprintId === 'sprint-3') {
        titleEl.textContent = 'Métricas da Sprint 3';
    } else if (sprintId === 'sprint-2') {
        titleEl.textContent = 'Métricas da Sprint 2';
    } else {
        titleEl.textContent = 'Métricas da Sprint 1';
    }
}

// Função para renderizar o gráfico e métricas
async function renderBurndownWithData(data) {
    const ctx = document.getElementById('burndownChart').getContext('2d');
    if (burndownChart) burndownChart.destroy();
    
    const labels = data.labels;
    const remainingPoints = data.pontosCompletados.map((completed, index) => data.totalPontos - completed);
    const completedPoints = data.pontosCompletados;
    const idealLine = calculateIdealLine(data);
    
    // Verificar se há progresso real (se todos os pontos completados são 0)
    const hasProgress = data.pontosCompletados.some(points => points > 0);

    // Configuração do gradiente para o gráfico
    const gradientRemaining = ctx.createLinearGradient(0, 0, 0, 400);
    const primaryRgb = hexToRgb(theme.primary);
    gradientRemaining.addColorStop(0, `rgba(${primaryRgb.r}, ${primaryRgb.g}, ${primaryRgb.b}, 0.2)`);
    gradientRemaining.addColorStop(1, `rgba(${primaryRgb.r}, ${primaryRgb.g}, ${primaryRgb.b}, 0)`);

    const gradientCompleted = ctx.createLinearGradient(0, 0, 0, 400);
    const secondaryRgb = hexToRgb(theme.secondary);
    gradientCompleted.addColorStop(0, `rgba(${secondaryRgb.r}, ${secondaryRgb.g}, ${secondaryRgb.b}, 0.2)`);
    gradientCompleted.addColorStop(1, `rgba(${secondaryRgb.r}, ${secondaryRgb.g}, ${secondaryRgb.b}, 0)`);

    burndownChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: hasProgress ? [
                {
                    label: 'Pontos Restantes',
                    data: remainingPoints,
                    borderColor: theme.primary,
                    backgroundColor: gradientRemaining,
                    tension: 0.4,
                    fill: true,
                    borderWidth: 3,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    pointBackgroundColor: '#FFFFFF',
                    pointBorderColor: theme.primary,
                    pointBorderWidth: 2,
                    order: 1
                },
                {
                    label: 'Burndown Ideal',
                    data: idealLine,
                    borderColor: getComputedStyle(document.documentElement).getPropertyValue('--brand-5').trim() || theme.accent,
                    backgroundColor: hexToRgba(getComputedStyle(document.documentElement).getPropertyValue('--brand-5').trim() || '#6366f1', 0.1),
                    borderDash: [5, 5],
                    fill: false,
                    borderWidth: 2,
                    pointRadius: 0,
                    pointHoverRadius: 0,
                    order: 3
                },
                {
                    label: 'Pontos Completados',
                    data: completedPoints,
                    type: 'line',
                    borderColor: getComputedStyle(document.documentElement).getPropertyValue('--brand-4').trim() || theme.secondary,
                    backgroundColor: gradientCompleted,
                    tension: 0.4,
                    fill: true,
                    borderWidth: 3,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    pointBackgroundColor: '#FFFFFF',
                    pointBorderColor: getComputedStyle(document.documentElement).getPropertyValue('--brand-4').trim() || theme.secondary,
                    pointBorderWidth: 2,
                    order: 2
                }
            ] : [
                {
                    label: 'Burndown Ideal',
                    data: idealLine,
                    borderColor: getComputedStyle(document.documentElement).getPropertyValue('--brand-5').trim() || theme.accent,
                    backgroundColor: hexToRgba(getComputedStyle(document.documentElement).getPropertyValue('--brand-5').trim() || '#6366f1', 0.1),
                    borderDash: [5, 5],
                    fill: false,
                    borderWidth: 3,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                    pointBackgroundColor: '#FFFFFF',
                    pointBorderColor: getComputedStyle(document.documentElement).getPropertyValue('--brand-5').trim() || theme.accent,
                    pointBorderWidth: 2,
                    order: 1
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            layout: {
                padding: {
                    top: 20,
                    right: 20,
                    bottom: 20,
                    left: 20
                }
            },
            plugins: {
                legend: {
                    position: 'top',
                    align: 'center',
                    labels: {
                        usePointStyle: true,
                        padding: 20,
                        color: theme.text,
                        font: {
                            size: 12,
                            weight: '500',
                            family: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
                        },
                        boxWidth: 8,
                        generateLabels: function(chart) {
                            const original = Chart.defaults.plugins.legend.labels.generateLabels;
                            const labels = original.call(this, chart);
                            labels.forEach(label => {
                                label.fillStyle = label.strokeStyle;
                                label.lineWidth = 0;
                            });
                            return labels;
                        }
                    }
                },
                tooltip: {
                    enabled: true,
                    mode: 'index',
                    intersect: false,
                    backgroundColor: '#FFFFFF',
                    titleColor: theme.text,
                    bodyColor: theme.textSecondary,
                    borderColor: theme.border,
                    borderWidth: 1,
                    padding: 12,
                    boxPadding: 6,
                    usePointStyle: true,
                    titleFont: {
                        size: 14,
                        weight: '600',
                        family: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
                    },
                    bodyFont: {
                        size: 12,
                        family: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
                    },
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) {
                                label += ': ';
                            }
                            if (context.parsed.y !== null) {
                                label += context.parsed.y.toFixed(1) + ' pontos';
                            }
                            return label;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        display: true,
                        drawBorder: false,
                        color: 'rgba(0, 0, 0, 0.03)',
                        lineWidth: 1
                    },
                    border: {
                        display: false
                    },
                    ticks: {
                        display: true,
                        color: theme.textSecondary,
                        font: {
                            size: 11,
                            family: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
                        },
                        padding: 8,
                        maxTicksLimit: 8,
                        callback: function(value) {
                            return value + ' pts';
                        }
                    }
                },
                x: {
                    grid: {
                        display: false,
                        drawBorder: false
                    },
                    border: {
                        display: false
                    },
                    ticks: {
                        display: true,
                        color: theme.textSecondary,
                        font: {
                            size: 11,
                            family: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif"
                        },
                        padding: 8,
                        maxRotation: 45,
                        minRotation: 45,
                        callback: function(value, index) {
                            const label = this.getLabelForValue(index);
                            return label; // Retorna o label original (Dia 1, Dia 2, etc.)
                        }
                    }
                }
            },
            animation: {
                duration: 1000,
                easing: 'easeInOutQuart'
            }
        }
    });

    // Atualiza as métricas
    updateMetrics(data);
}

// Função para atualizar métricas com animação
function updateMetricsWithAnimation(metrics) {
    const elements = {
        cardsCompleted: {
            progress: document.getElementById('cards-progress'),
            text: document.getElementById('cards-text')
        },
        pointsCompleted: {
            progress: document.getElementById('points-progress'),
            text: document.getElementById('points-text')
        },
        daysWorked: {
            progress: document.getElementById('days-progress'),
            text: document.getElementById('days-text')
        }
    };

    // Anima cada métrica
    Object.entries(metrics).forEach(([key, value]) => {
        const element = elements[key];
        if (!element) return;

        // Anima a barra de progresso
        element.progress.style.transition = 'width 1s ease-in-out';
        element.progress.style.width = `${value.percentage}%`;

        // Anima o texto
        let currentValue = 0;
        const targetValue = value.completed;
        const duration = 1000;
        const steps = 60;
        const increment = targetValue / steps;
        const stepTime = duration / steps;

        const updateText = () => {
            currentValue = Math.min(currentValue + increment, targetValue);
            element.text.textContent = `${Math.round(currentValue)}/${value.total} (${value.percentage}%)`;
            
            if (currentValue < targetValue) {
                setTimeout(updateText, stepTime);
            }
        };

        updateText();
    });
}

// Inicialização
document.addEventListener('DOMContentLoaded', async () => {
    try {
        // Inicializa o modal
        const openModalBtn = document.getElementById('open-trello-modal-btn');
        const closeModalBtn = document.querySelector('.close-modal');
        const trelloModal = document.getElementById('trello-modal');
        
        if (openModalBtn) {
            openModalBtn.addEventListener('click', openTrelloModal);
        }
        
        if (closeModalBtn) {
            closeModalBtn.addEventListener('click', closeTrelloModal);
        }
        
        // Fecha o modal quando clica fora
        window.addEventListener('click', (e) => {
            if (e.target === trelloModal) {
                closeTrelloModal();
            }
        });
        
        // Listener para carregar dados
        document.getElementById('load-trello-btn').addEventListener('click', async () => {
            const key = document.getElementById('trello-key').value.trim();
            const token = document.getElementById('trello-token').value.trim();
            const boardId = document.getElementById('trello-board').value.trim();
            if (key && token && boardId) {
                saveCredentials(key, token, boardId);
            }
            await loadBurndownData();
            closeTrelloModal();
        });

        // Listener para desconectar
        document.getElementById('disconnect-trello-btn').addEventListener('click', disconnectFromTrello);
        
        // Listener para mudança de sprint
        const sprintSelect = document.getElementById('sprint-select');
        if (sprintSelect) {
            // Sincronizar seletor com a URL atual
            const urlParams = new URLSearchParams(window.location.search);
            const currentSprint = urlParams.get('sprint') || 'sprint-1';
            const sprintNumber = currentSprint.replace('sprint-', '');
            sprintSelect.value = sprintNumber;
            
            sprintSelect.addEventListener('change', async () => {
                const selectedSprint = sprintSelect.value;
                // Atualizar a URL com o novo parâmetro de sprint
                const url = new URL(window.location);
                url.searchParams.set('sprint', `sprint-${selectedSprint}`);
                window.history.pushState({}, '', url);
                
                // Recarregar os dados
                await loadBurndownData();
            });
        }
        
        loadCredentials();
        await loadBurndownData();
    } catch (error) {
        console.error('Erro ao inicializar:', error);
    }
});

// Atualizar dados a cada 5 minutos
setInterval(loadBurndownData, 5 * 60 * 1000);

// Reagir a mudanças de tema para re-renderizar o gráfico com novas cores
window.addEventListener('themechange', async () => {
    try {
        theme = getThemeColors();
        await loadBurndownData();
    } catch (e) {
        console.error('Erro ao aplicar tema:', e);
    }
});