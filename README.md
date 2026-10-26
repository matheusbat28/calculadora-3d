# Calculadora de impressão 3D

Aplicativo desktop **Calculadora de Preço 3D**, desenvolvido em Python com Tkinter para estimar o custo e o preço de um projeto de impressão 3D.

A interface abre em modo escuro e permite alternar para o modo claro pelo botão no cabeçalho. O tempo de impressão é informado em um único campo, no formato `horas:minutos` (por exemplo, `2:30`).

As fórmulas usadas para compor o orçamento também ficam visíveis na tela principal. A janela possui rolagem vertical, reorganiza os campos em uma coluna quando fica estreita e atualiza o orçamento automaticamente conforme os campos são preenchidos.

Na seção **Meus orçamentos**, informe o nome do projeto e salve o cálculo para manter um histórico com os custos de material, energia, mão de obra, custo total, lucro e preço final. Selecione um item para editar ou excluir. Os orçamentos ficam salvos em `%LOCALAPPDATA%\PrintCost\budgets.json` no Windows.

## Como executar

Requer Python 3.10 ou superior. O Tkinter normalmente já vem incluído nas instalações oficiais do Python para Windows.

```powershell
python main.py
```

## Cálculos

- **Material:** peso usado em gramas × preço do filamento por kg ÷ 1.000.
- **Energia:** potência da impressora em kW × duração em horas × tarifa por kWh.
- **Mão de obra:** minutos de trabalho ÷ 60 × valor por hora.
- **Custo total:** material + energia + mão de obra.
- **Preço final:** custo total × (1 + margem de lucro ÷ 100).

Os valores monetários são arredondados para centavos. A margem é aplicada sobre o custo total. Digite valores decimais usando vírgula ou ponto. O tempo e o valor da mão de obra, assim como a margem de lucro, são opcionais; se ficarem em branco, serão considerados como zero. A tarifa de energia também pode ser zero.

## Testes

```powershell
python -m unittest
```
