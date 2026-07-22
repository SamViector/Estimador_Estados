import sys
import os
import warnings
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pandapower.estimation import estimate
from src.sistema_eletrico import criar_sistema_4barras
from src.medidas import adicionar_medidas_base
from src.analise_erros import verificar_e_corrigir_erros
from src.tabelas import exibir_tabelas_comparacao, exibir_tabela_residuos

pd.options.mode.chained_assignment = None
warnings.filterwarnings("ignore", module="pandapower")

def main():
    print("=========================================================")
    print("  CENÁRIO 4: DETEÇÃO E PURGA DE ERROS GROSSEIROS (BD)    ")
    print("=========================================================\n")
    
    # 1. Criação do Sistema e SCADA
    net, b1, b2, b3, b4 = criar_sistema_4barras()
    
    print("-> A instalar os medidores normais no sistema...")
    # Oculta a saída da tabela de medidas aqui para o terminal não ficar gigante
    import sys, os; sys.stdout = open(os.devnull, 'w') 
    adicionar_medidas_base(net, b1, b2, b3, b4)
    sys.stdout = sys.__stdout__
    
    # 2. INJEÇÃO DO ERRO (Sabotagem Cibernética / Avaria)
    print("\n-> 🚨 SIMULANDO AVARIA (BAD DATA): O medidor de Tensão da Barra 2 avariou!")
    print("-> O valor real da Barra 2 é ~0.98 pu. O medidor enviará 0.50 pu para o SCADA.")
    
    indice_v2 = net.measurement[(net.measurement.element == b2) & (net.measurement.measurement_type == "v")].index
    if not indice_v2.empty:
        net.measurement.at[indice_v2[0], 'value'] = 0.50
        
    # 3. Execução WLS Contaminado
    print("\n-> A executar a Estimação de Estados WLS com dados corrompidos...")
    estimate(net, init="flat")
    
    # 4. CHAMA O MÓDULO DE ANÁLISE DE ERRO QUE ACABÁMOS DE CRIAR
    verificar_e_corrigir_erros(net)
    
    # 5. Exibe as Tabelas Finais Comprovando a Recuperação da Rede
    print("\n-> A gerar relatórios finais do sistema recuperado:")
    exibir_tabelas_comparacao(net)
    exibir_tabela_residuos(net)

if __name__ == "__main__":
    main()