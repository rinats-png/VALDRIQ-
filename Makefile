.PHONY: run test check
run:
	python3 -m valdriq

test:
	python3 -m unittest discover -v

check: test
	python3 -m compileall -q valdriq
