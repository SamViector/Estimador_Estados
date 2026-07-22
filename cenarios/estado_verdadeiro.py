import sys
import os
import pandas as pd
import warnings

# Este comando garante que o Python encontre a pasta "src" 
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Importamos a função que você acabou de criar no arquivo network.py
from src.sistema_eletrico import criar_sistema_4barras

# Ocultando avisos internos das bibliotecas (Estética do console)
pd.options.mode.chained_assignment = None
warnings.filterwarnings("ignore", module="pandapower")

def main():
    print("=== INICIANDO SIMULAÇÃO: ESTADO VERDADEIRO ===\n")
    
    # 1. Carrega a rede e calcula o fluxo de carga perfeito
    net, b1, b2, b3, b4 = criar_sistema_4barras()

    # 2. Exibe as Tensões e Ângulos
    print("=== ESTADO VERDADEIRO (Fluxo de Carga Perfeito) ===")
    resultados_estado = net.res_bus[['vm_pu', 'va_degree']].copy()
    resultados_estado.index = ['Barra 1', 'Barra 2', 'Barra 3', 'Barra 4']
    print(resultados_estado)

    # 3. Exibe os fluxos de potência
    print("\n=== FLUXOS DE POTÊNCIA NAS LINHAS ===")
    resultados_linhas = net.res_line[['p_from_mw', 'q_from_mvar', 'p_to_mw', 'q_to_mvar']].copy()
    resultados_linhas.index = net.line['name']
    print(resultados_linhas)

# Executa o script
if __name__ == "__main__":
    main()