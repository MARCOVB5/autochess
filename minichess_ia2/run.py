#!/usr/bin/env python3
"""
Script para iniciar o jogo MiniChess com IA Q-Learning.
Este script permite executar facilmente o jogo a partir do diretório raiz.
"""

import os
import sys

# Adiciona o diretório pai ao path se estiver executando de dentro do diretório do pacote
if os.path.basename(os.getcwd()) == 'minichess_ia2':
    sys.path.insert(0, os.path.abspath('..'))
    from main import main
else:
    from minichess_ia2.main import main

if __name__ == '__main__':
    main() 