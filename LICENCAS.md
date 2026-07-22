# Licenças e procedência

Este repositório mistura três coisas com naturezas jurídicas diferentes, então
elas são licenciadas separadamente. Resumo:

| O que | Licença |
|---|---|
| Código (pipeline Python, site Astro, scripts) | [MIT](LICENSE) |
| Textos e conteúdo editorial do site | CC BY 4.0 |
| Dados de estabelecimentos e grupos (`data/`) | Fatos, sem direito autoral (veja abaixo) |

## Código

MIT. Use, copie, adapte e republique à vontade, inclusive para montar um portal
parecido em outra área ou outro país. É esse o ponto de abrir o código.

## Textos

O conteúdo editorial (explicações sobre CAPS AD, textos das seções, guias) está
sob Creative Commons Atribuição 4.0. Copie e adapte citando a fonte.

## Dados

Os registros em `data/services.json` são **fatos**: nome, endereço, telefone
institucional e coordenada de serviços públicos, mais dia e horário de reuniões
abertas. Fato não é obra e não tem autor.

A Lei de Direitos Autorais (Lei 9.610/1998, art. 8º) diz que não são objeto de
proteção "os textos de tratados, convenções, leis, decretos, regulamentos,
decisões judiciais e demais atos oficiais" (inciso IV) nem "as informações de
uso comum tais como calendários, agendas, **cadastros** ou legendas" (inciso V).
O CNES é literalmente um cadastro oficial. Não havendo direito autoral sobre o
dado, não há o que licenciar.

Isso importa por um motivo prático: o portal de dados abertos do Ministério da
Saúde exibe no rodapé um aviso genérico de CC BY-ND (que proibiria obra
derivada). Lido ao pé da letra, esse aviso contradiz o próprio Decreto
8.777/2016, que estabelece "permissão irrestrita de reuso das bases de dados
publicadas em formato aberto", e de todo modo não alcança fatos, que não são
protegidos. O aviso é boilerplate de site aplicado a tudo, não uma licença
pensada para cada conjunto.

Ainda assim, creditamos a fonte em toda página, com a data de extração, porque
é o certo a fazer e porque atribuição é o que o Decreto 8.777 pede.

## Procedência das fontes

- **CAPS, CAPS AD e demais serviços do SUS**: [CNES, Cadastro Nacional de
  Estabelecimentos de Saúde](https://cnes.datasus.gov.br), do Ministério da
  Saúde, via [API de dados abertos](https://apidadosabertos.saude.gov.br).
  Importamos apenas campos institucionais (nome, endereço, telefone e e-mail da
  unidade, coordenada). Nenhum dado de profissional ou de pessoa física entra
  no pipeline.
- **Grupos de Narcóticos Anônimos**: [diretório público de reuniões do NA
  Brasil](https://www.na.org.br/grupo), via API BMLT. Publicamos local, dia e
  horário de reuniões abertas. Nunca informação sobre participantes.
- **Malha territorial do mapa**: [API de malhas do
  IBGE](https://servicodados.ibge.gov.br/api/v3/malhas/), dado público.
- **Municípios**: [API de localidades do IBGE](https://servicodados.ibge.gov.br/api/v1/localidades/).

## Sem vínculo institucional

Este é um projeto independente. Não possui vínculo, convênio, patrocínio ou
endosso do Ministério da Saúde, do SUS, de Narcóticos Anônimos ou de Alcoólicos
Anônimos. Os nomes dessas instituições aparecem aqui apenas para identificar os
serviços e a procedência dos dados, o que a Lei de Propriedade Industrial
(Lei 9.279/1996, art. 132, IV) permite expressamente para publicações sem
conotação comercial.

Não usamos logotipo, marca figurativa nem brasão de nenhuma dessas instituições.

## Correção e remoção

Qualquer serviço listado aqui é corrigido ou removido mediante aviso. Se você
representa um grupo de mútua ajuda e prefere que ele não apareça, escreva para
contato@acolhimento.org e retiramos, sem pedir explicação.
