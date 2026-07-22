# Ajusta `sys.path` para permitir importações relativas ao diretório do projeto
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pandapower.estimation import estimate
# Importamos a física da rede
from src.sistema_eletrico import criar_sistema_4barras
# Importamos o SCADA
from src.medidas import adicionar_medidas_base

# 1. Cria a rede
net, b1, b2, b3, b4 = criar_sistema_4barras()

# 2. Instala os medidores SCADA
adicionar_medidas_base(net, b1, b2, b3, b4)

# 3. Roda o Estimador
sucesso = estimate(net, init="flat")
print(f"Sucesso na Estimação WLS: {sucesso}")