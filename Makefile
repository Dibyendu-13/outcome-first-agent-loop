SCENARIO ?= scenarios/public_01_dev.yaml
NAME ?= $(basename $(notdir $(SCENARIO)))

baseline:
	python -m sim baseline --scenario $(SCENARIO) --run-dir runs/base_$(NAME)
serve:
	python -m sim serve --scenario $(SCENARIO) --run-dir runs/mine_$(NAME) --force
grade:
	mkdir -p reports && python -m sim grade --run runs/mine_$(NAME) --baseline runs/base_$(NAME) --out reports/$(NAME).md
test:
	python -m pytest -q tests

SIM_URL ?= http://127.0.0.1:8700
DB ?= controller-data/state.sqlite
controller:
	CONTROLLER_DB="$(DB)" ./run.sh "$(SIM_URL)"
status:
	python -m controller status --db "$(DB)"
dashboard:
	python -m controller serve --db "$(DB)" --port 8800
evaluate:
	python scripts/evaluate.py --name "$(NAME)" --scenario "$(SCENARIO)"
