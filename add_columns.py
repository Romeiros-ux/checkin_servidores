import pandas as pd

# Ler o CSV
df = pd.read_csv('data.csv', encoding='latin1', dtype=str, on_bad_lines='skip')

print(f'Colunas atuais: {list(df.columns)}')

# Adicionar colunas se não existirem
if 'validado_por' not in df.columns:
    df['validado_por'] = ''
    print('Coluna validado_por adicionada')

if 'data_validacao' not in df.columns:
    df['data_validacao'] = ''
    print('Coluna data_validacao adicionada')

# Salvar
df.to_csv('data.csv', index=False, encoding='latin1')
print('✓ CSV atualizado com sucesso!')
