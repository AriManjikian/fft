.PHONY: address_generator butterfly complex_adder complex_mult fft test

test:
	. venv/bin/activate && $(MAKE) address_generator butterfly complex_adder complex_mult fft

address_generator:
	$(MAKE) -C test/address_generator

butterfly:
	$(MAKE) -C test/butterfly

complex_adder:
	$(MAKE) -C test/complex_adder

complex_mult:
	$(MAKE) -C test/complex_mult

fft:
	$(MAKE) -C test/fft

clean:
	@find ./test -type d -name "__pycache__" -exec rm -rf {} +
	@find ./test -type d -name "sim_build" -exec rm -rf {} +
	@find ./test -type f -name "results.xml" -exec rm -f {} +
	@find ./test -type f -name "*.None" -exec rm -f {} +
	@find ./test -type d -name ".pytest_cache" -exec rm -rf {} +
	@find ./test -type f -name "dump.vcd" -exec rm -f {} +
	@find ./test -type f -name "dump.fst" -exec rm -f {} +
