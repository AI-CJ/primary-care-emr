Primary Care EMR — third-party runtime notices

This portfolio application does not claim ownership of third-party frameworks,
runtime components, starter tooling, or clinical reference vocabularies.
These files reproduce upstream notices; they do not set a repository-wide
license for the application.

Pinned browser runtime:
  Pyodide 314.0.8: https://github.com/pyodide/pyodide/tree/314.0.8
  CPython 3.14.2: https://github.com/python/cpython/tree/v3.14.2
  Emscripten 5.0.3: https://github.com/emscripten-core/emscripten/tree/5.0.3

License text sources:
pyodide-314.0.8-LICENSE.txt
  https://github.com/pyodide/pyodide/blob/314.0.8/LICENSE
cpython-3.14.2-LICENSE.txt
  https://github.com/python/cpython/blob/v3.14.2/LICENSE
emscripten-5.0.3-LICENSE.txt
  https://github.com/emscripten-core/emscripten/blob/5.0.3/LICENSE
emscripten-musl-COPYRIGHT.txt
  https://github.com/emscripten-core/emscripten/blob/5.0.3/system/lib/libc/musl/COPYRIGHT
emscripten-libcxx-LICENSE.txt
  https://github.com/emscripten-core/emscripten/blob/5.0.3/system/lib/libcxx/LICENSE.TXT
emscripten-libcxxabi-LICENSE.txt
  https://github.com/emscripten-core/emscripten/blob/5.0.3/system/lib/libcxxabi/LICENSE.TXT

The distributed Python wheels are kept intact, including their embedded
license and copyright metadata. The effective runtime package lock is in
../runtime/pyodide-lock.json. The npm/ directory is generated from installed
frontend packages during the build, including the Vite runtime helper's license.

Clinical terminology provenance:
  ICD-10-CM FY 2027 — CDC/NCHS and CMS
  https://www.cdc.gov/nchs/icd/icd-10-cm/
  RxNorm Current Prescribable Content — U.S. National Library of Medicine
  https://www.nlm.nih.gov/research/umls/rxnorm/docs/prescribe.html
  CVX and MVX — CDC immunization information systems
  https://www2.cdc.gov/vaccines/iis/iisstandards/vaccines.asp
  Detailed importer and source evidence: https://github.com/AI-CJ/primary-care-emr/tree/main/docs

This is a scoped notice collection, not a legal determination that every
transitive native library or distribution obligation has been audited.
