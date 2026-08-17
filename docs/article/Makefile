# Rendu PDF de l'article via paper-forge.
#
# Le gabarit `perso` n'a pas ete ecrit pour des documents a bibliographie :
# citeproc-header.tex apporte les trois choses qui lui manquent, chacune
# documentee sur place et chacune a remonter en amont plutot qu'a recopier.
PF ?= $(HOME)/projects/pro/deeptech/paper-forge
SRC := instrument-before-inference.md
OUT := outputs/instrument-before-inference.pdf

.PHONY: pdf figures clean

pdf: figures $(OUT)

$(OUT): $(SRC) references.bib citeproc-header.tex
	@mkdir -p outputs
	pandoc $(SRC) \
	  --citeproc --bibliography=references.bib \
	  --include-in-header=citeproc-header.tex \
	  --lua-filter=$(PF)/pandoc/filters/table_style.lua \
	  --lua-filter=$(PF)/pandoc/filters/divs_to_environments.lua \
	  --metadata=paper-forge:$(PF) \
	  --template=$(PF)/templates/perso/perso.tex \
	  --pdf-engine=xelatex -o $@
	@pdfinfo $@ | grep -E "Pages|Title" || true

figures:          ## regenerate the figures from the bench outputs
	cd ../.. && python3 -m ichnos.common.figures

clean:
	rm -rf outputs
