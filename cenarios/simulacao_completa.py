import sys, os
import warnings
import pandas as pd
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.topologia import criar_sistema_4barras, processar_topologia
from src.scada import instalar_medidas_scada, pre_filtrar_medidas
from src.observabilidade import analisar_observabilidade
from src.estimador import executar_pipeline_wls
from src.relatorios import exibir_quadro_medidas, exibir_comparacao_finais

# Suprime SettingWithCopyWarning do pandapower
warnings.filterwarnings("ignore", message=".*SettingWithCopyWarning.*")
pd.options.mode.chained_assignment = None

def main():
    print("=================================================================")
    print(" ⚡ PIPELINE COMPLETO DE ESTIMAÇÃO DE ESTADOS WLS - TCC")
    print("=================================================================\n")

    # 1. Topologia e SCADA
    net, b1, b2, b3, b4 = criar_sistema_4barras()
    processar_topologia(net)
    instalar_medidas_scada(net)

    # Injeção de Erro Grosseiro Proposital para Teste (Sabotagem V2 = 0.50 pu)
    print("\n[SIMULAÇÃO] 🚨 Injetando erro grosseiro severo no medidor V2 (0.50 pu)...")
    net.measurement.loc[(net.measurement.element == 1) & (net.measurement.measurement_type == 'v'), 'value'] = 0.50

    # 2. Pré-filtro e Tabela SCADA
    pre_filtrar_medidas(net)
    exibir_quadro_medidas(net)

    # 3. Observabilidade
    print("\n" + "-"*50)
    observavel, _ = analisar_observabilidade(net)
    
    # 4. Estimação e Bad Data Processing
    if observavel:
        sucesso = executar_pipeline_wls(net, limiar_lnr=3.5)
        if sucesso:
            exibir_comparacao_finais(net)
    print("\n=================================================================")
    print(" SIMULAÇÃO FINALIZADA")
    print("=================================================================")

if __name__ == "__main__":
    main()