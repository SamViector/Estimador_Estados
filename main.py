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

# Suporta o nome da função de 4 barras independentemente da versão do scada.py
try:
    from src.scada import instalar_medidas_scada_4barras, pre_filtrar_medidas
except ImportError:
    from src.scada import instalar_medidas_4barras_delgado as instalar_medidas_scada_4barras, pre_filtrar_medidas

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
    """Limpa o terminal independentemente do Sistema Operacional."""
    os.system('cls' if os.name == 'nt' else 'clear')

def exibir_menu_cenarios():
    """Menu para escolha de condição de operação do SCADA."""
    while True:
        print("\n --- MODO DE OPERAÇÃO DO SCADA ---")
        print(" [A] Estado Normal (Apenas ruído Gaussiano inerente)")
        print(" [B] Injetar Erros Grosseiros (Personalizado pelo Usuário)")
        opcao = input(" Escolha a condição de medição (A/B): ").strip().upper()
        if opcao in ["A", "B"]:
            return opcao
        print(" ⚠️ Opção inválida! Escolha A ou B.")

def configurar_e_injetar_erros(net):
    """
    Permite ao usuário definir interativamente quantos erros grosseiros
    deseja injetar, em quais medidores (por ID) e os respectivos valores corrompidos.
    """
    print("\n" + "="*70)
    print(" 🚨 PAINEL DE CONFIGURAÇÃO DE ERROS GROSSEIROS (SABOTAGEM)")
    print("="*70)
    
    # Exibe lista simplificada dos medidores disponíveis
    print(f" {'ID':<4} | {'Tipo':<12} | {'Elemento':<22} | {'Valor Lido Atual':<15}")
    print("-" * 70)
    
    for idx, row in net.measurement.iterrows():
        m_type = row['measurement_type']
        e_type = row['element_type']
        elem_idx = row['element']
        val = row['value']
        
        # Mapeia nome do elemento
        if e_type == "bus":
            nome_elem = net.bus.at[elem_idx, 'name'] if 'name' in net.bus.columns else f"Barra {elem_idx+1}"
        elif e_type == "line":
            nome_elem = net.line.at[elem_idx, 'name'] if 'name' in net.line.columns else f"Linha {elem_idx+1}"
        else:
            nome_elem = f"{e_type} {elem_idx}"
            
        # Nome amigável do tipo
        tipo_str = "Tensão (V)" if m_type == "v" else ("Pot. Ativa (P)" if m_type == "p" else "Pot. Reat. (Q)")
        print(f" {idx:<4} | {tipo_str:<12} | {nome_elem:<22} | {val:<15.4f}")
        
    print("="*70)

    # 1. Pergunta a quantidade de erros a injetar
    total_medidores = len(net.measurement)
    while True:
        try:
            qtd_str = input(f"\n Quantos erros grosseiros deseja injetar? (1 a {total_medidores}): ").strip()
            qtd = int(qtd_str)
            if 1 <= qtd <= total_medidores:
                break
            print(f" ⚠️ Por favor, escolha um número entre 1 e {total_medidores}.")
        except ValueError:
            print(" ⚠️ Por favor, digite um número inteiro válido.")

    medidores_alterados = []
    
    # 2. Loop para configurar cada erro
    for i in range(qtd):
        print(f"\n --- Configurando Erro {i+1} de {qtd} ---")
        
        # Seleção do ID do medidor
        while True:
            try:
                id_med = int(input(" Digite o ID do medidor a ser corrompido: ").strip())
                if id_med not in net.measurement.index:
                    print(f" ⚠️ O ID {id_med} não existe na tabela acima.")
                    continue
                if id_med in medidores_alterados:
                    print(f" ⚠️ O medidor ID {id_med} já foi alterado nesta rodada. Escolha outro ID.")
                    continue
                break
            except ValueError:
                print(" ⚠️ Digite um ID numérico válido.")

        # Leitura das informações do medidor escolhido
        val_antigo = net.measurement.at[id_med, 'value']
        m_type = net.measurement.at[id_med, 'measurement_type']
        
        # Unidade explicativa para o prompt
        unidade_dica = "pu (ex: 0.50 ou 1.30)" if m_type == "v" else "MW/MVAr (ex: 150.0 ou -80.0)"

        # Seleção do novo valor corrompido
        while True:
            try:
                novo_val = float(input(f" Digite o NOVO valor corrompido [{unidade_dica}] (Atual = {val_antigo:.4f}): ").strip())
                break
            except ValueError:
                print(" ⚠️ Digite um número válido (ex: 0.50 ou 120.5).")

        # Injeta a alteração na tabela de medições do pandapower
        net.measurement.at[id_med, 'value'] = novo_val
        medidores_alterados.append(id_med)
        print(f" 🚨 Medidor ID {id_med} atualizado com sucesso! ({val_antigo:.4f} -> {novo_val:.4f})")

    print(f"\n[SIMULAÇÃO] 🚨 {len(medidores_alterados)} erro(s) grosseiro(s) injetado(s) na rede.")

def executar_estimacao(net, limiar_lnr=3.5, modo_interativo=True):
    """
    Agrupa o pipeline padrão de estimação (Pré-filtro -> Observabilidade -> WLS -> Relatórios).
    """
    pre_filtrar_medidas(net)
    exibir_quadro_medidas(net)

    print("\n" + "-"*50)
    observavel, _ = analisar_observabilidade(net)
    
    if observavel:
        sucesso = executar_pipeline_wls(net, limiar_lnr=limiar_lnr,modo_interativo=modo_interativo)
        if sucesso:
            exibir_comparacao_finais(net)
            exibir_tabelas_comparacao_estados(net)
            exibir_tabela_residuos(net)

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
            net, b1, b2, b3, b4 = criar_sistema_4barras()
            pt_4b(net)
            
            # Instala o SCADA base
            instalar_medidas_scada_4barras(net)
            
            modo = exibir_menu_cenarios()
            if modo == "B":
                configurar_e_injetar_erros(net)
            else:
                print("\n[SIMULAÇÃO] ✅ Operação em Modo Normal (sem avarias).")

            # Chama a execução ativando explicitamente o painel interativo de IA em caso de falha
            executar_estimacao(net, modo_interativo=True)
            input("\nPressione ENTER para voltar ao menu principal...")

        elif opcao == "2":
            print("\n" + "="*65)
            print(" 🔄 CARREGANDO SISTEMA: 5 BARRAS")
            print("="*65)
            net, b1, b2, b3, b4, b5 = criar_sistema_5barras()
            pt_5b(net)
            
            # Instala o SCADA base
            instalar_medidas_scada_5barras(net)
            
            modo = exibir_menu_cenarios()
            if modo == "B":
                configurar_e_injetar_erros(net)
            else:
                print("\n[SIMULAÇÃO] ✅ Operação em Modo Normal (sem avarias).")

            # Chama a execução ativando explicitamente o painel interativo de IA em caso de falha
            executar_estimacao(net, modo_interativo=True)
            input("\nPressione ENTER para voltar ao menu principal...")

        else:
            print("\n ⚠️ Opção inválida! Por favor, digite 0, 1 ou 2.")
            input(" Pressione ENTER para tentar novamente...")

if __name__ == "__main__":
    main()