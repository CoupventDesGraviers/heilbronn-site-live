# Golden verifier fixtures

Configurations with dual-verified `verify_output.json` files, used by
`tests/test_verify.py` and `tests/test_verifier_js.mjs` to check that both
the Python and browser verifiers reproduce the upstream exact results.

Most directories came from
[TejSteadQC/heilbronn-configurations](https://github.com/TejSteadQC/heilbronn-configurations)
(this site's own search campaign) and were retired here once a better
configuration reached `data/sources/external/`; `square-n21-superseded` is
Chouaieb Nemri's AlphaEvolve submission, likewise superseded. None of these
feed the site build.
