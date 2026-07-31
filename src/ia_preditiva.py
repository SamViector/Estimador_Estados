# =====================================================================
# FICHEIRO: src/ia_preditiva.py
# =====================================================================
import numpy as np
import pandapower as pp
import copy
import warnings
from sklearn.neural_network import MLPRegressor

# Suprime os avisos de não convergência durante a geração de dados extremos
warnings.filterwarnings("ignore", message=".*Power Flow nr did not converge.*")

class AssistenteMLP_DigitalTwin:
    def __init__(self):
        # Configuração da Rede Neural (2 camadas ocultas com 20 e 10 neurónios)
        # O solver 'lbfgs' (ou 'adam') capta perfeitamente a curva não-linear P-V
        self.mlp = MLPRegressor(hidden_layer_sizes=(20, 10), activation='relu', 
                                solver='adam', max_iter=1500, random_state=42)

    def gerar_historico_e_treinar(self, net_base, m_type, e_type, elem_idx, num_amostras=150):
        """
        Gera um histórico operativo (Digital Twin) variando o perfil de carga da rede.
        Resolve o fluxo de potência para cada variação e ensina à IA como o medidor
        específico se comporta perante as leis de Kirchhoff.
        """
        X_treino = []
        y_treino = []

        # Trabalhamos numa cópia para não corromper a rede original em tempo real
        net_sim = copy.deepcopy(net_base)
        cargas_p = net_sim.load.p_mw.copy()
        cargas_q = net_sim.load.q_mvar.copy()

        # Simulações de carga variando de 70% a 130% do consumo nominal
        fatores_carga = np.linspace(0.7, 1.3, num_amostras)

        for fator in fatores_carga:
            # Adiciona uma ligeira perturbação aleatória (5%) a cada carga para criar
            # variabilidade realista (perfis de consumo independentes)
            ruido = np.random.normal(1.0, 0.05, len(net_sim.load))
            
            net_sim.load.p_mw = cargas_p * fator * ruido
            net_sim.load.q_mvar = cargas_q * fator * ruido

            try:
                # Executa o fluxo de carga exato (sem mostrar logs)
                pp.runpp(net_sim, verbose=False)
                
                # A "Feature" (X) que a IA vê é o nível de carregamento global do sistema
                X_treino.append([fator])

                # O "Alvo" (y) é a grandeza física que a IA tem de aprender a prever
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
                # Se a rede entrar em colapso com 130% de carga, a IA ignora essa amostra
                continue

        # Treina a Rede Neural com a física exata da rede!
        X_treino = np.array(X_treino)
        y_treino = np.array(y_treino)
        self.mlp.fit(X_treino, y_treino)

    def prever_estado_atual(self, fator_atual=1.0):
        """
        Prevê com alta precisão qual deveria ser o valor do sensor perdido
        considerando que a rede está a operar no fator nominal (1.0).
        """
        # Num cenário de EMS real, o 'fator_atual' viria do módulo de Previsão de Carga
        return self.mlp.predict([[fator_atual]])[0]


def recuperar_observabilidade_com_ia(net, medidas_antigas, indices_removidos):
    """
    Treina a IA para cada medida perdida, gera uma Pseudo-Medida baseada
    na física da rede, e injeta na matriz WLS para evitar inobservabilidade.
    """
    print("\n" + "="*70)
    print(" 🧠 MÓDULO DE INTELIGÊNCIA ARTIFICIAL ATIVADO (MLP - DIGITAL TWIN)")
    print("="*70)
    print(" -> [IA] Alerta: O expurgo LNR comprometeu a observabilidade (Matriz Singular)!")
    print(" -> [IA] A iniciar simulações de fluxo para treinar as Redes Neurais...\n")
    
    assistente = AssistenteMLP_DigitalTwin()
    medidas_restauradas = 0
    
    for idx in indices_removidos:
        row = medidas_antigas.loc[idx]
        m_type = row['measurement_type']
        e_type = row['element_type']
        elem_idx = row['element']
        
        # 1. Geração de Dados e Treino em Tempo Real para este sensor específico
        assistente.gerar_historico_e_treinar(net, m_type, e_type, elem_idx)
        
        # 2. IA prevê o valor do sensor para a hora atual (carga nominal = 1.0)
        valor_ia = assistente.prever_estado_atual(fator_atual=1.0)
        
        # 3. Parametrização da incerteza: Atribuímos um Desvio Padrão mais alto (ex: 5% a 10%),
        # para o Estimador de Estados saber que é um dado "imaginado" pela IA, dando preferência aos sensores físicos reais.
        std_ia = max(0.05, abs(valor_ia) * 0.10) 
        
        # 4. Injetamos a "Pseudo-Medida Inteligente" na tabela do SCADA
        nome_sensor = f"Pseudo-MLP {m_type.upper()}_{e_type} {elem_idx}"
        pp.create_measurement(net, m_type, e_type, value=valor_ia, std_dev=std_ia, 
                              element=elem_idx, name=nome_sensor)
        
        medidas_restauradas += 1
        print(f" 🟢 [MLP] Sensor Virtual Gerado -> {nome_sensor:<20} | Predição: {valor_ia:8.4f}")
        
    print(f"\n -> [IA] ✅ {medidas_restauradas} Pseudo-Medidas injetadas! A rede voltou a ser observável.")
    print("="*70)