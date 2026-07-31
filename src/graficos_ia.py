# =====================================================================
# ARQUIVO: src/graficos_ia.py
# =====================================================================
import matplotlib.pyplot as plt
import numpy as np

def exibir_dashboard_ia(historico_treino, predicoes, nomes_sensores):
    """
    Gera um painel (Dashboard) com os gráficos de aprendizado da Rede Neural MLP
    para todas as pseudo-medidas restauradas.
    """
    num_graficos = len(nomes_sensores)
    if num_graficos == 0:
        return

    # Ajusta o tamanho da figura dinamicamente de acordo com a quantidade de sensores
    fig, axes = plt.subplots(nrows=num_graficos, ncols=1, figsize=(10, 5 * num_graficos))
    
    # Se for apenas 1 gráfico, transforma num array para não quebrar o loop
    if num_graficos == 1:
        axes = [axes]

    for i in range(num_graficos):
        ax = axes[i]
        X = historico_treino[i]['X'].flatten()
        y = historico_treino[i]['y']
        pred = predicoes[i]
        nome = nomes_sensores[i]

        # Dispersão dos dados simulados (Gêmeo Digital / Pandapower)
        ax.scatter(X, y, color='dodgerblue', alpha=0.6, edgecolors='w', s=50, 
                   label='Treino: Simulações Físicas (Pandapower)')

        # Ponto exato da Predição da IA (Carga = 1.0 pu)
        ax.plot(1.0, pred, marker='*', markersize=18, color='crimson', markeredgecolor='black', 
                label=f'Predição MLP Atual (1.0 pu): {pred:.4f}')

        # Formatação do Gráfico
        ax.set_title(f'Curva de Aprendizado do Gêmeo Digital: {nome}', fontsize=12, fontweight='bold')
        ax.set_xlabel('Fator de Carregamento Global da Rede (pu)', fontsize=10)
        ax.set_ylabel('Valor Esperado do Sensor', fontsize=10)
        
        # Marca a linha vertical do momento atual (1.0 pu)
        ax.axvline(x=1.0, color='gray', linestyle='--', alpha=0.5)
        
        ax.grid(True, linestyle=':', alpha=0.7)
        ax.legend(loc='best', fontsize=10)

    plt.tight_layout()
    plt.show()