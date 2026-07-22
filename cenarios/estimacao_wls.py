import sys
import os
import warnings
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pandapower.estimation import estimate, chi2_analysis
from src.sistema_eletrico import criar_sistema_4barras
from src.medidas import adicionar_medidas_base

# Importe a nova função de resíduos aqui!
from src.tabelas import exibir_tabela_medidas,exibir_tabelas_comparacao, exibir_tabela_residuos

pd.options.mode.chained_assignment = None
warnings.filterwarnings("ignore", module="pandapower")

def main():
    print("=========================================================")
    print("  CENÁRIO 2: ESTIMADOR WLS COM SCADA NORMAL (SEM FALHAS) ")
    print("=========================================================\n")
    
    # 1. Cria a rede elétrica
    net, b1, b2, b3, b4 = criar_sistema_4barras()
    
    # 2. Instala os medidores SCADA
    print("-> A instalar medidores e simular ruído de telecomunicações...")
    adicionar_medidas_base(net, b1, b2, b3, b4)
    
    # 👉 3. MOSTRAR A TABELA DO VETOR Z E MATRIZ R ANTES DE ESTIMAR
    exibir_tabela_medidas(net)
    
    # 4. Executa o Estimador de Estados
    print("\n-> A executar o algoritmo WLS (Newton-Gauss)...")
    sucesso = estimate(net, init="flat")
    
    if sucesso:
        print("✅ Estimação convergida com sucesso!\n")
        
        # Filtro Qui-Quadrado (Módulo de Verificação)
        tem_erro_grosseiro = chi2_analysis(net, chi2_prob_false=0.05)
        
        if not tem_erro_grosseiro:
            print("✅ Verificação Aprovada: O Teste Qui-Quadrado (X²) não detetou erros.")
        else:
            from pandapower.estimation import remove_bad_data
            
            print("🚨 ALARME: O Teste Qui-Quadrado (X²) detetou a presença de Erros Grosseiros!")
            print("-> A iniciar a identificação da medida corrompida (Teste LNR)...")
            
            # 1. Tira uma "fotografia" das medidas antes da limpeza
            medidas_antes = net.measurement.copy()
            indices_antes = set(medidas_antes.index)
            
            # 2. Executa a purga (O pandapower vai apagar a linha do medidor defeituoso)
            sucesso_purga = remove_bad_data(net, init="flat", rn_max_threshold=3.0)
            
            if sucesso_purga:
                # 3. Descobre qual foi o índice apagado
                indices_depois = set(net.measurement.index)
                indices_removidos = indices_antes - indices_depois
                
                print("✅ SUCESSO: O algoritmo isolou e removeu a(s) seguinte(s) medida(s):")
                
                # 4. Imprime os detalhes exatos do medidor sabotado
                for idx in indices_removidos:
                    medida_ruim = medidas_antes.loc[idx]
                    nome = medida_ruim.get('name', f"Medidor {idx}")
                    tipo = medida_ruim['measurement_type']
                    valor_falso = medida_ruim['value']
                    
                    print(f"   ❌ [REMOVIDA] {nome} | Grandeza: '{tipo}' | Valor Lido: {valor_falso} pu")
                
                print("\n-> O Estado da rede foi recalculado automaticamente de forma segura.\n")
            else:
                print("❌ FALHA CRÍTICA: Erro detetado, mas não houve redundância suficiente para o isolar.\n")
            
        # Exibe a tabela comparativa Final (Módulos e Ângulos)
        exibir_tabelas_comparacao(net)

        # EXIBE A NOVA TABELA COMPLETA DE RESÍDUOS E GRANDEZAS
        exibir_tabela_residuos(net)
        
    else:
        print("❌ Falha na convergência do Estimador.")

if __name__ == "__main__":
    main()