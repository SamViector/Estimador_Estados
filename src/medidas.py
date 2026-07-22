import numpy as np
import pandapower as pp


def simular_medidor(valor_real, desvio_padrao):
    """
    Função inteligente para adicionar ruído Gaussiano ao valor verdadeiro.
    Emula a imprecisão física dos medidores de campo (SCADA/PMU).
    """
    return valor_real + np.random.normal(0, desvio_padrao)

def adicionar_medidas_base(net, b1, b2, b3, b4):
    """
    Limpa qualquer medida antiga e insere o pacote de medições com redundância.
    """
    # 1. Medida de segurança: limpa a base de dados
    net.measurement.drop(net.measurement.index, inplace=True)
    
    # 2. Medidas de Magnitude de Tensão (v)
    v1_scada = simular_medidor(net.res_bus.at[b1, 'vm_pu'], 0.004)
    pp.create_measurement(net, "v", "bus", value=v1_scada, std_dev=0.004, element=b1, name="Medidor V1")
    
    v2_scada = simular_medidor(net.res_bus.at[b2, 'vm_pu'], 0.004)
    pp.create_measurement(net, "v", "bus", value=v2_scada, std_dev=0.004, element=b2, name="Medidor V2")
    
    # 3. Medidas de Injeção de Potência nas Barras (p, q)
    # Nota: Injeção = -(Demanda). Por isso o sinal negativo antes do net.res_bus
    pp.create_measurement(net, "p", "bus", simular_medidor(-net.res_bus.at[b2, 'p_mw'], 0.010), 0.010, b2, name="Medidor P2")
    pp.create_measurement(net, "q", "bus", simular_medidor(-net.res_bus.at[b2, 'q_mvar'], 0.010), 0.010, b2, name="Medidor Q2")
    
    pp.create_measurement(net, "p", "bus", simular_medidor(-net.res_bus.at[b3, 'p_mw'], 0.010), 0.010, b3, name="Medidor P3")
    pp.create_measurement(net, "q", "bus", simular_medidor(-net.res_bus.at[b3, 'q_mvar'], 0.010), 0.010, b3, name="Medidor Q3")
    
    pp.create_measurement(net, "p", "bus", simular_medidor(-net.res_bus.at[b4, 'p_mw'], 0.010), 0.010, b4, name="Medidor P4")
    
    # 4. Medidas de Fluxo de Potência nas Linhas (p, q)
    # Precisamos encontrar os índices das linhas para inserir os medidores
    l12 = net.line[net.line.name == "Linha 1-2"].index[0]
    l23 = net.line[net.line.name == "Linha 2-3"].index[0]
    l24 = net.line[net.line.name == "Linha 2-4"].index[0]

    pp.create_measurement(net, "p", "line", simular_medidor(net.res_line.at[l12, 'p_from_mw'], 0.008), 0.008, l12, side="from", name="Fluxo P 1-2")
    pp.create_measurement(net, "q", "line", simular_medidor(net.res_line.at[l12, 'q_from_mvar'], 0.008), 0.008, l12, side="from", name="Fluxo Q 1-2")
    
    pp.create_measurement(net, "p", "line", simular_medidor(net.res_line.at[l23, 'p_from_mw'], 0.008), 0.008, l23, side="from", name="Fluxo P 2-3")
    pp.create_measurement(net, "q", "line", simular_medidor(net.res_line.at[l23, 'q_from_mvar'], 0.008), 0.008, l23, side="from", name="Fluxo Q 2-3")
    
    pp.create_measurement(net, "p", "line", simular_medidor(net.res_line.at[l24, 'p_from_mw'], 0.008), 0.008, l24, side="from", name="Fluxo P 2-4")
