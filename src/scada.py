import numpy as np
import pandapower as pp

def simular_medidor(valor_real, desvio_padrao):
    """Adiciona ruído gaussiano ao valor verdadeiro do fluxo de carga."""
    return valor_real + np.random.normal(0, desvio_padrao)

def instalar_medidas_scada_4barras(net):
    """[ETAPA 1: SCADA] Instala conjunto redundante de medições elétricas."""
    net.measurement.drop(net.measurement.index, inplace=True)
    b1, b2, b3, b4 = 0, 1, 2, 3

    # Medidores de Tensão (V) - Desvio: 0.4%
    pp.create_measurement(net, "v", "bus", simular_medidor(net.res_bus.at[b1, 'vm_pu'], 0.004), 0.004, b1, name="V1")
    pp.create_measurement(net, "v", "bus", simular_medidor(net.res_bus.at[b2, 'vm_pu'], 0.004), 0.004, b2, name="V2")

    # Injeções de Potência (P, Q) - Desvio: 0.002 pu
    for b in [b2, b3, b4]:
        pp.create_measurement(net, "p", "bus", simular_medidor(-net.res_bus.at[b, 'p_mw'], 0.002), 0.002, b, name=f"P{b+1}")
        if b != b4: # Q4 não medido para testar redundância cruzada
            pp.create_measurement(net, "q", "bus", simular_medidor(-net.res_bus.at[b, 'q_mvar'], 0.002), 0.002, b, name=f"Q{b+1}")

    # Fluxos de Linha (P, Q) - Desvio: 0.001 pu
    for idx, linha in net.line.iterrows():
        pp.create_measurement(net, "p", "line", simular_medidor(net.res_line.at[idx, 'p_from_mw'], 0.001), 0.001, idx, side="from", name=f"P_{linha['name']}")
        pp.create_measurement(net, "q", "line", simular_medidor(net.res_line.at[idx, 'q_from_mvar'], 0.001), 0.001, idx, side="from", name=f"Q_{linha['name']}")

def instalar_medidas_scada_5barras(net):
    """
    Instala medidores SCADA no sistema de 5 barras com precisão proporcional (2%)
    e piso de 0.005 pu, pulando a injeção da Barra Slack para evitar conflito numérico.
    """
    net.measurement.drop(net.measurement.index, inplace=True)
    
    # Identifica a barra Slack
    barra_slack = net.ext_grid['bus'].iloc[0] if len(net.ext_grid) > 0 else 0

    # 1. Medidas Nodais (Tensões e Injeções)
    for bus_idx in net.bus.index:
        v_real = net.res_bus.at[bus_idx, 'vm_pu']
        pp.create_measurement(net, "v", "bus", simular_medidor(v_real, 0.004), 0.004, bus_idx, name=f"V_B{bus_idx+1}")

        # Mede P e Q em todas as barras, EXCETO na Slack
        if bus_idx != barra_slack:
            p_inj = -net.res_bus.at[bus_idx, 'p_mw'] / 100.0  # Em pu na base de 100 MVA
            q_inj = -net.res_bus.at[bus_idx, 'q_mvar'] / 100.0
            
            std_p = max(0.005, abs(p_inj) * 0.02)
            std_q = max(0.005, abs(q_inj) * 0.02)

            pp.create_measurement(net, "p", "bus", simular_medidor(p_inj, std_p), std_p, bus_idx, name=f"P_B{bus_idx+1}")
            pp.create_measurement(net, "q", "bus", simular_medidor(q_inj, std_q), std_q, bus_idx, name=f"Q_B{bus_idx+1}")

    # 2. Medidas de Fluxo (Linhas)
    for line_idx in net.line.index:
        p_from = net.res_line.at[line_idx, 'p_from_mw'] / 100.0
        q_from = net.res_line.at[line_idx, 'q_from_mvar'] / 100.0
        
        std_pf = max(0.005, abs(p_from) * 0.02)
        std_qf = max(0.005, abs(q_from) * 0.02)

        pp.create_measurement(net, "p", "line", simular_medidor(p_from, std_pf), std_pf, line_idx, side="from", name=f"P_L{line_idx+1}")
        pp.create_measurement(net, "q", "line", simular_medidor(q_from, std_qf), std_qf, line_idx, side="from", name=f"Q_L{line_idx+1}")

    print(f" -> [SCADA] {len(net.measurement)} medidores alocados com sucesso na rede de 5 Barras!")

def pre_filtrar_medidas(net):
    """
    [ETAPA 3: PRÉ-FILTRAGEM] Remove erros de hardware óbvios antes do cálculo numérico.
    Ex: Tensões negativas ou magnitudes excessivamente absurdas (> 5.0 pu).
    """
    medidas_iniciais = len(net.measurement)
    # Filtra tensões negativas ou maiores que 1.5 pu
    filtro_v = (net.measurement.measurement_type == 'v') & ((net.measurement.value < 0.0) | (net.measurement.value > 1.5))
    # Filtra potências absurdas (> 10 pu)
    filtro_pq = (net.measurement.measurement_type.isin(['p', 'q'])) & (net.measurement.value.abs() > 10.0)
    
    invalidas = net.measurement[filtro_v | filtro_pq].index
    if len(invalidas) > 0:
        print(f" -> [PRÉ-FILTRO] ⚠️ {len(invalidas)} medida(s) com erro absurdo de hardware eliminada(s)!")
        net.measurement.drop(invalidas, inplace=True)
    else:
        print(" -> [PRÉ-FILTRO] ✅ Nenhuma anomalia bruta de hardware detectada nas leituras iniciais.")
    return len(net.measurement)