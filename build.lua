module = "pdfannex-fixture"
sourcefiledir = "."
docfiledir = "ctan"
textfiledir = "ctan"
testfiledir = "testfiles/l3build"

sourcefiles = {
  "pdfannex-fixture.sty",
  "pdfannex-resolver-fixture",
  "adapter-lib.lua"
}
installfiles = { "pdfannex-fixture.sty" }
scriptfiles = { "pdfannex-resolver-fixture", "adapter-lib.lua" }
exefiles = { "pdfannex-resolver-fixture" }
typesetfiles = { "pdfannex-fixture-doc.tex" }
scriptmanfiles = { "pdfannex-resolver-fixture.1" }
textfiles = { "README.md", "LICENSE" }
