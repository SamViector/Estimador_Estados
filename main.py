# =====================================================================
# ARQUIVO: main.py
# =====================================================================
import sys
import os
import warnings
import pandas as pd

# Garante que as pastas src/ e cenarios/ são visíveis para os imports
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# Importação dos módulos do Sistema de 4 Barras
from src.topologia_4b import criar_sistema_4barras, processar_topologia as pt_4b
from src.scada import instalar_medidas_scada_4barras, pre_filtrar_medidas

# Importação dos módulos do Sistema de 5 Barras
from src.topologia_5b import criar_sistema_5barras, processar_topologia as pt_5b
from src.scada import instalar_medidas_scada_5barras

# Importação dos Módulos Comuns (Pipeline, WLS e Relatórios)
from src.observabilidade import analisar_observabilidade
from src.estimador import executar_pipeline_wls
from src.relatorios import (exibir_quadro_medidas, exibir_comparacao_finais, 
                            exibir_tabelas_comparacao_estados, exibir_tabela_residuos)

# Configurações de visualização e alertas do Pandas/Pandapower
warnings.filterwarnings("ignore", message=".*SettingWithCopyWarning.*")
pd.options.mode.chained_assignment = None

def limpar_tela():
    """Limpa o terminal independentemente do Sistema Operativo."""
    os.system('cls' if os.name == 'nt' else 'clear')

def executar_estimacao(net, limiar_lnr=3.5):
    """
    Agrupa o pipeline padrão de estimação (Pré-filtro -> Observabilidade -> WLS -> Relatórios)
    que é comum a todas as topologias.
    """
    pre_filtrar_medidas(net)
    exibir_quadro_medidas(net)

    print("\n" + "-"*50)
    observavel, _ = analisar_observabilidade(net)
    
    if observavel:
        sucesso = executar_pipeline_wls(net, limiar_lnr=limiar_lnr)
        if sucesso:
            exibir_comparacao_finais(net)
            exibir_tabelas_comparacao_estados(net)
            exibir_tabela_residuos(net)

def exibir_menu_cenarios():
    """Menu para escolha de injeção de erros (Sabotagem)."""
    print("\n --- MODO DE OPERAÇÃO DO SCADA ---")
    print(" [A] Estado Normal (Apenas ruído Gaussiano inerente)")
    print(" [B] Injetar Erro Grosseiro (Sabotagem no Medidor de Tensão)")
    return input(" Escolha a condição de medição (A/B): ").strip().upper()

def main():
    while True:
        limpar_tela()
        print("=================================================================")
        print(" ⚡ EMS - ESTIMADOR DE ESTADOS WLS (MENU PRINCIPAL) ⚡")
        print("=================================================================")
        print(" [1] Executar Rede de 4 Barras")
        print(" [2] Executar Rede de 5 Barras (Sistema em Malha)")
        print(" [0] Sair da Aplicação")
        print("=================================================================")
        
        opcao = input(" Escolha a topologia desejada (0-2): ").strip()
        
        if opcao == "0":
            print("\n Encerrando o Estimador de Estados. Até logo!")
            break
            
        elif opcao == "1":
            print("\n" + "="*65)
            print(" 🔄 CARREGANDO SISTEMA: 4 BARRAS")
            print("="*65)
            # 1. Carrega e analisa topologia
            net, b1, b2, b3, b4 = criar_sistema_4barras()
            pt_4b(net)
            
            # 2. Escolha de Cenário (Erro ou Normal)
            modo = exibir_menu_cenarios()
            
            # 3. Instala SCADA (Exclusivo 4 barras)
            instalar_medidas_scada_4barras(net)
            
            if modo == "B":
                print("\n[SIMULAÇÃO] 🚨 Injetando erro grosseiro severo no medidor V2 (0.50 pu)...")
                # Barra 2 no pandapower costuma ser o índice 1
                net.measurement.loc[(net.measurement.element == 1) & (net.measurement.measurement_type == 'v'), 'value'] = 0.50
            else:
                print("\n[SIMULAÇÃO] ✅ Operação em Modo Normal (sem avarias).")

            # 4. Executa WLS
            executar_estimacao(net)
            input("\nPressione ENTER para voltar ao menu principal...")

        elif opcao == "2":
            print("\n" + "="*65)
            print(" 🔄 CARREGANDO SISTEMA: 5 BARRAS")
            print("="*65)
            # 1. Carrega e analisa topologia
            net, b1, b2, b3, b4, b5 = criar_sistema_5barras()
            pt_5b(net)
            
            # 2. Escolha de Cenário (Erro ou Normal)
            modo = exibir_menu_cenarios()
            
            # 3. Instala SCADA (Exclusivo 5 barras)
            instalar_medidas_scada_5barras(net)
            
            if modo == "B":
                print("\n[SIMULAÇÃO] 🚨 Injetando erro grosseiro severo no medidor V3 (0.50 pu)...")
                # Barra 3 no pandapower costuma ser o índice 2
                net.measurement.loc[(net.measurement.element == 2) & (net.measurement.measurement_type == 'v'), 'value'] = 0.50
            else:
                print("\n[SIMULAÇÃO] ✅ Operação em Modo Normal (sem avarias).")

            # 4. Executa WLS
            executar_estimacao(net)
            input("\nPressione ENTER para voltar ao menu principal...")

        else:
            print("\n ⚠️ Opção inválida! Por favor, digite 0, 1 ou 2.")
            input(" Pressione ENTER para tentar novamente...")

if __name__ == "__main__":
    main()