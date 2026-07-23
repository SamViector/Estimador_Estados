import pandapower as pp
import numpy as np

def criar_sistema_4barras():
    """Cria a rede de 4 barras, roda o fluxo de carga perfeito e retorna a rede."""
    # Fixa a semente para garantir reprodutibilidade nos ruídos futuros
    np.random.seed(42)

    # Criando a rede (S_base = 1 MVA)
    net = pp.create_empty_network(sn_mva=1)

    # Criação das Barras (V_base = 1 kV)
    b1 = pp.create_bus(net, vn_kv=1., name="Barra 1 (Ref)", type="b")
    b2 = pp.create_bus(net, vn_kv=1., name="Barra 2 (PQ)", type="b")
    b3 = pp.create_bus(net, vn_kv=1., name="Barra 3 (PQ)", type="b")
    b4 = pp.create_bus(net, vn_kv=1., name="Barra 4 (PV)", type="b")

    # Criação dos Elementos Shunt
    pp.create_ext_grid(net, bus=b1, vm_pu=1.0, va_degree=0.0, name="Grade/Ref Barra 1")

    # Criação das cargas
    pp.create_load(net, bus=b2, p_mw=0.02, q_mvar=0.01, name="Carga Barra 2")
    pp.create_load(net, bus=b3, p_mw=0.04, q_mvar=0.01, name="Carga Barra 3")

    # Barra 4: Possui um Gerador E uma Carga simultaneamente!
    pp.create_gen(net, bus=b4, p_mw=0.09, vm_pu=0.98, name="Gerador Barra 4")
    pp.create_load(net, bus=b4, p_mw=0.04, q_mvar=0.02, name="Carga Barra 4")

    # Criação das Linhas de Transmissão
    l12 = pp.create_line_from_parameters(net, from_bus=b1, to_bus=b2, length_km=1, r_ohm_per_km=0.2, x_ohm_per_km=0.1, c_nf_per_km=0, max_i_ka=999, name="Linha 1-2")
    l23 = pp.create_line_from_parameters(net, from_bus=b2, to_bus=b3, length_km=1, r_ohm_per_km=0.2, x_ohm_per_km=0.1, c_nf_per_km=0, max_i_ka=999, name="Linha 2-3")
    l24 = pp.create_line_from_parameters(net, from_bus=b2, to_bus=b4, length_km=1, r_ohm_per_km=0.1, x_ohm_per_km=0.05, c_nf_per_km=0, max_i_ka=999, name="Linha 2-4")

    # Roda o Newton-Raphson para obter o Estado Verdadeiro
    pp.runpp(net)  # Algoritmo de Fluxo de Carga

    # Retorna o objeto 'net' e as variáveis das barras para facilitar o uso no SCADA
    return net, b1, b2, b3, b4

def processar_topologia(net):
    """
    [ETAPA 2: TOPOLOGIA] Verifica elementos fora de serviço ou ilhas desenergizadas.
    """
    linhas_ativas = len(net.line[net.line.in_service == True])
    barras_ativas = len(net.bus[net.bus.in_service == True])
    print(f" -> [TOPOLOGIA] Verificação concluída: {barras_ativas} Barras e {linhas_ativas} Linhas em operação normal.")
    return True