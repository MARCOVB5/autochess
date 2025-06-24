# Makefile para compilação do artigo LaTeX

# Diretórios
SRCDIR = src
BUILDDIR = build
OUTPUTDIR = output
IMGDIR = images

# Arquivos principais
MAIN = main
TEX_FILE = $(SRCDIR)/$(MAIN).tex
PDF_FILE = $(BUILDDIR)/$(MAIN).pdf
OUTPUT_PDF = $(OUTPUTDIR)/$(MAIN).pdf

# Comandos
PDFLATEX = pdflatex -interaction=nonstopmode -output-directory=$(BUILDDIR)
BIBTEX = bibtex

# Criar diretórios se não existirem
$(BUILDDIR):
	mkdir -p $(BUILDDIR)

$(OUTPUTDIR):
	mkdir -p $(OUTPUTDIR)

# Compilação principal
pdf: $(BUILDDIR) $(OUTPUTDIR)
	TEXINPUTS="$(SRCDIR):" $(PDFLATEX) $(TEX_FILE)
	@if [ -f "$(SRCDIR)/referencias.bib" ]; then \
		cp $(SRCDIR)/referencias.bib $(BUILDDIR)/; \
		cd $(BUILDDIR) && $(BIBTEX) $(MAIN); \
		TEXINPUTS="$(SRCDIR):" $(PDFLATEX) $(TEX_FILE); \
		TEXINPUTS="$(SRCDIR):" $(PDFLATEX) $(TEX_FILE); \
	fi
	cp $(PDF_FILE) $(OUTPUT_PDF)
	@echo "PDF gerado com sucesso em $(OUTPUT_PDF)"

# Compilação rápida (sem bibliografia)
quick: $(BUILDDIR) $(OUTPUTDIR)
	TEXINPUTS="$(SRCDIR):" $(PDFLATEX) $(TEX_FILE)
	cp $(PDF_FILE) $(OUTPUT_PDF)
	@echo "PDF gerado (compilação rápida) em $(OUTPUT_PDF)"

# Limpar arquivos temporários
clean:
	rm -rf $(BUILDDIR)/*
	@echo "Arquivos temporários removidos"

# Limpar tudo (incluindo PDF final)
clean-all: clean
	rm -rf $(OUTPUTDIR)/*
	@echo "Todos os arquivos gerados removidos"

# Visualizar PDF
view: pdf
	@if command -v evince > /dev/null 2>&1; then \
		evince $(OUTPUT_PDF) & \
	elif command -v okular > /dev/null 2>&1; then \
		okular $(OUTPUT_PDF) & \
	elif command -v xdg-open > /dev/null 2>&1; then \
		xdg-open $(OUTPUT_PDF) & \
	else \
		echo "Nenhum visualizador de PDF encontrado"; \
	fi

# Mostrar ajuda
help:
	@echo "Comandos disponíveis:"
	@echo "  make pdf       - Compila o documento completo (com bibliografia)"
	@echo "  make quick     - Compilação rápida (sem bibliografia)"
	@echo "  make clean     - Remove arquivos temporários"
	@echo "  make clean-all - Remove todos os arquivos gerados"
	@echo "  make view      - Compila e abre o PDF"
	@echo "  make help      - Mostra esta ajuda"

# Alvos que não são arquivos
.PHONY: pdf quick clean clean-all view help
