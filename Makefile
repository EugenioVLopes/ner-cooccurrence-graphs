.PHONY: training-data train evaluate clean-training help

PYTHON ?= uv run python
SPACY ?= uv run python -m spacy
MODEL_DIR ?= models/custom-ner
CONFIG ?= configs/config.cfg
TRAIN ?= data/training/train.spacy
DEV ?= data/training/dev.spacy

help:
	@echo "Targets:"
	@echo "  training-data  - regenerate train.spacy / dev.spacy from jsonl"
	@echo "  train          - train custom NER into $(MODEL_DIR)"
	@echo "  evaluate       - evaluate $(MODEL_DIR)/model-best against dev set"
	@echo "  clean-training - remove generated training artifacts"

training-data:
	$(PYTHON) generate_training_data.py

train: $(TRAIN) $(DEV)
	mkdir -p $(MODEL_DIR)
	$(SPACY) train $(CONFIG) \
		--output $(MODEL_DIR) \
		--paths.train $(TRAIN) \
		--paths.dev $(DEV)

evaluate:
	$(SPACY) evaluate $(MODEL_DIR)/model-best $(DEV) \
		--output $(MODEL_DIR)/metrics.json

clean-training:
	rm -rf $(MODEL_DIR) $(TRAIN) $(DEV)

$(TRAIN) $(DEV):
	$(MAKE) training-data
