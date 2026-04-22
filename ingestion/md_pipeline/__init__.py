"""
Pipeline de extração de editais baseado em markdown estrutural.

Dado um PDF de edital, gera:
1. _toc.txt — Table of Contents em markdown com ranges de página (via LLM multimodal)
2. splits/{edital}/cap_N.pdf — split físico por capítulo de nível 1
3. splits/{edital}/cap_N.md — cada capítulo convertido em markdown filtrado para
   a ênfase "Ciência de Dados" (via LLM multimodal)
4. pós-processamento que força subseções numeradas (2.1, 2.1.1, ...) a virarem
   headers markdown de fato (##, ###, ...), exceto em anexos/apêndices

Ponto de entrada: `gerar_md_edital(pdf_path)` em `pipeline.py`.

Implementação portada do notebook toc_sonnet.ipynb sem mudanças de comportamento
(prompts verbatim, apenas reorganização em módulos).
"""
