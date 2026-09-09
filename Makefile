PYTHON ?= python

.PHONY: verify-mechanism verify-qualification verify-paper verify-anonymity verify-artifact generate-paper-evidence build-anonymous-artifact

generate-paper-evidence:
	$(PYTHON) scripts/submission_artifact.py generate

verify-mechanism:
	$(PYTHON) scripts/submission_artifact.py verify-mechanism

verify-qualification:
	$(PYTHON) scripts/submission_artifact.py verify-qualification

verify-paper:
	$(PYTHON) scripts/submission_artifact.py verify-paper

verify-anonymity:
	$(PYTHON) scripts/submission_artifact.py verify-anonymity

build-anonymous-artifact:
	$(PYTHON) paper/fse2027/tools/build_artifact_package.py

verify-artifact:
	$(PYTHON) scripts/submission_artifact.py verify-artifact
