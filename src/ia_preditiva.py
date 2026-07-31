# =====================================================================
# ARQUIVO: src/ia_preditiva.py
# =====================================================================
import numpy as np
import pandapower as pp
import copy
import warnings
import pandas as pd
from sklearn.neural_network import MLPRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

# IMPORTAÇÃO DO NOVO MÓDULO DE GRÁFICOS
from src.graficos_ia import exibir_dashboard_ia

# Suprime avisos de não convergência durante simulações extremas de treino
warnings.filterwarnings("ignore", message=".*Power Flow nr did not converge.*")

class AssistenteMLP_DigitalTwin:
    def __init__(self):
        # Configuração da Rede Neural (MLP)
        self.mlp = MLPRegressor(hidden_layer_sizes=(10, 5), activation='relu', 
                                solver='lbfgs', max_iter=1500, random_state=42)
        self.X_treino = None
        self.y_treino = None

    def gerar_historico_e_treinar(self, net_base, m_type, e_type, elem_idx, num_amostras=200):
        X_treino = []
        y_treino = []

        net_sim = copy.deepcopy(net_base)
        cargas_p = net_sim.load.p_mw.copy()
        cargas_q = net_sim.load.q_mvar.copy()

        fatores_carga = np.linspace(0.7, 1.3, num_amostras)

        for fator in fatores_carga:
            ruido = np.random.normal(1.0, 0.001, len(net_sim.load))
            net_sim.load.p_mw = cargas_p * fator * ruido
            net_sim.load.q_mvar = cargas_q * fator * ruido

            try:
                pp.runpp(net_sim, verbose=False)
                X_treino.append([fator])

                if m_type == "v":
                    val = net_sim.res_bus.at[elem_idx, "vm_pu"]
                elif m_type == "p" and e_type == "bus":
                    val = -net_sim.res_bus.at[elem_idx, "p_mw"]
                elif m_type == "q" and e_type == "bus":
                    val = -net_sim.res_bus.at[elem_idx, "q_mvar"]
                elif m_type == "p" and e_type == "line":
                    val = net_sim.res_line.at[elem_idx, "p_from_mw"]
                elif m_type == "q" and e_type == "line":
                    val = net_sim.res_line.at[elem_idx, "q_from_mvar"]
                else:
                    val = 0.0

                y_treino.append(val)
                
            except pp.LoadflowNotConverged:
                continue

        self.X_treino = np.array(X_treino)
        self.y_treino = np.array(y_treino)
        self.mlp.fit(self.X_treino, self.y_treino)

        # =========================================================
        # CÁLCULO E EXIBIÇÃO DAS MÉTRICAS DE AVALIAÇÃO DA IA
        # =========================================================
        y_pred = self.mlp.predict(self.X_treino)
        
        mse = mean_squared_error(self.y_treino, y_pred)
        rmse = np.sqrt(mse)
        mae = mean_absolute_error(self.y_treino, y_pred)
        r2 = r2_score(self.y_treino, y_pred)
        
        unidade = "pu" if m_type == "v" else "MW/MVAr"
        
        print(f"   [MÉTRICAS IA] Treinamento concluído para ID {elem_idx} ({e_type}):")
        print(f"   > R² (Acurácia de Forma): {r2:.4f} (Ideal: > 0.95)")
        print(f"   > RMSE (Erro Quadrático): {rmse:.6f} {unidade}")
        print(f"   > MAE (Erro Médio Abs.) : {mae:.6f} {unidade}")

    def prever_estado_atual(self, fator_atual=1.0):
        return self.mlp.predict([[fator_atual]])[0]


def recuperar_observabilidade_com_ia(net, medidas_antigas, indices_removidos):
    print("\n" + "="*75)
    print(" 🧠 MÓDULO DE INTELIGÊNCIA ARTIFICIAL ATIVADO (MLP - DIGITAL TWIN)")
    print("="*75)
    print(" -> [IA] Alerta: O expurgo LNR comprometeu a observabilidade (Matriz Singular)!")
    print(" -> [IA] Iniciando simulações de fluxo para treinar as Redes Neurais...\n")
    
    assistente = AssistenteMLP_DigitalTwin()
    medidas_restauradas = 0
    
    # Listas para guardar dados para o gráfico
    historico_all = []
    predicoes_all = []
    nomes_all = []
    
    for idx in indices_removidos:
        row = medidas_antigas.loc[idx]
        m_type = row['measurement_type']
        e_type = row['element_type']
        elem_idx = row['element']
        
        if e_type == "bus":
            if 'name' in net.bus.columns and pd.notna(net.bus.at[elem_idx, 'name']):
                nome_elem = net.bus.at[elem_idx, 'name']
            else:
                nome_elem = f"Barra {elem_idx + 1}"
        elif e_type == "line":
            if 'name' in net.line.columns and pd.notna(net.line.at[elem_idx, 'name']):
                nome_elem = net.line.at[elem_idx, 'name']
            else:
                nome_elem = f"Linha {elem_idx + 1}"
        else:
            nome_elem = f"{e_type} {elem_idx}"
            
        grandeza_str = "V" if m_type == "v" else ("P" if m_type == "p" else "Q")

        assistente.gerar_historico_e_treinar(net, m_type, e_type, elem_idx)
        valor_ia = assistente.prever_estado_atual(fator_atual=1.0)
        
        std_ia = max(0.01, abs(valor_ia) * 0.10) if m_type in ["p", "q"] else 0.01
        
        nome_sensor = f"Pseudo-MLP {grandeza_str} ({nome_elem})"
        pp.create_measurement(net, m_type, e_type, value=valor_ia, std_dev=std_ia, 
                              element=elem_idx, name=nome_sensor)
        
        # Salva para o Dashboard
        historico_all.append({'X': assistente.X_treino, 'y': assistente.y_treino})
        predicoes_all.append(valor_ia)
        nomes_all.append(nome_sensor)
        
        medidas_restauradas += 1
        unidade_str = "pu" if m_type == "v" else ("MW/MVAr" if abs(valor_ia) > 1.5 else "pu")
        print(f" 🟢 [MLP] Sensor Virtual Gerado -> {nome_sensor:<35} | Predição: {valor_ia:8.4f} {unidade_str}")
        
    print(f"\n -> [IA] ✅ {medidas_restauradas} Pseudo-Medida(s) injetada(s)! A rede voltou a ser observável.")
    print("="*75)
    
    # PERGUNTA SE O USUÁRIO QUER VER O GRÁFICO DA IA
    while True:
        ver_grafico = input("\n -> [IA] Deseja visualizar o Dashboard de Aprendizado do Gêmeo Digital? (S/N): ").strip().upper()
        if ver_grafico == 'S':
            print(" -> Abrindo janela de gráficos (Feche a janela do gráfico para o programa continuar)...")
            exibir_dashboard_ia(historico_all, predicoes_all, nomes_all)
            break
        elif ver_grafico == 'N':
            break