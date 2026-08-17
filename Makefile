PY ?= python3
A  := ichnos/adapters
E  := ichnos/elephants
B  := ichnos/baboons
S  := ichnos/storks
C  := ichnos/common

.PHONY: help data scan corpus elephants baboons storks conformance figures paper all clean

help:            ## list the targets
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | sed 's/:.*##/	/'

data:            ## download the case datasets from the Movebank repository
	$(PY) -m ichnos.common.fetch_data
	$(PY) -m ichnos.common.fetch_more

scan:            ## inventory the 2008 items of the Movebank repository
	$(PY) -m ichnos.common.scan_movebank

corpus:          ## survey the corpus, validate the detector, write the sheets
	$(PY) -m ichnos.common.corpus
	$(PY) -m ichnos.common.detector_validation
	$(PY) -m ichnos.common.quality_sheets

elephants:       ## case 1: fleet metrology, burst ranks, subsampling
	$(PY) -m ichnos.adapters.movebank
	$(PY) -m ichnos.elephants.bench
	$(PY) -m ichnos.elephants.fleet_health
	$(PY) -m ichnos.elephants.burst_ranks

baboons:         ## case 2: position noise, gravity calibration, gait profiles
	$(PY) -m ichnos.adapters.eobs
	$(PY) -m ichnos.baboons.bench
	$(PY) -m ichnos.baboons.acc_calibrate
	$(PY) -m ichnos.baboons.gaits

storks:          ## case 3: wind aloft from thermal soaring
	$(PY) -m ichnos.storks.wind

conformance:     ## conformance of the corpus to the open pivot format
	$(PY) -m ichnos.conformance.survey

figures:         ## regenerate the paper figures from the bench outputs
	$(PY) -m ichnos.common.figures

paper: figures   ## build the paper PDF (needs pandoc and xelatex)
	$(MAKE) -C docs/article pdf

all: scan corpus elephants baboons storks conformance figures

clean:
	rm -rf out/*.parquet out/*.npy __pycache__ ichnos/*/__pycache__
