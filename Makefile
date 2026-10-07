.PHONY: test test-fast core-dependency package clean
test:
	shellcheck scripts/package scripts/install-texmfhome-tds.sh
	python3 test_core_dependency.py
	python3 test_fixture.py
	python3 test_integration.py
	python3 test_package.py

test-fast:
	python3 test_core_dependency.py
	python3 test_package.py

core-dependency:
	python3 core_dependency.py

package:
	./scripts/package

clean:
	l3build clean
	rm -f pdfannex-fixture-ctan.zip ctan/pdfannex-fixture-doc.pdf
